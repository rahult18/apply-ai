import React from 'react';

// Arrow right icon (inline, no extra import needed)
const ArrowRightIcon = () => (
  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
  </svg>
);

const NavCue = ({ applyUrl }) => {
  const hasLink = Boolean(applyUrl);

  const handleOpen = () => {
    if (applyUrl) {
      chrome.tabs.create({ url: applyUrl });
    }
  };

  return (
    <div className="flex items-start gap-3 p-3 bg-amber-50 rounded-xl border border-amber-200 animate-slide-up">
      {/* Icon */}
      <div className="mt-0.5 flex-shrink-0 w-5 h-5 rounded-full bg-amber-200 flex items-center justify-center">
        <svg className="w-3 h-3 text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      </div>

      {/* Text + button */}
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold text-amber-800 leading-snug">
          Job saved! Now open the application form.
        </p>
        <p className="text-xs text-amber-700 mt-0.5 leading-relaxed">
          {hasLink
            ? 'Click below to go directly to the application page.'
            : 'Navigate to the application form page on this site to start autofilling.'}
        </p>
        {hasLink && (
          <button
            onClick={handleOpen}
            className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-amber-900 bg-amber-100 hover:bg-amber-200 border border-amber-300 px-2.5 py-1.5 rounded-lg transition-colors duration-150"
          >
            Open Application
            <ArrowRightIcon />
          </button>
        )}
      </div>
    </div>
  );
};

export default NavCue;
