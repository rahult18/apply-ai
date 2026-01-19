import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCloudBolt } from '@fortawesome/free-solid-svg-icons';
import { useExtension } from './hooks/useExtension';
import StatusPill from './components/StatusPill';
import StatusMessage from './components/StatusMessage';
import JobCard from './components/JobCard';
import ActionButton from './components/ActionButton';

const Popup = () => {
  const {
    connectionStatus,
    userEmail,
    userName,
    sessionState,
    statusMessage,
    extractedJob,
    autofillStats,
    jobStatus,
    isCheckingStatus,
    connect,
    disconnect,
    openDashboard,
    extractJob,
    generateAutofill,
    debugExtractFields
  } = useExtension();

  // Determine status pill state
  const getPillState = () => {
    if (connectionStatus === 'checking') return { status: 'checking', text: 'Checking...' };
    if (connectionStatus === 'error') return { status: 'error', text: 'Error' };
    if (connectionStatus === 'disconnected') return { status: 'disconnected', text: 'Not connected' };

    if (isCheckingStatus) {
      return { status: 'checking', text: 'Loading...' };
    }
    if (sessionState === 'extracting' || sessionState === 'autofilling') {
      return { status: 'working', text: 'Working' };
    }
    if (sessionState === 'applied') {
      return { status: 'connected', text: 'Applied' };
    }
    if (sessionState === 'extracted' || sessionState === 'autofilled') {
      return { status: 'connected', text: 'Ready' };
    }
    if (sessionState === 'error') {
      return { status: 'error', text: 'Error' };
    }

    return { status: 'connected', text: 'Connected' };
  };

  const pillState = getPillState();

  // Determine status message type
  const getMessageType = () => {
    if (sessionState === 'extracted' || sessionState === 'autofilled' || sessionState === 'applied') return 'success';
    if (sessionState === 'error') return 'error';
    if (sessionState === 'extracting' || sessionState === 'autofilling') return 'info';
    return 'info';
  };

  // Get appropriate hint text
  const getHintText = () => {
    if (connectionStatus !== 'connected') {
      return 'Connect to sync your profile and autofill preferences';
    }
    if (isCheckingStatus) {
      return 'Checking job status...';
    }

    const pageType = jobStatus?.page_type;
    const isApplicationPage = pageType === 'application';
    const isJdPage = pageType === 'jd' || pageType === 'combined';

    if (!jobStatus?.found) {
      if (isApplicationPage) {
        return 'Navigate to the job description page first to extract the JD';
      }
      return 'Click "Extract JD" to save this job posting';
    }

    if (sessionState === 'extracted') {
      if (isJdPage && pageType !== 'combined') {
        return 'Navigate to the application form, then click Generate Autofill';
      }
      return 'Click "Generate Autofill" to fill the application form';
    }
    if (sessionState === 'autofilled') {
      return 'Review the filled form before submitting';
    }
    if (sessionState === 'applied') {
      return 'You have already applied to this job';
    }
    return '';
  };

  return (
    <div className="w-[380px] min-h-[500px] bg-gray-50">
      <div className="p-4 space-y-3">
        {/* Header */}
        <header className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-3">
            {/* Logo */}
            <div className="w-10 h-10 rounded-lg bg-blue-500 flex items-center justify-center flex-shrink-0">
              <FontAwesomeIcon icon={faCloudBolt} className="text-white text-xl" />
            </div>

            {/* Title and Status */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h1 className="text-base font-bold text-gray-900">ApplyAI</h1>
                <StatusPill status={pillState.status} text={pillState.text} />
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                Autofill applications faster
              </p>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm space-y-3">
          {/* Account Info */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500 font-medium">Account</span>
            <span className={`font-medium ${connectionStatus === 'connected' ? 'text-gray-900' : 'text-gray-400'}`}>
              {connectionStatus === 'connected' ? (userName || userEmail || 'Connected') : 'Not connected'}
            </span>
          </div>

          <div className="h-px bg-gray-200"></div>

          {/* Status Message */}
          {statusMessage && (
            <StatusMessage message={statusMessage} type={getMessageType()} />
          )}

          {/* Job Card */}
          {extractedJob && (
            <JobCard title={extractedJob.title} company={extractedJob.company} />
          )}

          {/* Autofill Stats */}
          {autofillStats && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="flex items-center gap-2 text-sm">
                <svg
                  className="w-5 h-5 text-green-600 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="text-green-700 font-medium">
                  Filled {autofillStats.filled} field{autofillStats.filled !== 1 ? 's' : ''}
                  {autofillStats.skipped > 0 && `, skipped ${autofillStats.skipped}`}
                </span>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-2 pt-1">
            {connectionStatus === 'connected' ? (
              <>
                {/* Page Type Indicator */}
                {jobStatus?.page_type && jobStatus.page_type !== 'unknown' && (
                  <div className="flex items-center justify-center gap-2 text-xs text-gray-500 pb-1">
                    <span className="inline-flex items-center gap-1">
                      {jobStatus.page_type === 'jd' && '📄 Job Description Page'}
                      {jobStatus.page_type === 'application' && '📝 Application Form Page'}
                      {jobStatus.page_type === 'combined' && '📄 Job Page (Single Page)'}
                    </span>
                  </div>
                )}

                {/* Primary Action Button */}
                {(() => {
                  const isWorking = sessionState === 'extracting' || sessionState === 'autofilling';
                  const pageType = jobStatus?.page_type;
                  const isApplicationPage = pageType === 'application';
                  const jobFound = jobStatus?.found;

                  // Show Extract JD button if no job found and not on application page
                  if (!jobFound && !isApplicationPage) {
                    return (
                      <ActionButton
                        onClick={extractJob}
                        loading={sessionState === 'extracting'}
                        disabled={isWorking || isCheckingStatus}
                        variant="primary"
                      >
                        {sessionState === 'extracting' ? 'Extracting...' : 'Extract JD'}
                      </ActionButton>
                    );
                  }

                  // If on application page but no JD extracted yet, show disabled button with hint
                  if (!jobFound && isApplicationPage) {
                    return (
                      <ActionButton
                        disabled={true}
                        variant="secondary"
                      >
                        Extract JD First
                      </ActionButton>
                    );
                  }

                  // Job found - show Generate Autofill or Autofill Again
                  const buttonText = sessionState === 'autofilling'
                    ? 'Generating...'
                    : sessionState === 'autofilled' || jobStatus?.state === 'autofill_generated'
                      ? 'Autofill Again'
                      : 'Generate Autofill';

                  return (
                    <ActionButton
                      onClick={generateAutofill}
                      loading={sessionState === 'autofilling'}
                      disabled={isWorking || isCheckingStatus}
                      variant="primary"
                    >
                      {buttonText}
                    </ActionButton>
                  );
                })()}

                {/* Applied Badge */}
                {sessionState === 'applied' && (
                  <div className="flex items-center justify-center gap-2 py-2">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-100 text-green-700 text-sm font-medium">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Applied
                    </span>
                  </div>
                )}

                {/* Secondary Actions */}
                <div className="grid grid-cols-2 gap-2">
                  <ActionButton onClick={openDashboard} variant="secondary">
                    Dashboard
                  </ActionButton>
                  <ActionButton onClick={debugExtractFields} variant="ghost">
                    🐛 Debug
                  </ActionButton>
                </div>

                {/* Disconnect */}
                <ActionButton onClick={disconnect} variant="danger">
                  Disconnect
                </ActionButton>
              </>
            ) : (
              <ActionButton onClick={connect} variant="primary">
                Connect to ApplyAI
              </ActionButton>
            )}
          </div>

          {/* Hint Text */}
          {getHintText() && (
            <p className="text-xs text-gray-500 text-center leading-relaxed px-1 pt-1">
              {getHintText()}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Popup;
