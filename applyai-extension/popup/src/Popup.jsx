import { useState, useEffect } from 'react';
import { useExtension } from './hooks/useExtension';
import { useStepperState } from './hooks/useStepperState';
import ProgressStepper from './components/ProgressStepper';
import StatusPill from './components/StatusPill';
import StatusMessage from './components/StatusMessage';
import JobCard from './components/JobCard';
import ActionButton from './components/ActionButton';
import NavCue from './components/NavCue';
import Tabs from './components/Tabs';
import ResumeMatchCard from './components/ResumeMatchCard';
import { BoltIcon, Squares2X2Icon, CheckIcon, CheckBadgeIcon, ArrowPathIcon, ArrowRightOnRectangleIcon } from './components/Icons';

const TABS = [
  { id: 'autofill', label: 'Autofill' },
  { id: 'match', label: 'Resume Score' }
];

function timeAgo(isoString) {
  if (!isoString) return null;
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'yesterday' : `${days}d ago`;
}

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
    isMarkingApplied,
    applyUrl,
    extractedAt,
    autofilledAt,
    connect,
    disconnect,
    openDashboard,
    extractJob,
    generateAutofill,
    fetchResumeMatch,
    markAsApplied
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
  } = useStepperState(connectionStatus, sessionState, jobStatus, isCheckingStatus, statusMessage, extractedJob);

  const handlers = { connect, extractJob, generateAutofill };

  const handlePrimaryAction = () => {
    if (primaryAction.handler && handlers[primaryAction.handler]) {
      handlers[primaryAction.handler]();
    }
  };

  // Nav cue: job is saved but we're still on the JD page (Lever/Ashby)
  const showNavCue = jobStatus?.page_type === 'jd' && showJobCard;

  // Skeleton: initial load while checking status before any data arrives
  const showSkeleton = isCheckingStatus && !jobStatus && connectionStatus === 'connected';

  return (
    <div className="w-[380px] min-h-[500px] bg-gray-50 shadow-[inset_0_0_0_1px_rgba(0,0,0,0.07)]">

      {/* ── Header ────────────────────────────────────────────────────────────── */}
      <header className="px-4 pt-4 pb-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500 to-sky-600 flex items-center justify-center shadow-md shadow-sky-500/25 flex-shrink-0">
            <BoltIcon className="text-white w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <h1 className="text-base font-bold text-gray-900 tracking-tight">ApplyAI</h1>
              <StatusPill status={pillStatus} text={pillText} />
            </div>
            <p className="text-[11px] text-gray-400 mt-0.5 leading-tight">
              Autofill applications faster
            </p>
          </div>
        </div>
      </header>

      {/* ── Progress Stepper ──────────────────────────────────────────────────── */}
      <div className="px-4 pb-3">
        <ProgressStepper steps={steps} />
      </div>

      {/* ── Divider ───────────────────────────────────────────────────────────── */}
      <div className="mx-4 border-t border-gray-100" />

      {/* ── Main Content Card ─────────────────────────────────────────────────── */}
      <div className="m-3 bg-white rounded-2xl border border-gray-100 shadow-md overflow-hidden">

        {/* Tabs — only when connected and a job is found */}
        {connectionStatus === 'connected' && jobStatus?.found && (
          <Tabs tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
        )}

        <div className="p-4 space-y-3">

          {/* Skeleton while loading */}
          {showSkeleton && (
            <div className="space-y-2.5 py-1 animate-slide-up">
              <div className="skeleton h-3.5 rounded-lg w-3/4" />
              <div className="skeleton h-3 rounded-lg w-1/2" />
              <div className="skeleton h-10 rounded-xl w-full mt-1" />
            </div>
          )}

          {/* Autofill Tab */}
          {!showSkeleton && activeTab === 'autofill' && (
            <>
              {/* Status Message */}
              {showStatusMessage && statusMessage && (
                <StatusMessage message={statusMessage} type={messageType} />
              )}

              {/* Job Card */}
              {showJobCard && extractedJob && (
                <JobCard
                  title={extractedJob.title}
                  company={extractedJob.company}
                  extractedAt={extractedAt}
                />
              )}

              {/* Nav Cue — Lever/Ashby: job saved, go to application page */}
              {showNavCue && <NavCue applyUrl={applyUrl} />}

              {/* Autofill Stats */}
              {autofillStats && (
                <div className="flex items-center justify-between gap-2 px-3 py-2.5 bg-green-50 rounded-xl border border-green-100">
                  <div className="flex items-center gap-2">
                    <CheckIcon className="w-4 h-4 text-green-600 flex-shrink-0" />
                    <span className="text-xs font-semibold text-green-700">
                      Filled {autofillStats.filled} field{autofillStats.filled !== 1 ? 's' : ''}
                      {autofillStats.skipped > 0 && `, skipped ${autofillStats.skipped}`}
                    </span>
                  </div>
                  {autofilledAt && (
                    <span className="text-[10px] text-green-500 flex-shrink-0">
                      {timeAgo(autofilledAt)}
                    </span>
                  )}
                </div>
              )}

              {/* Mark as Applied — sole primary CTA in autofilled state */}
              {sessionState === 'autofilled' && (
                <ActionButton
                  onClick={markAsApplied}
                  loading={isMarkingApplied}
                  disabled={isMarkingApplied}
                  icon={CheckBadgeIcon}
                  variant="primary"
                  size="lg"
                >
                  Mark as Applied
                </ActionButton>
              )}

              {/* Applied Badge */}
              {sessionState === 'applied' && (
                <div className="flex items-center justify-center gap-2 py-1.5">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold border border-green-200">
                    <CheckIcon className="w-3.5 h-3.5" />
                    Applied
                  </span>
                </div>
              )}

              {/* Primary Action Button — hidden when Mark as Applied or Applied badge is shown */}
              {sessionState !== 'autofilled' && sessionState !== 'applied' && (
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
              )}

              {/* Hint for disabled state */}
              {primaryAction.hint && (
                <p className="text-[11px] text-gray-400 text-center leading-relaxed">
                  {primaryAction.hint}
                </p>
              )}

            </>
          )}

          {/* Resume Match Tab */}
          {!showSkeleton && activeTab === 'match' && (
            <ResumeMatchCard
              resumeMatch={resumeMatch}
              isLoading={isLoadingMatch}
            />
          )}

        </div>

        {/* ── Footer utility strip ──────────────────────────────────────────── */}
        {connectionStatus === 'connected' && (
          <div className="border-t border-gray-100 bg-gray-50 rounded-b-2xl">
            <div className="flex items-center p-1.5 gap-0.5">

              {/* Run Again — contextual, only after autofill */}
              {sessionState === 'autofilled' && (
                <button
                  onClick={generateAutofill}
                  disabled={isMarkingApplied}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-2
                             text-xs font-medium text-gray-500 hover:text-gray-800
                             hover:bg-white rounded-xl transition-colors duration-150
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <ArrowPathIcon className="w-3.5 h-3.5" />
                  Run Again
                </button>
              )}

              {/* Dashboard */}
              <button
                onClick={openDashboard}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 px-2
                           text-xs font-medium text-gray-500 hover:text-gray-800
                           hover:bg-white rounded-xl transition-colors duration-150"
              >
                <Squares2X2Icon className="w-3.5 h-3.5" />
                Dashboard
              </button>

              {/* Disconnect */}
              <button
                onClick={disconnect}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 px-2
                           text-xs font-medium text-red-400 hover:text-red-600
                           hover:bg-red-50 rounded-xl transition-colors duration-150"
              >
                <ArrowRightOnRectangleIcon className="w-3.5 h-3.5" />
                Disconnect
              </button>

            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default Popup;
