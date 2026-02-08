import { SpinnerIcon } from './Icons';

const ScoreRing = ({ score }) => {
  const radius = 40;
  const stroke = 8;
  const normalizedRadius = radius - stroke / 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const getColor = (score) => {
    if (score >= 80) return '#22c55e'; // green-500
    if (score >= 60) return '#eab308'; // yellow-500
    return '#ef4444'; // red-500
  };

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg height={radius * 2} width={radius * 2}>
        <circle
          stroke="#e5e7eb"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke={getColor(score)}
          fill="transparent"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference + ' ' + circumference}
          style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.5s ease' }}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          transform={`rotate(-90 ${radius} ${radius})`}
        />
      </svg>
      <span className="absolute text-xl font-bold text-gray-900">{score}%</span>
    </div>
  );
};

const KeywordPill = ({ keyword, matched }) => (
  <span
    className={`inline-block px-2 py-0.5 text-xs rounded-full ${
      matched
        ? 'bg-green-100 text-green-700'
        : 'bg-red-100 text-red-700'
    }`}
  >
    {keyword}
  </span>
);

const ResumeMatchCard = ({ resumeMatch, isLoading, onRefresh }) => {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <SpinnerIcon className="w-6 h-6 text-sky-600" />
      </div>
    );
  }

  if (!resumeMatch) {
    return (
      <div className="text-center py-6 text-gray-500 text-sm">
        <p>Extract a job first to see your resume match score.</p>
      </div>
    );
  }

  const { score, matched_keywords, missing_keywords } = resumeMatch;

  return (
    <div className="space-y-4">
      {/* Score Ring */}
      <div className="flex flex-col items-center py-2">
        <ScoreRing score={score} />
        <p className="mt-2 text-sm text-gray-600">
          {score >= 80 ? 'Great match!' : score >= 60 ? 'Good match' : 'Needs improvement'}
        </p>
      </div>

      {/* Matched Keywords */}
      {matched_keywords.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 mb-2">
            Matched ({matched_keywords.length})
          </h4>
          <div className="flex flex-wrap gap-1">
            {matched_keywords.map((kw) => (
              <KeywordPill key={kw} keyword={kw} matched />
            ))}
          </div>
        </div>
      )}

      {/* Missing Keywords */}
      {missing_keywords.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-gray-500 mb-2">
            Missing ({missing_keywords.length})
          </h4>
          <div className="flex flex-wrap gap-1">
            {missing_keywords.map((kw) => (
              <KeywordPill key={kw} keyword={kw} matched={false} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ResumeMatchCard;
