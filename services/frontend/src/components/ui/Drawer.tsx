import React from 'react';
import { X } from 'lucide-react';
import './Drawer.css';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export const Drawer: React.FC<DrawerProps> = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer-content">
        <div className="drawer-header">
          <h3 className="drawer-title">{title}</h3>
          <button className="drawer-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="drawer-body">
          {children}
        </div>
      </div>
    </>
  );
};
