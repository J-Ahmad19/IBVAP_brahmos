import React, { useState, useEffect } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { Panel } from '../components/ui/Panel';
import { SectionHeader } from '../components/ui/SectionHeader';
import { DataTable } from '../components/ui/DataTable';
import { StatusBadge } from '../components/ui/StatusBadge';
import { SeverityBadge } from '../components/ui/SeverityBadge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import type { EventData } from '../components/ui/EventRow';
import { Drawer } from '../components/ui/Drawer';
import { PrimaryButton, SecondaryButton } from '../components/ui/Buttons';
import { useAuth } from '../contexts/AuthContext';
import './EventExplorer.css';

export const EventExplorer: React.FC = () => {
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<EventData | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const { canOperate, role } = useAuth();

  // Filters
  const [cameraId, setCameraId] = useState('');
  const [eventType, setEventType] = useState('');

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (cameraId) params.append('camera_id', cameraId);
      if (eventType) params.append('event_type', eventType);
      params.append('size', '50');

      const res = await fetch(`/api/v1/events?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to fetch events');
      const data = await res.json();
      setEvents(data.data || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [cameraId, eventType]);

  const updateEventStatus = async (status: string) => {
    if (!selectedEvent) return;
    setActionLoading(true);
    try {
      const res = await fetch(`/api/v1/events/${selectedEvent.event_id}`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Role': role
        },
        body: JSON.stringify({ status })
      });
      if (!res.ok) throw new Error('Failed to update event');
      
      const updated = await res.json();
      
      // Update local state
      setEvents(events.map(e => e.event_id === updated.data.event_id ? updated.data : e));
      setSelectedEvent(updated.data);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const columns = [
    {
      key: 'timestamp',
      header: 'TIME',
      render: (e: EventData) => new Date(e.timestamp).toLocaleString()
    },
    {
      key: 'camera_id',
      header: 'CAMERA'
    },
    {
      key: 'type',
      header: 'EVENT TYPE',
      render: (e: EventData) => e.type.replace(/_/g, ' ')
    },
    {
      key: 'severity',
      header: 'SEVERITY',
      render: (e: EventData) => <SeverityBadge severity={e.severity} />
    },
    {
      key: 'status',
      header: 'STATUS',
      render: (e: EventData) => <StatusBadge status={e.status || 'NEW'} />
    }
  ];

  return (
    <PageContainer>
      <div className="event-explorer-container">
        <Panel className="event-filters">
          <SectionHeader title="Event Explorer" />
          <div className="filters-row">
            <div className="filter-group">
              <label>Camera ID</label>
              <input 
                type="text" 
                placeholder="All Cameras"
                value={cameraId}
                onChange={e => setCameraId(e.target.value)}
              />
            </div>
            <div className="filter-group">
              <label>Event Type</label>
              <select value={eventType} onChange={e => setEventType(e.target.value)}>
                <option value="">All Types</option>
                <option value="VIRTUAL_FENCE_INTRUSION">Virtual Fence Intrusion</option>
                <option value="LOITERING">Loitering</option>
                <option value="FACE_MATCH">Face Match</option>
                <option value="ANPR_MATCH">ANPR Match</option>
              </select>
            </div>
            <SecondaryButton onClick={fetchEvents}>REFRESH</SecondaryButton>
          </div>
        </Panel>

        <div className="event-table-wrapper">
          {loading ? (
            <LoadingState message="FETCHING EVENTS..." />
          ) : error ? (
            <ErrorState message={error} />
          ) : (
            <DataTable 
              columns={columns} 
              data={events} 
              onRowClick={setSelectedEvent} 
            />
          )}
        </div>

        <Drawer 
          isOpen={!!selectedEvent} 
          onClose={() => setSelectedEvent(null)}
          title="Event Details"
        >
          {selectedEvent && (
            <div className="event-detail-content">
              {(selectedEvent as any).media_ref ? (
                <div className="event-snapshot">
                  {/* Since media_ref might be an S3 key, we might need a presigned URL endpoint, 
                      but for this prototype, if it's a URL we display it, else show placeholder */}
                  <img src={`/api/v1/media/${(selectedEvent as any).media_ref}`} alt="Event Snapshot" 
                       onError={(e) => (e.currentTarget.style.display = 'none')} />
                  <div className="no-snapshot-text">NO MEDIA AVAILABLE</div>
                </div>
              ) : (
                <div className="event-snapshot placeholder">
                  NO MEDIA CAPTURED
                </div>
              )}

              <div className="event-meta-grid">
                <div className="meta-item">
                  <label>EVENT ID</label>
                  <span>{selectedEvent.event_id}</span>
                </div>
                <div className="meta-item">
                  <label>TIMESTAMP</label>
                  <span>{new Date(selectedEvent.timestamp).toLocaleString()}</span>
                </div>
                <div className="meta-item">
                  <label>TYPE</label>
                  <span>{selectedEvent.type}</span>
                </div>
                <div className="meta-item">
                  <label>CAMERA</label>
                  <span>{selectedEvent.camera_id}</span>
                </div>
                <div className="meta-item">
                  <label>TRACK ID</label>
                  <span>{selectedEvent.metadata?.track_id || 'N/A'}</span>
                </div>
                <div className="meta-item">
                  <label>CONFIDENCE</label>
                  <span>{(selectedEvent as any).confidence ? `${((selectedEvent as any).confidence * 100).toFixed(1)}%` : 'N/A'}</span>
                </div>
                <div className="meta-item">
                  <label>CURRENT STATUS</label>
                  <StatusBadge status={selectedEvent.status || 'NEW'} />
                </div>
                
                {selectedEvent.type === 'FACE_MATCH' && (
                  <>
                    <div className="meta-item" style={{ color: 'var(--color-brand)' }}>
                      <label>MATCHED IDENTITY</label>
                      <span>{selectedEvent.metadata?.subject_id || 'UNKNOWN'}</span>
                    </div>
                    <div className="meta-item">
                      <label>SIMILARITY SCORE</label>
                      <span>{(selectedEvent as any).confidence ? `${((selectedEvent as any).confidence * 100).toFixed(1)}%` : 'N/A'}</span>
                    </div>
                  </>
                )}
                
                {selectedEvent.type === 'ANPR_MATCH' && (
                  <>
                    <div className="meta-item" style={{ color: 'var(--color-brand)' }}>
                      <label>LICENSE PLATE</label>
                      <span>{selectedEvent.metadata?.plate_text || 'UNKNOWN'}</span>
                    </div>
                  </>
                )}
              </div>

              {canOperate && (
                <div className="event-actions">
                  <SectionHeader title="Operator Action" />
                  <div className="action-buttons">
                    <PrimaryButton 
                      onClick={() => updateEventStatus('CONFIRMED')}
                      disabled={actionLoading}
                      style={{ backgroundColor: '#2E7D32', borderColor: '#2E7D32' }}
                    >
                      CONFIRM
                    </PrimaryButton>
                    <SecondaryButton 
                      onClick={() => updateEventStatus('FALSE_ALARM')}
                      disabled={actionLoading}
                    >
                      FALSE ALARM
                    </SecondaryButton>
                    <SecondaryButton 
                      onClick={() => updateEventStatus('NEEDS_REVIEW')}
                      disabled={actionLoading}
                    >
                      NEEDS REVIEW
                    </SecondaryButton>
                  </div>
                </div>
              )}
              
              {Object.keys(selectedEvent.metadata || {}).length > 0 && (
                <div className="event-raw-meta">
                  <SectionHeader title="Raw Metadata" />
                  <pre>{JSON.stringify(selectedEvent.metadata, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </Drawer>
      </div>
    </PageContainer>
  );
};
