import React from 'react';
import { BriefcaseIcon } from './Icons';

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

const JobCard = ({ title, company, extractedAt }) => {
  if (!title && !company) return null;

  const when = timeAgo(extractedAt);

  return (
    <div className="flex items-center gap-3 p-3 bg-sky-50 rounded-xl border border-sky-100">
      {/* Company logo placeholder */}
      <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-sky-100 to-sky-200 flex items-center justify-center flex-shrink-0">
        <BriefcaseIcon className="w-4 h-4 text-sky-600" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-gray-900 truncate">
          {title || 'Untitled Role'}
        </h3>
        <div className="flex items-center gap-1.5 mt-0.5">
          {company && (
            <p className="text-xs text-gray-500 truncate">{company}</p>
          )}
          {when && company && (
            <span className="text-gray-300 text-xs flex-shrink-0">·</span>
          )}
          {when && (
            <span className="text-xs text-gray-400 flex-shrink-0">Extracted {when}</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default JobCard;
