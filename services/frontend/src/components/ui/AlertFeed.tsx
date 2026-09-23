import React from 'react';
import { Panel } from './Panel';
import { SectionHeader } from './SectionHeader';
import { EventRow, type EventData } from './EventRow';
import { EmptyState } from './EmptyState';
import './AlertFeed.css';

interface AlertFeedProps {
  events: EventData[];
  onEventClick?: (event: EventData) => void;
}

export const AlertFeed: React.FC<AlertFeedProps> = ({ events, onEventClick }) => {
  return (
    <Panel className="alert-feed-panel" noPadding>
      <div className="alert-feed-header-wrapper">
        <SectionHeader title="Live Alerts" />
      </div>
      <div className="alert-feed-content">
        {events.length === 0 ? (
          <EmptyState message="NO ACTIVE ALERTS" />
        ) : (
          events.map(event => (
            <EventRow 
              key={event.event_id} 
              event={event} 
              onClick={onEventClick} 
            />
          ))
        )}
      </div>
    </Panel>
  );
};
