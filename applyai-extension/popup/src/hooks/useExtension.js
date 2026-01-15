import { useState, useEffect, useCallback } from 'react';

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
    } catch (e) {
      console.error('Connection check failed:', e);
      setConnectionStatus('error');
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

    chrome.runtime.sendMessage({ type: 'APPLYAI_AUTOFILL_PLAN' }, (resp) => {
      if (chrome.runtime.lastError) {
        setSessionState('extracted');
        setStatusMessage(`Error: ${chrome.runtime.lastError.message}`);
      } else if (!resp?.ok) {
        setSessionState('extracted');
        setStatusMessage(`Error: ${resp?.error || 'Unknown error'}`);
      }
    });
  }, []);

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
        } else {
          setSessionState('extracted');
          setStatusMessage(`Autofill failed: ${msg.error || 'Unknown error'}`);
        }
      }
    };

    chrome.runtime.onMessage.addListener(messageListener);
    return () => chrome.runtime.onMessage.removeListener(messageListener);
  }, [sessionState, checkConnection]);

  // Check connection on mount
  useEffect(() => {
    checkConnection();
  }, [checkConnection]);

  return {
    connectionStatus,
    userEmail,
    userName,
    sessionState,
    statusMessage,
    extractedJob,
    autofillStats,
    connect,
    disconnect,
    openDashboard,
    extractJob,
    generateAutofill,
    debugExtractFields
  };
};
