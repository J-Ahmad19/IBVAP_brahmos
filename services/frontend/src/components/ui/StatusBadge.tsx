import React from 'react';
import './StatusBadge.css';

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const statusClass = status.replace(' ', '-').toLowerCase();
  
  return (
    <div className={`status-badge ${statusClass}`}>
      <span className="dot"></span>
      {status}
    </div>
  );
};
