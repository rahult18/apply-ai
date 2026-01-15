import React from 'react';

const StatusPill = ({ status, text }) => {
  const statusStyles = {
    checking: 'bg-gray-200 text-gray-900 border-gray-300',
    connected: 'bg-green-100 text-green-900 border-green-300',
    disconnected: 'bg-amber-100 text-amber-900 border-amber-300',
    error: 'bg-red-100 text-red-900 border-red-300',
    working: 'bg-blue-100 text-blue-900 border-blue-300 animate-pulse-subtle'
  };

  const style = statusStyles[status] || statusStyles.checking;

  return (
    <span
      className={`text-xs font-semibold px-2.5 py-1 rounded-full border whitespace-nowrap transition-all duration-300 ${style}`}
    >
      {text}
    </span>
  );
};

export default StatusPill;
