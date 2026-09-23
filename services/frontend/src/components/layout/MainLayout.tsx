import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopTelemetryBar } from './TopTelemetryBar';
import './MainLayout.css';

export const MainLayout: React.FC = () => {
  return (
    <div className="main-layout">
      <Sidebar />
      <div className="main-content">
        <TopTelemetryBar />
        <main className="main-scrollable">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
