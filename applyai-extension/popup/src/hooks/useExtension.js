import { useState, useEffect, useCallback, useRef } from 'react';

const APP_BASE_URL = "http://localhost:3000";
const API_BASE_URL = "http://localhost:8000";

const storageGet = (keys) => {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
};

const storageRemove = (keys) => {
  return new Promise((resolve) => chrome.storage.local.remove(keys, resolve));
};

export const useExtension = () => {
  const [connectionStatus, setConnectionStatus] = useState('checking'); // checking | connected | disconnected | error
  const [userEmail, setUserEmail] = useState('');
  const [userName, setUserName] = useState('');
  const [sessionState, setSessionState] = useState('idle'); // idle | extracting | extracted | autofilling | autofilled | error
  const [statusMessage, setStatusMessage] = useState('');
  const [extractedJob, setExtractedJob] = useState(null);
  const [autofillStats, setAutofillStats] = useState(null);
  const [jobStatus, setJobStatus] = useState(null); // Response from /jobs/status endpoint
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [resumeMatch, setResumeMatch] = useState(null); // { score, matched_keywords, missing_keywords }
  const [isLoadingMatch, setIsLoadingMatch] = useState(false);
  const [lastRunId, setLastRunId] = useState(null); // Store run_id from last autofill for marking as applied
  const [isMarkingApplied, setIsMarkingApplied] = useState(false);

  // Ref to track if we just completed an action (prevents checkJobStatus from resetting state)
  const skipNextResetRef = useRef(false);

  // Check connection status
  const checkConnection = useCallback(async () => {
    try {
      setConnectionStatus('checking');
      const { extensionToken } = await storageGet(['extensionToken']);

      if (!extensionToken) {
        setConnectionStatus('disconnected');
        return;
      }

      const res = await fetch(`${API_BASE_URL}/extension/me`, {
        headers: { Authorization: `Bearer ${extensionToken}` }
      });

      if (!res.ok) {
        await storageRemove(['extensionToken']);
        setConnectionStatus('disconnected');
        return;
      }

      const userData = await res.json();
      setUserEmail(userData?.email || '');
      setUserName(userData?.full_name || '');
      setConnectionStatus('connected');
      return true; // Return true to indicate successful connection
    } catch (e) {
      console.error('Connection check failed:', e);
      setConnectionStatus('error');
      return false;
    }
  }, []);

  // Check job status for current tab URL
  const checkJobStatus = useCallback(async () => {
    try {
      setIsCheckingStatus(true);
      const { extensionToken } = await storageGet(['extensionToken']);

      if (!extensionToken) {
        return;
      }

      // Get current tab URL
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.url) {
        return;
      }

      const res = await fetch(`${API_BASE_URL}/extension/jobs/status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${extensionToken}`
        },
        body: JSON.stringify({ url: tab.url })
      });

      if (!res.ok) {
        console.error('Failed to check job status:', res.status);
        return;
      }

      const status = await res.json();
      setJobStatus(status);

      // Update session state and extracted job based on status
      if (status.found) {
        setExtractedJob({
          title: status.job_title,
          company: status.company
        });

        // Set session state based on application state
        if (status.state === 'applied') {
          setSessionState('applied');
        } else if (status.state === 'autofill_generated') {
          setSessionState('autofilled');
        } else if (status.state === 'jd_extracted') {
          setSessionState('extracted');
        }

        // Restore lastRunId so "Mark as Applied" works after popup is reopened
        if (status.run_id) {
          setLastRunId(status.run_id);
        }

        // Restore autofillStats from plan_summary (page-specific)
        if (status.plan_summary) {
          setAutofillStats({
            filled: status.plan_summary.autofilled_fields || 0,
            skipped: status.plan_summary.skipped_fields || 0
          });
        }
      } else {
        // No job found for this URL - but don't reset if we just completed an action
        // (extraction/autofill/applied result should be trusted over status check)
        if (skipNextResetRef.current) {
          skipNextResetRef.current = false; // Reset the flag
          // Keep current state
        } else {
          setExtractedJob(null);
          setAutofillStats(null);
          setSessionState('idle');
        }
      }
    } catch (e) {
      console.error('Job status check failed:', e);
    } finally {
      setIsCheckingStatus(false);
    }
  }, []);

  // Connect to ApplyAI
  const connect = useCallback(() => {
    chrome.tabs.create({ url: `${APP_BASE_URL}/extension/connect` });
    window.close();
  }, []);

  // Disconnect
  const disconnect = useCallback(async () => {
    await storageRemove(['extensionToken']);
    setConnectionStatus('disconnected');
    setSessionState('idle');
    setExtractedJob(null);
    setStatusMessage('');
    setAutofillStats(null);
    setJobStatus(null);
  }, []);

  // Open dashboard
  const openDashboard = useCallback(() => {
    chrome.tabs.create({ url: `${APP_BASE_URL}/home` });
    window.close();
  }, []);

  // Extract job description
  const extractJob = useCallback(() => {
    setSessionState('extracting');
    setStatusMessage('Starting extraction...');
    setExtractedJob(null);

    chrome.runtime.sendMessage({ type: 'APPLYAI_EXTRACT_JD' }, (resp) => {
      if (chrome.runtime.lastError) {
        setSessionState('error');
        setStatusMessage(`Error: ${chrome.runtime.lastError.message}`);
      } else if (!resp?.ok) {
        setSessionState('error');
        setStatusMessage(`Error: ${resp?.error || 'Unknown error'}`);
      }
    });
  }, []);

  // Generate autofill
  const generateAutofill = useCallback(() => {
    setSessionState('autofilling');
    setStatusMessage('Generating autofill plan...');
    setAutofillStats(null);

    chrome.runtime.sendMessage({ type: 'APPLYAI_AUTOFILL_PLAN', job_application_id: jobStatus?.job_application_id }, (resp) => {
      if (chrome.runtime.lastError) {
        setSessionState('extracted');
        setStatusMessage(`Error: ${chrome.runtime.lastError.message}`);
      } else if (!resp?.ok) {
        setSessionState('extracted');
        setStatusMessage(`Error: ${resp?.error || 'Unknown error'}`);
      }
    });
  }, [jobStatus]);

  // Debug extract fields
  const debugExtractFields = useCallback(() => {
    chrome.runtime.sendMessage({ type: 'APPLYAI_DEBUG_EXTRACT_FIELDS' }, (resp) => {
      if (chrome.runtime.lastError) {
        setStatusMessage(`Debug Error: ${chrome.runtime.lastError.message}`);
      } else if (resp?.ok) {
        setStatusMessage(`Found ${resp.fieldCount} fields (check console for details)`);
      } else {
        setStatusMessage(`Debug Error: ${resp?.error || 'Unknown error'}`);
      }
    });
  }, []);

  // Fetch resume match score
  const fetchResumeMatch = useCallback(async (jobApplicationId) => {
    if (!jobApplicationId) return;

    try {
      setIsLoadingMatch(true);
      const { extensionToken } = await storageGet(['extensionToken']);
      if (!extensionToken) return;

      const res = await fetch(`${API_BASE_URL}/extension/resume-match`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${extensionToken}`
        },
        body: JSON.stringify({ job_application_id: jobApplicationId })
      });

      if (res.ok) {
        const data = await res.json();
        setResumeMatch(data);
      }
    } catch (e) {
      console.error('Resume match fetch failed:', e);
    } finally {
      setIsLoadingMatch(false);
    }
  }, []);

  // Mark application as applied
  const markAsApplied = useCallback(() => {
    if (!lastRunId) {
      setStatusMessage('No autofill run to mark as applied');
      return;
    }

    setIsMarkingApplied(true);
    setStatusMessage('Marking as applied...');

    chrome.runtime.sendMessage({
      type: 'APPLYAI_MARK_APPLIED',
      run_id: lastRunId
    }, (resp) => {
      if (chrome.runtime.lastError) {
        setIsMarkingApplied(false);
        setStatusMessage(`Error: ${chrome.runtime.lastError.message}`);
      } else if (!resp?.ok) {
        setIsMarkingApplied(false);
        setStatusMessage(`Error: ${resp?.error || 'Unknown error'}`);
      }
      // Success handled by message listener
    });
  }, [lastRunId]);

  // Listen to messages from background script
  useEffect(() => {
    const messageListener = (msg) => {
      if (msg?.type === 'APPLYAI_EXTENSION_CONNECTED') {
        checkConnection();
      }

      if (msg?.type === 'APPLYAI_EXTRACT_JD_PROGRESS') {
        if (sessionState !== 'extracting') return;

        if (msg.stage === 'starting') setStatusMessage('Starting extraction...');
        if (msg.stage === 'extracting_dom') setStatusMessage('Reading page content...');
        if (msg.stage === 'sending_to_backend') setStatusMessage('Analyzing job posting...');
      }

      if (msg?.type === 'APPLYAI_EXTRACT_JD_RESULT') {
        if (msg.ok) {
          setSessionState('extracted');
          setStatusMessage('Job saved successfully!');
          setExtractedJob({
            title: msg.job_title,
            company: msg.company
          });
          // Mark that we just completed an action (prevents checkJobStatus from resetting state)
          skipNextResetRef.current = true;
          // Refresh job status to get updated state
          checkJobStatus();
        } else {
          setSessionState('error');
          setStatusMessage(`Extraction failed: ${msg.error || 'Unknown error'}`);
        }
      }

      if (msg?.type === 'APPLYAI_AUTOFILL_PROGRESS') {
        if (sessionState !== 'autofilling') return;

        if (msg.stage === 'starting') setStatusMessage('Starting autofill...');
        if (msg.stage === 'extracting_dom') setStatusMessage('Reading form...');
        if (msg.stage === 'extracting_fields') setStatusMessage('Analyzing form fields...');
        if (msg.stage === 'planning') setStatusMessage('Generating answers...');
        if (msg.stage === 'autofilling') setStatusMessage('Filling form...');
      }

      if (msg?.type === 'APPLYAI_AUTOFILL_RESULT') {
        if (msg.ok) {
          setSessionState('autofilled');
          setStatusMessage('Form autofilled successfully!');
          setAutofillStats({
            filled: msg.filled,
            skipped: msg.skipped
          });
          // Store run_id for marking as applied later
          if (msg.run_id) {
            setLastRunId(msg.run_id);
          }
        } else {
          setSessionState('extracted');
          setStatusMessage(`Autofill failed: ${msg.error || 'Unknown error'}`);
        }
      }

      if (msg?.type === 'APPLYAI_MARK_APPLIED_RESULT') {
        setIsMarkingApplied(false);
        if (msg.ok) {
          setSessionState('applied');
          setStatusMessage('Application marked as applied!');
          // Mark that we just completed an action (prevents checkJobStatus from resetting state)
          skipNextResetRef.current = true;
          // Refresh job status
          checkJobStatus();
        } else {
          setStatusMessage(`Failed to mark as applied: ${msg.error || 'Unknown error'}`);
        }
      }
    };

    chrome.runtime.onMessage.addListener(messageListener);
    return () => chrome.runtime.onMessage.removeListener(messageListener);
  }, [sessionState, checkConnection, checkJobStatus]);

  // Check connection and job status on mount
  useEffect(() => {
    const initialize = async () => {
      const isConnected = await checkConnection();
      if (isConnected) {
        await checkJobStatus();
      }
    };
    initialize();
  }, [checkConnection, checkJobStatus]);

  return {
    connectionStatus,
    userEmail,
    userName,
    sessionState,
    statusMessage,
    extractedJob,
    autofillStats,
    jobStatus,
    isCheckingStatus,
    resumeMatch,
    isLoadingMatch,
    isMarkingApplied,
    connect,
    disconnect,
    openDashboard,
    extractJob,
    generateAutofill,
    debugExtractFields,
    checkJobStatus,
    fetchResumeMatch,
    markAsApplied
  };
};
