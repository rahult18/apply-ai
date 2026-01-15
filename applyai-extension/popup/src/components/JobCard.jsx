import React from 'react';

const JobCard = ({ title, company }) => {
  if (!title && !company) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 animate-slide-up shadow-sm">
      <div className="flex items-start gap-3">
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-2.5 flex-shrink-0">
          <svg
            className="w-5 h-5 text-primary-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate">
            {title || '(Untitled role)'}
          </h3>
          {company && (
            <p className="text-xs text-gray-600 mt-1 truncate">{company}</p>
          )}
          <div className="flex items-center gap-1.5 mt-2">
            <svg
              className="w-3.5 h-3.5 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-xs text-green-600 font-medium">
              Saved to tracker
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JobCard;
