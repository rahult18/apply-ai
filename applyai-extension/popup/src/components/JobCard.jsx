import React from 'react';
import { BriefcaseIcon } from './Icons';

const JobCard = ({ title, company }) => {
  if (!title && !company) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-3">
        {/* Company logo placeholder */}
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-sky-100 to-sky-200 flex items-center justify-center flex-shrink-0">
          <BriefcaseIcon className="w-5 h-5 text-sky-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 truncate">
            {title || 'Untitled Role'}
          </h3>
          {company && (
            <p className="text-xs text-gray-500 truncate mt-0.5">{company}</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default JobCard;
