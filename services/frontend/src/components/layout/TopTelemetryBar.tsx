import React, { useState, useEffect } from 'react';
import { Clock, Cpu, Activity, AlertTriangle, User } from 'lucide-react';
import { useAuth, type Role } from '../../contexts/AuthContext';
import './TopTelemetryBar.css';

export const TopTelemetryBar: React.FC = () => {
  const [time, setTime] = useState(new Date());
  const { role, setRole } = useAuth();

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="telemetry-bar">
      <div className="telemetry-group">
        <div className="telemetry-item">
          <span className="label">SYS_STATUS</span>
          <span className="value success">NOMINAL</span>
        </div>
        <div className="telemetry-item">
          <span className="label">ACTIVE_CAMS</span>
          <span className="value">4/4</span>
        </div>
      </div>
      
      <div className="telemetry-group">
        <div className="telemetry-item">
          <Activity size={14} className="icon" />
          <span className="label">INF_FPS</span>
          <span className="value">30.2</span>
        </div>
        <div className="telemetry-item">
          <Cpu size={14} className="icon" />
          <span className="label">CPU_LOAD</span>
          <span className="value warning">78%</span>
        </div>
        <div className="telemetry-item">
          <AlertTriangle size={14} className="icon" />
          <span className="label">EVT_RATE</span>
          <span className="value">12/m</span>
        </div>
      </div>
      
      <div className="telemetry-group">
        <div className="telemetry-item">
          <User size={14} className="icon" />
          <span className="label">ROLE</span>
          <select 
            className="role-selector"
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
          >
            <option value="VIEWER">VIEWER</option>
            <option value="OPERATOR">OPERATOR</option>
            <option value="ADMIN">ADMIN</option>
          </select>
        </div>
        <div className="telemetry-item clock">
          <Clock size={14} className="icon" />
          <span className="value">
            {time.toISOString().split('T')[1].substring(0, 8)} Z
          </span>
        </div>
      </div>
    </header>
  );
};
