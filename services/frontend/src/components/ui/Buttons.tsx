import React from 'react';
import './Buttons.css';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  icon?: React.ReactNode;
}

export const PrimaryButton: React.FC<ButtonProps> = ({ children, icon, className = '', ...props }) => {
  return (
    <button className={`btn primary-btn ${className}`} {...props}>
      {icon && <span className="btn-icon">{icon}</span>}
      {children}
    </button>
  );
};

export const SecondaryButton: React.FC<ButtonProps> = ({ children, icon, className = '', ...props }) => {
  return (
    <button className={`btn secondary-btn ${className}`} {...props}>
      {icon && <span className="btn-icon">{icon}</span>}
      {children}
    </button>
  );
};

export const PillButton: React.FC<ButtonProps> = ({ children, icon, className = '', ...props }) => {
  return (
    <button className={`btn pill-btn ${className}`} {...props}>
      {icon && <span className="btn-icon">{icon}</span>}
      {children}
    </button>
  );
};
