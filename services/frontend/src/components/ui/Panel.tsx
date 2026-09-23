import React from 'react';
import './Panel.css';

interface PanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  noPadding?: boolean;
}

export const Panel: React.FC<PanelProps> = ({ children, className = '', noPadding = false, ...props }) => {
  return (
    <div className={`panel ${noPadding ? 'no-padding' : ''} ${className}`} {...props}>
      {children}
    </div>
  );
};
