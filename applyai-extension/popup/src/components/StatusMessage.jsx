import React from 'react';

const StatusMessage = ({ message, type = 'info' }) => {
  if (!message) return null;

  const typeStyles = {
    info: 'bg-blue-100 text-blue-900 border-blue-300',
    success: 'bg-green-100 text-green-900 border-green-300',
    error: 'bg-red-100 text-red-900 border-red-300',
    warning: 'bg-amber-100 text-amber-900 border-amber-300'
  };

  const icons = {
    info: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    success: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    error: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    warning: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    )
  };

  const style = typeStyles[type] || typeStyles.info;
  const icon = icons[type] || icons.info;

  return (
    <div
      className={`flex items-start gap-2 p-3 rounded-lg border ${style} animate-slide-up`}
    >
      <div className="mt-0.5 flex-shrink-0">
        {icon}
      </div>
      <p className="text-sm leading-relaxed flex-1">{message}</p>
    </div>
  );
};

export default StatusMessage;
