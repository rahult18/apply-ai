import { useState, useEffect, useCallback, useRef } from 'react';
import { APP_BASE_URL, API_BASE_URL } from '../../../shared/config.js';

const storageGet = (keys) => {
  return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
};

const storageSet = (items) => {
  return new Promise((resolve) => chrome.storage.local.set(items, resolve));
};

const storageRemove = (keys) => {
  return new Promise((resolve) => chrome.storage.local.remove(keys, resolve));
};

// ─── Apply URL derivation ─────────────────────────────────────────────────────
// For Lever/Ashby JD pages we can construct the application form URL by
// appending the platform-specific suffix to the current tab URL.

function deriveApplyUrl(tabUrl, pageType) {
  if (!tabUrl || pageType !== 'jd') return null;
  try {
    const url = new URL(tabUrl);
    const host = url.hostname;
    if (host.includes('lever.co')) {
      return tabUrl.replace(/\/?$/, '/apply');
    }
    if (host.includes('ashbyhq.com')) {
      return tabUrl.replace(/\/?$/, '/application');
    }
  } catch {
    // Invalid URL
  }
  return null;
}

// ─── Timestamp helpers ────────────────────────────────────────────────────────

async function saveTimestamps(jobApplicationId, patch) {
  const { jobTimestamps } = await storageGet(['jobTimestamps']);
  const existing = jobTimestamps?.job_application_id === jobApplicationId
    ? jobTimestamps
    : { job_application_id: jobApplicationId };
  await storageSet({ jobTimestamps: { ...existing, ...patch } });
}

async function loadTimestamps(jobApplicationId) {
  const { jobTimestamps } = await storageGet(['jobTimestamps']);
  if (jobTimestamps?.job_application_id === jobApplicationId) {
    return jobTimestamps;
  }
  return null;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export const useExtension = () => {
  const [connectionStatus, setConnectionStatus] = useState('checking'); // checking | connected | disconnected | error
  const [userEmail, setUserEmail] = useState('');
  const [userName, setUserName] = useState('');
  const [sessionState, setSessionState] = useState('idle'); // idle | extracting | extracted | autofilling | autofilled | error
  const [statusMessage, setStatusMessage] = useState('');
  const [extractedJob, setExtractedJob] = useState(null);
  const [autofillStats, setAutofillStats] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [resumeMatch, setResumeMatch] = useState(null);
  const [isLoadingMatch, setIsLoadingMatch] = useState(false);
  const [lastRunId, setLastRunId] = useState(null);
  const [isMarkingApplied, setIsMarkingApplied] = useState(false);

  // New state for nav cue and timestamps
  const [currentTabUrl, setCurrentTabUrl] = useState(null);
  const [applyUrl, setApplyUrl] = useState(null);
  const [extractedAt, setExtractedAt] = useState(null);
  const [autofilledAt, setAutofilledAt] = useState(null);

  // Ref to track if we just completed an action (prevents checkJobStatus from resetting state)
  const skipNextResetRef = useRef(false);
  // Ref to always have the current job_application_id available in async message handlers
  const currentJobIdRef = useRef(null);

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
      return true;
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

      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.url) {
        return;
      }

      setCurrentTabUrl(tab.url);

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

      // Derive apply URL for Lever/Ashby JD pages
      setApplyUrl(deriveApplyUrl(tab.url, status.page_type));

      if (status.found) {
        const jobId = status.job_application_id;
        currentJobIdRef.current = jobId;

        setExtractedJob({
          title: status.job_title,
          company: status.company
        });

        if (status.state === 'applied') {
          setSessionState('applied');
        } else if (status.state === 'autofill_generated') {
          setSessionState('autofilled');
        } else if (status.state === 'jd_extracted') {
          setSessionState('extracted');
        }

        if (status.run_id) {
          setLastRunId(status.run_id);
        }

        if (status.plan_summary) {
          setAutofillStats({
            filled: status.plan_summary.autofilled_fields || 0,
            skipped: status.plan_summary.skipped_fields || 0
          });
        }

        // Restore or associate timestamps from local storage.
        // If a provisional entry exists (no job_application_id yet, written right after
        // extraction before we had the id), associate it now.
        const { jobTimestamps } = await storageGet(['jobTimestamps']);
        if (jobTimestamps && !jobTimestamps.job_application_id) {
          // Provisional — associate with current job
          await storageSet({ jobTimestamps: { ...jobTimestamps, job_application_id: jobId } });
          if (jobTimestamps.extractedAt) setExtractedAt(jobTimestamps.extractedAt);
          if (jobTimestamps.autofilledAt) setAutofilledAt(jobTimestamps.autofilledAt);
        } else if (jobTimestamps?.job_application_id === jobId) {
          if (jobTimestamps.extractedAt) setExtractedAt(jobTimestamps.extractedAt);
          if (jobTimestamps.autofilledAt) setAutofilledAt(jobTimestamps.autofilledAt);
        }
      } else {
        if (skipNextResetRef.current) {
          skipNextResetRef.current = false;
        } else {
          setExtractedJob(null);
          setAutofillStats(null);
          setSessionState('idle');
          setExtractedAt(null);
          setAutofilledAt(null);
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
    setExtractedAt(null);
    setAutofilledAt(null);
    setApplyUrl(null);
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
          const now = new Date().toISOString();
          setSessionState('extracted');
          setStatusMessage('Job saved successfully!');
          setExtractedJob({ title: msg.job_title, company: msg.company });
          setExtractedAt(now);
          setAutofilledAt(null); // fresh job, no autofill yet

          // Save provisional timestamp (no job_application_id yet).
          // checkJobStatus() will read this and associate it with the correct job id.
          storageSet({ jobTimestamps: { extractedAt: now, autofilledAt: null } });

          skipNextResetRef.current = true;
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
          const now = new Date().toISOString();
          setSessionState('autofilled');
          setStatusMessage('Form autofilled successfully!');
          setAutofillStats({ filled: msg.filled, skipped: msg.skipped });
          setAutofilledAt(now);

          if (msg.run_id) setLastRunId(msg.run_id);

          // Persist autofill timestamp keyed by current job id
          storageGet(['jobTimestamps']).then(({ jobTimestamps }) => {
            storageSet({
              jobTimestamps: {
                ...(jobTimestamps || {}),
                job_application_id: currentJobIdRef.current,
                autofilledAt: now
              }
            });
          });
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
          skipNextResetRef.current = true;
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
    currentTabUrl,
    applyUrl,
    extractedAt,
    autofilledAt,
    connect,
    disconnect,
    openDashboard,
    extractJob,
    generateAutofill,
    checkJobStatus,
    fetchResumeMatch,
    markAsApplied
  };
};
