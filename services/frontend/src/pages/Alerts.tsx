import React, { useState, useEffect } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { Panel } from '../components/ui/Panel';
import { SectionHeader } from '../components/ui/SectionHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { SeverityBadge } from '../components/ui/SeverityBadge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { PrimaryButton, SecondaryButton } from '../components/ui/Buttons';
import { useAuth } from '../contexts/AuthContext';
import type { EventData } from '../components/ui/EventRow';
import './Alerts.css';

export const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<EventData | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const { canOperate, role } = useAuth();

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      // Fetch high severity events for the alerts page
      // Normally we'd filter on backend, but since the endpoint doesn't support severity filter yet, 
      // we fetch recent and filter locally, or just display all. Let's fetch all and show them for now.
      const res = await fetch(`/api/v1/events?size=100`);
      if (!res.ok) throw new Error('Failed to fetch alerts');
      const data = await res.json();
      
      // Filter for CRITICAL or WARNING (or just show all if none exist for demo)
      const highSeverity = data.data.filter((e: EventData) => e.severity === 'CRITICAL' || e.severity === 'WARNING');
      const displayAlerts = highSeverity.length > 0 ? highSeverity : data.data; // fallback for prototype
      
      setAlerts(displayAlerts);
      if (displayAlerts.length > 0 && !selectedAlert) {
        setSelectedAlert(displayAlerts[0]);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
    // In a real app, we'd hook up a WebSocket here for live alerts
    const interval = setInterval(fetchAlerts, 10000);
    return () => clearInterval(interval);
  }, []);

  const updateAlertStatus = async (status: string) => {
    if (!selectedAlert) return;
    setActionLoading(true);
    try {
      const res = await fetch(`/api/v1/events/${selectedAlert.event_id}`, {
        method: 'PATCH',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Role': role
        },
        body: JSON.stringify({ status })
      });
      if (!res.ok) throw new Error('Failed to update alert');
      
      const updated = await res.json();
      
      setAlerts(alerts.map(a => a.event_id === updated.data.event_id ? updated.data : a));
      setSelectedAlert(updated.data);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <PageContainer>
      <div className="alerts-page-container">
        
        {/* Left Pane: Alert List */}
        <div className="alerts-list-pane">
          <div className="alerts-list-header">
            <h2>Active Alerts</h2>
            <div className="badge">{alerts.length} Total</div>
          </div>
          
          <div className="alerts-feed">
            {loading && alerts.length === 0 ? (
              <LoadingState message="Fetching alerts..." />
            ) : error ? (
              <ErrorState message={error} />
            ) : alerts.length === 0 ? (
              <div className="alerts-empty-state">No alerts to display.</div>
            ) : (
              alerts.map((alert) => (
                <div 
                  key={alert.event_id}
                  className={`event-row ${selectedAlert?.event_id === alert.event_id ? 'selected' : ''}`}
                  onClick={() => setSelectedAlert(alert)}
                >
                  <div className="event-time">
                    {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </div>
                  <div className="event-details">
                    <div className="event-header">
                      <span className="event-type">{alert.type.replace(/_/g, ' ')}</span>
                      <SeverityBadge severity={alert.severity} />
                    </div>
                    <div className="event-camera">{alert.camera_id}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Pane: Alert Details */}
        {selectedAlert ? (
          <div className="alerts-detail-pane">
            <Panel className="alert-snapshot-panel no-padding">
              {selectedAlert.media_ref ? (
                <div className="alert-snapshot-card">
                  <img src={`/api/v1/media/${selectedAlert.media_ref}`} alt="Alert Snapshot" className="alert-snapshot-image" />
                </div>
              ) : (
                <div className="alert-snapshot-card">
                  <div className="alert-no-snapshot">NO MEDIA AVAILABLE</div>
                </div>
              )}
            </Panel>

            <Panel className="alert-details-panel">
              <SectionHeader title="Alert Metadata" />
              <div className="alert-metadata-grid">
                <div className="meta-box">
                  <label>EVENT TYPE</label>
                  <span className="meta-val">{selectedAlert.type.replace(/_/g, ' ')}</span>
                </div>
                <div className="meta-box">
                  <label>TIMESTAMP</label>
                  <span className="meta-val">{new Date(selectedAlert.timestamp).toLocaleString()}</span>
                </div>
                <div className="meta-box">
                  <label>CAMERA SOURCE</label>
                  <span className="meta-val">{selectedAlert.camera_id}</span>
                </div>
                <div className="meta-box">
                  <label>CURRENT STATUS</label>
                  <StatusBadge status={selectedAlert.status || 'NEW'} />
                </div>
                {selectedAlert.type === 'FACE_MATCH' && (
                  <div className="meta-box">
                    <label>MATCHED IDENTITY</label>
                    <span className="meta-val" style={{color: 'var(--accent-orange)'}}>
                      {selectedAlert.metadata?.subject_id || 'UNKNOWN'}
                    </span>
                  </div>
                )}
                {selectedAlert.type === 'ANPR_MATCH' && (
                  <div className="meta-box">
                    <label>LICENSE PLATE</label>
                    <span className="meta-val" style={{color: 'var(--accent-orange)'}}>
                      {selectedAlert.metadata?.plate_text || 'UNKNOWN'}
                    </span>
                  </div>
                )}
              </div>

              {canOperate && (
                <div className="alert-actions-panel">
                  <PrimaryButton 
                    onClick={() => updateAlertStatus('CONFIRMED')}
                    disabled={actionLoading}
                    style={{ backgroundColor: '#00ff88', color: '#000', borderColor: '#00ff88', boxShadow: '0 4px 10px rgba(0,255,136,0.3)' }}
                  >
                    CONFIRM THREAT
                  </PrimaryButton>
                  <SecondaryButton 
                    onClick={() => updateAlertStatus('FALSE_ALARM')}
                    disabled={actionLoading}
                  >
                    MARK FALSE ALARM
                  </SecondaryButton>
                  <SecondaryButton 
                    onClick={() => updateAlertStatus('RESOLVED')}
                    disabled={actionLoading}
                  >
                    RESOLVE
                  </SecondaryButton>
                </div>
              )}
            </Panel>
          </div>
        ) : (
          <div className="alerts-empty-state">
            Select an alert from the feed to view details.
          </div>
        )}
      </div>
    </PageContainer>
  );
};
