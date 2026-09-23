import React from 'react';
import { Panel } from './Panel';
import { MetricValue } from './MetricValue';
import './TelemetryCard.css';

interface TelemetryCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
}

export const TelemetryCard: React.FC<TelemetryCardProps> = ({ title, value, unit, icon }) => {
  return (
    <Panel className="telemetry-card">
      <div className="telemetry-card-header">
        <span className="telemetry-card-title">{title}</span>
        {icon && <div className="telemetry-card-icon">{icon}</div>}
      </div>
      <MetricValue label="" value={value} unit={unit} />
    </Panel>
  );
};
