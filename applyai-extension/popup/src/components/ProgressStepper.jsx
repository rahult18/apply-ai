import React from 'react';
import { CheckIcon, LinkIcon, DocumentTextIcon, SparklesIcon, CheckBadgeIcon } from './Icons';

const STEP_ICONS = {
  connect: LinkIcon,
  extract: DocumentTextIcon,
  autofill: SparklesIcon,
  applied: CheckBadgeIcon
};

const ProgressStepper = ({ steps }) => {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
      <div className="flex items-center">
        {steps.map((step, idx) => {
          const Icon = STEP_ICONS[step.id];
          const isLast = idx === steps.length - 1;

          return (
            <React.Fragment key={step.id}>
              {/* Step circle + label */}
              <div className="flex flex-col items-center">
                <div
                  className={`
                    w-9 h-9 rounded-full flex items-center justify-center
                    transition-all duration-300 ease-out
                    ${step.state === 'completed'
                      ? 'bg-green-500 text-white'
                      : step.state === 'active'
                        ? 'bg-sky-600 text-white ring-4 ring-sky-100'
                        : 'bg-gray-100 text-gray-400 border-2 border-gray-200'
                    }
                  `}
                >
                  {step.state === 'completed' ? (
                    <CheckIcon className="w-4 h-4" />
                  ) : (
                    <Icon className="w-4 h-4" />
                  )}
                </div>

                {/* Step label */}
                <span
                  className={`
                    text-xs mt-1.5 font-medium transition-colors duration-300
                    ${step.state === 'completed'
                      ? 'text-green-600'
                      : step.state === 'active'
                        ? 'text-sky-600'
                        : 'text-gray-400'
                    }
                  `}
                >
                  {step.label}
                </span>
              </div>

              {/* Connector line (except after last) */}
              {!isLast && (
                <div className="flex-1 mx-1.5">
                  <div
                    className={`
                      h-0.5 transition-colors duration-300
                      ${step.state === 'completed' ? 'bg-green-500' : 'bg-gray-200'}
                    `}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default ProgressStepper;
