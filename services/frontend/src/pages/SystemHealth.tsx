import React, { useState, useEffect } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { Panel } from '../components/ui/Panel';
import { SectionHeader } from '../components/ui/SectionHeader';
import { TelemetryCard } from '../components/ui/TelemetryCard';
import { LoadingState } from '../components/ui/LoadingState';
import { ErrorState } from '../components/ui/ErrorState';
import './SystemHealth.css';

interface HealthMetrics {
  active_cameras: number;
  total_cameras: number;
  inference_fps: string | number;
  cpu_usage: string | number;
  queue_depth: string | number;
  total_events: number;
}

interface ServicesHealth {
  FastAPI: string;
  PostgreSQL: string;
  Redis: string;
  Qdrant: string;
  MinIO: string;
}

interface HealthData {
  status: string;
  metrics: HealthMetrics;
  services: ServicesHealth;
}

export const SystemHealth: React.FC = () => {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/v1/system/health');
      if (!res.ok) throw new Error('Failed to fetch system health');
      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // Poll every 10 seconds
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch(status.toUpperCase()) {
      case 'HEALTHY':
      case 'ONLINE':
      case 'ACTIVE':
        return '#2E7D32'; // green
      case 'DEGRADED':
        return 'var(--accent-orange)';
      case 'FAILED':
      case 'OFFLINE':
      case 'ERROR':
        return 'var(--primary-red)';
      default:
        return 'var(--text-slate)'; // unavailable/unknown
    }
  };

  if (loading && !data) return <LoadingState message="FETCHING SYSTEM DIAGNOSTICS..." />;
  if (error && !data) return <ErrorState message={error} />;
  if (!data) return null;

  return (
    <PageContainer>
      <div className="system-health-container">
        
        <div className="system-header-panel">
          <SectionHeader title="System Status" />
          <div className="system-overall-status">
            <div 
              className="status-indicator" 
              style={{ backgroundColor: getStatusColor(data.status) }}
            />
            <span style={{ color: getStatusColor(data.status), fontWeight: 'bold' }}>
              {data.status.toUpperCase()}
            </span>
          </div>
        </div>

        <SectionHeader title="Core Telemetry" />
        <div className="telemetry-grid">
          <TelemetryCard 
            title="ACTIVE CAMERAS" 
            value={`${data.metrics.active_cameras} / ${data.metrics.total_cameras}`} 
          />
          <TelemetryCard 
            title="TOTAL EVENTS" 
            value={data.metrics.total_events} 
          />
          <TelemetryCard 
            title="INFERENCE FPS" 
            value={data.metrics.inference_fps} 
          />
          <TelemetryCard 
            title="CPU USAGE" 
            value={data.metrics.cpu_usage} 
            unit={typeof data.metrics.cpu_usage === 'number' ? '%' : ''}
          />
          <TelemetryCard 
            title="QUEUE DEPTH" 
            value={data.metrics.queue_depth} 
          />
        </div>

        <SectionHeader title="Service Health" />
        <div className="services-grid">
          {Object.entries(data.services).map(([service, status]) => (
            <Panel key={service} className="service-panel">
              <div className="service-name">{service}</div>
              <div className="service-status" style={{ color: getStatusColor(status as string) }}>
                {String(status).toUpperCase()}
              </div>
            </Panel>
          ))}
        </div>

      </div>
    </PageContainer>
  );
};
