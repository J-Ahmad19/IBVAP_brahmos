import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { Panel } from '../components/ui/Panel';
import { SectionHeader } from '../components/ui/SectionHeader';
import { PrimaryButton, SecondaryButton } from '../components/ui/Buttons';
import { StatusBadge } from '../components/ui/StatusBadge';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import { EventRow, type EventData } from '../components/ui/EventRow';
import { FenceEditor } from '../components/ui/FenceEditor';
import { useAuth } from '../contexts/AuthContext';
import './CameraDetail.css';

interface CameraConfig {
  id: string;
  name: string;
  location: string;
  rtsp_url: string;
  enabled: boolean;
  priority: number;
}

export const CameraDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [config, setConfig] = useState<CameraConfig | null>(null);
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { canAdmin, role } = useAuth();

  useEffect(() => {
    const fetchCamera = async () => {
      try {
        const [camRes, eventsRes] = await Promise.all([
          fetch(`/api/v1/cameras/${id}`),
          fetch(`/api/v1/events/?camera_id=${id}&size=10`)
        ]);

        if (!camRes.ok) throw new Error('Camera not found');
        
        const camData = await camRes.json();
        let evtsData = { data: [] };
        if (eventsRes.ok) {
          evtsData = await eventsRes.json();
        }

        setConfig(camData);
        setEvents(evtsData.data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchCamera();
  }, [id]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    
    setSaving(true);
    try {
      const res = await fetch(`/api/v1/cameras/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': role
        },
        body: JSON.stringify({
          name: config.name,
          location: config.location,
          rtsp_url: config.rtsp_url,
          enabled: config.enabled,
          priority: config.priority
        }),
      });

      if (!res.ok) throw new Error('Failed to save configuration');
      
      // Optionally show a toast here
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState message="LOADING CAMERA DETAILS..." />;
  if (error || !config) return <ErrorState message={error || "Camera not found"} />;

  return (
    <PageContainer>
      <div className="camera-detail-header">
        <div className="camera-detail-title">
          <h2>{config.name}</h2>
          <span className="camera-id-badge">{config.id}</span>
          <StatusBadge status={config.enabled ? 'ONLINE' : 'OFFLINE'} />
        </div>
        <SecondaryButton onClick={() => navigate('/cameras')}>BACK</SecondaryButton>
      </div>

      <div className="camera-detail-grid">
        <div className="camera-detail-main">
          <Panel className="camera-preview-panel" noPadding>
            <div className="camera-preview-wrapper">
              {/* This is the large camera preview and fence editor placeholder */}
              <img 
                src={`/api/v1/cameras/${id}/stream`} 
                alt={config.name} 
                style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
              />
              
              <div className="preview-overlay">
                <div className="overlay-metrics">
                  <span>FPS: 30</span>
                  <span>TRK: 2</span>
                </div>
              </div>
            </div>
          </Panel>

          {canAdmin && (
            <Panel>
              <SectionHeader title="Fence Editor" />
              <div style={{ height: '300px' }}>
                <FenceEditor cameraId={id || ''} />
              </div>
            </Panel>
          )}
        </div>

        <div className="camera-detail-sidebar">
          {canAdmin && (
            <Panel>
              <SectionHeader title="Configuration" />
              <form className="config-form" onSubmit={handleSave}>
                <div className="form-group">
                  <label>Name</label>
                  <input 
                    type="text" 
                    value={config.name} 
                    onChange={e => setConfig({...config, name: e.target.value})} 
                  />
                </div>
                <div className="form-group">
                  <label>Zone / Location</label>
                  <input 
                    type="text" 
                    value={config.location} 
                    onChange={e => setConfig({...config, location: e.target.value})} 
                  />
                </div>
                <div className="form-group">
                  <label>Source URI (RTSP/HTTP)</label>
                  <input 
                    type="text" 
                    value={config.rtsp_url} 
                    onChange={e => setConfig({...config, rtsp_url: e.target.value})} 
                  />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Priority (1-10)</label>
                    <input 
                      type="number" 
                      min="1" max="10"
                      value={config.priority} 
                      onChange={e => setConfig({...config, priority: parseInt(e.target.value) || 1})} 
                    />
                  </div>
                  <div className="form-group checkbox-group">
                    <label>Enabled</label>
                    <input 
                      type="checkbox" 
                      checked={config.enabled} 
                      onChange={e => setConfig({...config, enabled: e.target.checked})} 
                    />
                  </div>
                </div>
                <PrimaryButton type="submit" disabled={saving} style={{ width: '100%', marginTop: '16px' }}>
                  {saving ? 'SAVING...' : 'SAVE CONFIGURATION'}
                </PrimaryButton>
              </form>
            </Panel>
          )}

          <Panel className="recent-events-panel" noPadding>
            <div style={{ padding: '16px 16px 8px' }}>
              <SectionHeader title="Recent Events" />
            </div>
            <div className="recent-events-list">
              {events.length === 0 ? (
                <div style={{ padding: '16px', color: 'var(--text-slate)', fontSize: '12px', textAlign: 'center' }}>
                  NO RECENT EVENTS
                </div>
              ) : (
                events.map(evt => (
                  <EventRow key={evt.event_id} event={evt} />
                ))
              )}
            </div>
          </Panel>
        </div>
      </div>
    </PageContainer>
  );
};
