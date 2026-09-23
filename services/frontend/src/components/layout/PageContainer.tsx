import React from 'react';
import './PageContainer.css';

interface PageContainerProps {
  children: React.ReactNode;
  title?: string;
}

export const PageContainer: React.FC<PageContainerProps> = ({ children, title }) => {
  return (
    <div className="page-container">
      {title && (
        <header className="page-header">
          <h2 className="page-title">{title}</h2>
        </header>
      )}
      <div className="page-content">
        {children}
      </div>
    </div>
  );
};
