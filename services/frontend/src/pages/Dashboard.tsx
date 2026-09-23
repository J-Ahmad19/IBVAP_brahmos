import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { CameraTile, type CameraTileProps } from '../components/ui/CameraTile';
import { AlertFeed } from '../components/ui/AlertFeed';
import type { EventData } from '../components/ui/EventRow';
import { Panel } from '../components/ui/Panel';
import { SectionHeader } from '../components/ui/SectionHeader';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [cameras, setCameras] = useState<CameraTileProps[]>([]);
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [camsRes, evtsRes] = await Promise.all([
          fetch('/api/v1/cameras/'),
          fetch('/api/v1/events/?size=50')
        ]);
        
        if (!camsRes.ok) throw new Error('Failed to fetch cameras');
        if (!evtsRes.ok) throw new Error('Failed to fetch events');
        
        const camsData = await camsRes.json();
        const evtsData = await evtsRes.json();
        
        const mappedCameras = camsData.map((c: any) => ({
          id: c.id,
          name: c.name,
          zone: c.location,
          status: 'ONLINE', // Dummy logic for now
          fps: 30,
          trackCount: Math.floor(Math.random() * 5),
          activeAlerts: 0,
          previewUrl: `/api/v1/cameras/${c.id}/stream`,
          onClick: () => navigate(`/cameras/${c.id}`)
        }));
        
        setCameras(mappedCameras);
        setEvents(evtsData.data || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  // Setup WebSocket for Live Alerts
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use localhost:8000 for local dev if not proxied
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/events`;
    
    // For local dev where vite proxies /api, window.location.host is localhost:5173 
    // We need proxy configured in vite.config.ts for ws to work properly
    wsRef.current = new WebSocket(wsUrl);
    
    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
    };
    
    wsRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setEvents(prev => [data, ...prev].slice(0, 100)); // Keep last 100
      } catch (err) {
        console.error('Error parsing WS message', err);
      }
    };
    
    wsRef.current.onerror = (err) => {
      console.error('WebSocket error', err);
    };
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  if (loading) return <LoadingState message="INITIALIZING DASHBOARD..." />;
  if (error) return <ErrorState message={error} />;

  return (
    <PageContainer>
      <div className="dashboard-grid">
        <div className="dashboard-main">
          <SectionHeader title="Camera Matrix" />
          <div className="camera-matrix">
            {cameras.length === 0 ? (
              <div className="no-cameras">
                NO CAMERAS CONFIGURED
              </div>
            ) : (
              cameras.map(cam => (
                <CameraTile key={cam.id} {...cam} />
              ))
            )}
          </div>
          
          <div className="dashboard-bottom">
            <Panel className="timeline-panel">
              <SectionHeader title="System Health & Timeline" />
              <div className="timeline-content">
                <span className="placeholder-text">TIMELINE DATA PENDING</span>
              </div>
            </Panel>
          </div>
        </div>
        
        <div className="dashboard-sidebar">
          <AlertFeed events={events} />
        </div>
      </div>
    </PageContainer>
  );
};
