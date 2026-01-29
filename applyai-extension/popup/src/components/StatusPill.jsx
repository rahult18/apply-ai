import React from 'react';

const StatusPill = ({ status, text }) => {
  const statusStyles = {
    connected: 'bg-green-100 text-green-700 border-green-200',
    disconnected: 'bg-amber-100 text-amber-700 border-amber-200',
    error: 'bg-red-100 text-red-700 border-red-200',
    working: 'bg-sky-100 text-sky-700 border-sky-200 animate-pulse-subtle'
  };

  const style = statusStyles[status] || statusStyles.connected;

  return (
    <span
      className={`text-xs font-semibold px-2.5 py-1 rounded-full border whitespace-nowrap transition-all duration-300 ${style}`}
    >
      {text}
    </span>
  );
};

export default StatusPill;
