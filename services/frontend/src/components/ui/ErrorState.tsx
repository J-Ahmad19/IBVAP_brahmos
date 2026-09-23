import React from 'react';
import { AlertTriangle } from 'lucide-react';
import './ErrorState.css';

interface ErrorStateProps {
  message: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ message }) => {
  return (
    <div className="error-state">
      <AlertTriangle className="error-state-icon" size={24} />
      <span className="error-state-message">SYS_ERR: {message}</span>
    </div>
  );
};
