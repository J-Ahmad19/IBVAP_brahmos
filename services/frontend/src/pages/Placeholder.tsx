import React from 'react';
import { PageContainer } from '../components/layout/PageContainer';

export const Placeholder: React.FC<{ title: string }> = ({ title }) => (
  <PageContainer title={title}>
    <div style={{ color: 'var(--text-slate)', opacity: 0.5, fontStyle: 'italic' }}>
      Module pending implementation...
    </div>
  </PageContainer>
);
