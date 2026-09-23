import React from 'react';
import './SeverityBadge.css';

interface SeverityBadgeProps {
  severity: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity }) => {
  const severityClass = severity.toLowerCase();
  
  return (
    <span className={`severity-badge ${severityClass}`}>
      {severity}
    </span>
  );
};
