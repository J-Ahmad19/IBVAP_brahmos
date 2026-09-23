import React from 'react';
import './EmptyState.css';

interface EmptyStateProps {
  message: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ message }) => {
  return (
    <div className="empty-state">
      <div className="empty-state-content">
        <div className="empty-state-lines"></div>
        <span className="empty-state-message">{message}</span>
        <div className="empty-state-lines"></div>
      </div>
    </div>
  );
};
