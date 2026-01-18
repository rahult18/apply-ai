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

    if (sessionState === 'extracting' || sessionState === 'autofilling') {
      return { status: 'working', text: 'Working' };
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
    if (sessionState === 'extracted' || sessionState === 'autofilled') return 'success';
    if (sessionState === 'error') return 'error';
    if (sessionState === 'extracting' || sessionState === 'autofilling') return 'info';
    return 'info';
  };

  // Get appropriate hint text
  const getHintText = () => {
    if (connectionStatus !== 'connected') {
      return 'Connect to sync your profile and autofill preferences';
    }
    if (sessionState === 'idle') {
      return 'Navigate to a job posting page, then click Extract Job';
    }
    if (sessionState === 'extracted') {
      return 'Open the application form, then click Generate Autofill';
    }
    if (sessionState === 'autofilled') {
      return 'Review the filled form before submitting';
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
                {/* Primary Action Button */}
                <ActionButton
                  onClick={sessionState === 'idle' ? extractJob : generateAutofill}
                  loading={sessionState === 'extracting' || sessionState === 'autofilling'}
                  disabled={sessionState === 'extracting' || sessionState === 'autofilling'}
                  variant="primary"
                >
                  {sessionState === 'extracting' && 'Extracting...'}
                  {sessionState === 'autofilling' && 'Generating...'}
                  {(sessionState === 'idle' || sessionState === 'error') && 'Extract Job'}
                  {(sessionState === 'extracted' || sessionState === 'autofilled') && 'Generate Autofill'}
                </ActionButton>

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
