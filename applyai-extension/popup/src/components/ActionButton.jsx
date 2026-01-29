import React from 'react';
import { SpinnerIcon } from './Icons';

const ActionButton = ({
  onClick,
  disabled,
  variant = 'primary',
  size = 'lg',
  icon: Icon,
  children,
  loading = false
}) => {
  const sizeStyles = {
    lg: 'px-6 py-3.5 text-base font-bold rounded-xl',
    md: 'px-4 py-2.5 text-sm font-semibold rounded-lg',
    sm: 'px-3 py-2 text-xs font-medium rounded-lg'
  };

  const variantStyles = {
    primary: 'bg-sky-600 text-white hover:bg-sky-700 shadow-md shadow-sky-600/20',
    secondary: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
    ghost: 'bg-gray-100 text-gray-600 hover:bg-gray-200',
    danger: 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100'
  };

  const iconSizes = {
    lg: 'w-5 h-5',
    md: 'w-4 h-4',
    sm: 'w-3.5 h-3.5'
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`
        w-full flex items-center justify-center gap-2
        transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none
        ${sizeStyles[size]}
        ${variantStyles[variant]}
      `}
    >
      {loading ? (
        <SpinnerIcon className={iconSizes[size]} />
      ) : Icon ? (
        <Icon className={iconSizes[size]} />
      ) : null}
      {children}
    </button>
  );
};

export default ActionButton;
