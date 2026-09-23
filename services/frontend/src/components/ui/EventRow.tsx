import React from 'react';
import { SeverityBadge } from './SeverityBadge';
import { Clock } from 'lucide-react';
import './EventRow.css';

export interface EventData {
  event_id: string;
  type: string;
  camera_id: string;
  timestamp: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL' | 'LOW' | 'MEDIUM' | 'HIGH';
  status?: string;
  metadata?: any;
}

interface EventRowProps {
  event: EventData;
  onClick?: (event: EventData) => void;
}

export const EventRow: React.FC<EventRowProps> = ({ event, onClick }) => {
  const time = new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  
  return (
    <div className="event-row" onClick={() => onClick && onClick(event)}>
      <div className="event-time">
        <Clock size={12} className="time-icon" />
        <span>{time}</span>
      </div>
      <div className="event-details">
        <div className="event-header">
          <span className="event-type">{event.type.replace(/_/g, ' ')}</span>
          <SeverityBadge severity={event.severity} />
        </div>
        <div className="event-camera">CAM: {event.camera_id}</div>
      </div>
    </div>
  );
};
