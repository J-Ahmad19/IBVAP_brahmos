import React from 'react';
import './MetricValue.css';

interface MetricValueProps {
  label: string;
  value: string | number;
  unit?: string;
}

export const MetricValue: React.FC<MetricValueProps> = ({ label, value, unit }) => {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-data">
        <span className="metric-value">{value}</span>
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
    </div>
  );
};
