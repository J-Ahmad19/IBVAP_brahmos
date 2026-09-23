import React from 'react';
import './SectionHeader.css';

interface SectionHeaderProps {
  title: string;
  action?: React.ReactNode;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({ title, action }) => {
  return (
    <div className="section-header">
      <h3 className="section-title">{title}</h3>
      {action && <div className="section-action">{action}</div>}
    </div>
  );
};
