import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Activity, 
  Camera, 
  ShieldAlert, 
  Map, 
  Users, 
  BarChart2, 
  Settings,
  LayoutDashboard
} from 'lucide-react';
import './Sidebar.css';

const navItems = [
  { path: '/overview', label: 'Overview', icon: Activity },
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/cameras', label: 'Cameras', icon: Camera },
  { path: '/alerts', label: 'Alerts', icon: ShieldAlert },
  { path: '/events', label: 'Events', icon: Activity },
  { path: '/fences', label: 'Fences', icon: Map },
  { path: '/watchlists', label: 'Watchlists', icon: Users },
  { path: '/analytics', label: 'Analytics', icon: BarChart2 },
  { path: '/system', label: 'System', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="brand-logo">IBVAP</h1>
        <div className="brand-subtitle">MISSION CONTROL</div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink 
              key={item.path} 
              to={item.path} 
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} className="nav-icon" />
              <span className="nav-label">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
      <div className="sidebar-footer">
        <div className="status-indicator online">
          <span className="dot"></span> ONLINE
        </div>
      </div>
    </aside>
  );
};
