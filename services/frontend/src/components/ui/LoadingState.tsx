import React from 'react';
import { Loader2 } from 'lucide-react';
import './LoadingState.css';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ message = 'INITIALIZING...' }) => {
  return (
    <div className="loading-state">
      <Loader2 className="loading-state-icon" size={24} />
      <span className="loading-state-message">{message}</span>
    </div>
  );
};
