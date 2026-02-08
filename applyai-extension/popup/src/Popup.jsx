import { useState, useEffect } from 'react';
import { useExtension } from './hooks/useExtension';
import { useStepperState } from './hooks/useStepperState';
import ProgressStepper from './components/ProgressStepper';
import StatusPill from './components/StatusPill';
import StatusMessage from './components/StatusMessage';
import JobCard from './components/JobCard';
import ActionButton from './components/ActionButton';
import Tabs from './components/Tabs';
import ResumeMatchCard from './components/ResumeMatchCard';
import { BoltIcon, Squares2X2Icon, BugAntIcon, CheckIcon } from './components/Icons';

const TABS = [
  { id: 'autofill', label: 'Autofill' },
  { id: 'match', label: 'Resume Score' }
];

const Popup = () => {
  const [activeTab, setActiveTab] = useState('autofill');

  const {
    connectionStatus,
    sessionState,
    statusMessage,
    extractedJob,
    autofillStats,
    jobStatus,
    isCheckingStatus,
    resumeMatch,
    isLoadingMatch,
    connect,
    disconnect,
    openDashboard,
    extractJob,
    generateAutofill,
    debugExtractFields,
    fetchResumeMatch
  } = useExtension();

  // Fetch resume match when switching to match tab
  useEffect(() => {
    if (activeTab === 'match' && jobStatus?.job_application_id && !resumeMatch) {
      fetchResumeMatch(jobStatus.job_application_id);
    }
  }, [activeTab, jobStatus?.job_application_id, resumeMatch, fetchResumeMatch]);

  const {
    steps,
    pillStatus,
    pillText,
    primaryAction,
    showJobCard,
    showStatusMessage,
    messageType
  } = useStepperState(connectionStatus, sessionState, jobStatus, isCheckingStatus, statusMessage);

  // Map handler names to actual functions
  const handlers = {
    connect,
    extractJob,
    generateAutofill
  };

  const handlePrimaryAction = () => {
    if (primaryAction.handler && handlers[primaryAction.handler]) {
      handlers[primaryAction.handler]();
    }
  };

  return (
    <div className="w-[380px] min-h-[500px] bg-gray-50">
      <div className="p-4 space-y-3">
        {/* Header */}
        <header className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-3">
            {/* Logo */}
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-sky-600 flex items-center justify-center shadow-lg shadow-sky-500/20 flex-shrink-0">
              <BoltIcon className="text-white w-5 h-5" />
            </div>

            {/* Title and Status */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h1 className="text-lg font-bold text-gray-900">ApplyAI</h1>
                <StatusPill status={pillStatus} text={pillText} />
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                Autofill applications faster
              </p>
            </div>
          </div>
        </header>

        {/* Progress Stepper */}
        <ProgressStepper steps={steps} />

        {/* Main Content Card */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
          {/* Tabs - only show when connected and job extracted */}
          {connectionStatus === 'connected' && jobStatus?.found && (
            <Tabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
          )}

          <div className="p-4 space-y-3">
            {/* Autofill Tab Content */}
            {activeTab === 'autofill' && (
              <>
                {/* Status Message */}
                {showStatusMessage && statusMessage && (
                  <StatusMessage message={statusMessage} type={messageType} />
                )}

                {/* Job Card */}
                {showJobCard && extractedJob && (
                  <JobCard title={extractedJob.title} company={extractedJob.company} />
                )}

                {/* Autofill Stats */}
                {autofillStats && (
                  <div className="flex items-center gap-2 p-3 bg-green-50 rounded-lg border border-green-200">
                    <CheckIcon className="w-5 h-5 text-green-600 flex-shrink-0" />
                    <span className="text-sm font-medium text-green-700">
                      Filled {autofillStats.filled} field{autofillStats.filled !== 1 ? 's' : ''}
                      {autofillStats.skipped > 0 && `, skipped ${autofillStats.skipped}`}
                    </span>
                  </div>
                )}

                {/* Applied Badge */}
                {sessionState === 'applied' && (
                  <div className="flex items-center justify-center gap-2 py-2">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-100 text-green-700 text-sm font-medium">
                      <CheckIcon className="w-4 h-4" />
                      Applied
                    </span>
                  </div>
                )}

                {/* Primary Action Button */}
                <ActionButton
                  onClick={handlePrimaryAction}
                  loading={primaryAction.loading}
                  disabled={primaryAction.disabled}
                  icon={primaryAction.icon}
                  variant="primary"
                  size="lg"
                >
                  {primaryAction.label}
                </ActionButton>

                {/* Hint for disabled state */}
                {primaryAction.hint && (
                  <p className="text-xs text-gray-500 text-center leading-relaxed">
                    {primaryAction.hint}
                  </p>
                )}

                {/* Secondary Actions (only when connected) */}
                {connectionStatus === 'connected' && (
                  <>
                    <div className="grid grid-cols-2 gap-2">
                      <ActionButton
                        onClick={openDashboard}
                        variant="secondary"
                        size="md"
                        icon={Squares2X2Icon}
                      >
                        Dashboard
                      </ActionButton>
                      <ActionButton
                        onClick={debugExtractFields}
                        variant="ghost"
                        size="md"
                        icon={BugAntIcon}
                      >
                        Debug
                      </ActionButton>
                    </div>

                    {/* Disconnect */}
                    <ActionButton onClick={disconnect} variant="danger" size="sm">
                      Disconnect
                    </ActionButton>
                  </>
                )}
              </>
            )}

            {/* Resume Match Tab Content */}
            {activeTab === 'match' && (
              <ResumeMatchCard
                resumeMatch={resumeMatch}
                isLoading={isLoadingMatch}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Popup;
