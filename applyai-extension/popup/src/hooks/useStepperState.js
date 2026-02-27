import { useMemo } from 'react';
import { LinkIcon, DocumentTextIcon, SparklesIcon } from '../components/Icons';

const STEPS_CONFIG = [
  { id: 'connect', label: 'Connect' },
  { id: 'extract', label: 'Extract' },
  { id: 'autofill', label: 'Autofill' },
  { id: 'applied', label: 'Applied' }
];

const ACTION_ICONS = {
  connect: LinkIcon,
  extract: DocumentTextIcon,
  autofill: SparklesIcon
};

export const useStepperState = (
  connectionStatus,
  sessionState,
  jobStatus,
  isCheckingStatus,
  statusMessage,
  extractedJob
) => {
  return useMemo(() => {
    // Consider job found if either jobStatus says so OR we have extractedJob from recent extraction
    const hasJob = jobStatus?.found || (extractedJob?.title && extractedJob?.company);

    // Determine current step index
    let currentStepIndex = 0;

    if (connectionStatus !== 'connected') {
      currentStepIndex = 0; // Connect
    } else if (!hasJob) {
      currentStepIndex = 1; // Extract
    } else if (sessionState === 'applied') {
      currentStepIndex = 3; // Applied
    } else {
      currentStepIndex = 2; // Autofill
    }

    // Build steps with states
    const steps = STEPS_CONFIG.map((step, idx) => ({
      ...step,
      state: idx < currentStepIndex ? 'completed' :
             idx === currentStepIndex ? 'active' : 'pending'
    }));

    // Determine pill status
    let pillStatus = 'connected';
    let pillText = 'Connected';

    if (connectionStatus !== 'connected') {
      pillStatus = 'disconnected';
      pillText = 'Not connected';
    } else if (sessionState === 'extracting' || sessionState === 'autofilling') {
      pillStatus = 'working';
      pillText = 'Working...';
    } else if (sessionState === 'error') {
      pillStatus = 'error';
      pillText = 'Error';
    } else if (isCheckingStatus) {
      pillStatus = 'working';
      pillText = 'Loading...';
    }

    // Determine primary action
    const getPrimaryAction = () => {
      if (connectionStatus !== 'connected') {
        return {
          label: 'Connect to ApplyAI',
          handler: 'connect',
          icon: ACTION_ICONS.connect,
          loading: false,
          disabled: false
        };
      }

      const isWorking = sessionState === 'extracting' || sessionState === 'autofilling';
      const pageType = jobStatus?.page_type;

      // On extract step
      if (!hasJob && pageType !== 'application') {
        return {
          label: sessionState === 'extracting' ? 'Extracting...' : 'Extract Job',
          handler: 'extractJob',
          icon: ACTION_ICONS.extract,
          loading: sessionState === 'extracting',
          disabled: isWorking || isCheckingStatus
        };
      }

      // On application page without job extracted
      if (!hasJob && pageType === 'application') {
        return {
          label: 'Extract Job First',
          handler: null,
          icon: ACTION_ICONS.extract,
          loading: false,
          disabled: true,
          hint: 'Go to the job description page to extract the job first'
        };
      }

      // Job found - autofill step
      const isAutofilled = sessionState === 'autofilled' || jobStatus?.state === 'autofill_generated';
      return {
        label: sessionState === 'autofilling' ? 'Generating...' :
               isAutofilled ? 'Autofill Again' : 'Generate Autofill',
        handler: 'generateAutofill',
        icon: ACTION_ICONS.autofill,
        loading: sessionState === 'autofilling',
        disabled: isWorking || isCheckingStatus
      };
    };

    const primaryAction = getPrimaryAction();

    // Message type
    const messageType = sessionState === 'error' ? 'error' :
                        (sessionState === 'extracted' || sessionState === 'autofilled') ? 'success' : 'info';

    // Show status message conditions
    const showStatusMessage = Boolean(statusMessage) && (
      sessionState === 'extracting' ||
      sessionState === 'autofilling' ||
      sessionState === 'error' ||
      sessionState === 'extracted' ||
      sessionState === 'autofilled'
    );

    return {
      steps,
      currentStepIndex,
      pillStatus,
      pillText,
      primaryAction,
      showJobCard: currentStepIndex >= 2 && hasJob,
      showStatusMessage,
      messageType
    };
  }, [connectionStatus, sessionState, jobStatus, isCheckingStatus, statusMessage, extractedJob]);
};
