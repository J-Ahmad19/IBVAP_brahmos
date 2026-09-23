import React from 'react';
import { StatusBadge } from './StatusBadge';
import './CameraTile.css';

export interface CameraTileProps {
  id: string;
  name: string;
  zone: string;
  status: 'ONLINE' | 'OFFLINE' | 'CONNECTING' | 'NO DATA';
  fps?: number;
  trackCount?: number;
  activeAlerts?: number;
  previewUrl?: string;
  onClick?: () => void;
}

export const CameraTile: React.FC<CameraTileProps> = ({
  id, name, zone, status, fps = 0, trackCount = 0, activeAlerts = 0, previewUrl, onClick
}) => {
  return (
    <div className={`camera-tile ${onClick ? 'clickable' : ''}`} onClick={onClick}>
      <div className="camera-tile-video">
        {previewUrl ? (
          <img src={previewUrl} alt={name} className="camera-preview" />
        ) : (
          <div className="camera-no-feed">
            <span className="no-feed-text">NO SIGNAL</span>
          </div>
        )}
        <div className="camera-overlay top-left">
          <span className="camera-id">{id}</span>
        </div>
        <div className="camera-overlay top-right">
          <StatusBadge status={status} />
        </div>
        <div className="camera-overlay bottom-left">
          <span className="camera-zone">{zone}</span>
        </div>
        <div className="camera-overlay bottom-right">
          {status === 'ONLINE' && (
            <div className="camera-metrics">
              <span className="metric">FPS: {fps}</span>
              <span className="metric">TRK: {trackCount}</span>
            </div>
          )}
        </div>
      </div>
      
      <div className="camera-tile-footer">
        <div className="camera-info">
          <div className="camera-name">{name}</div>
        </div>
        {activeAlerts > 0 && (
          <div className="camera-alerts">
            <span className="alert-count">{activeAlerts}</span>
            <span className="alert-label">ALERTS</span>
          </div>
        )}
      </div>
    </div>
  );
};
