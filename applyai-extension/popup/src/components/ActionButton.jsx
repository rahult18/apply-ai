import React from 'react';

const ActionButton = ({ onClick, disabled, variant = 'primary', children, loading = false }) => {
  const variantStyles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm font-bold',
    secondary: 'bg-white text-gray-950 border-2 border-gray-400 hover:bg-gray-50 font-bold',
    danger: 'bg-red-600 text-white border border-red-700 hover:bg-red-700 font-bold',
    ghost: 'bg-gray-200 text-gray-950 hover:text-black hover:bg-gray-300 font-bold'
  };

  const style = variantStyles[variant] || variantStyles.primary;

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`
        w-full px-4 py-3 rounded-lg text-base font-bold leading-tight
        transition-all duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        flex items-center justify-center gap-2
        ${style}
      `}
    >
      {loading && (
        <svg
          className="animate-spin h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {children}
    </button>
  );
};

export default ActionButton;
