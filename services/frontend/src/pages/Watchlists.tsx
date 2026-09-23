import React, { useState, useEffect, useRef } from 'react';
import { PageContainer } from '../components/layout/PageContainer';
import { Panel } from '../components/ui/Panel';
import { SectionHeader } from '../components/ui/SectionHeader';
import { DataTable } from '../components/ui/DataTable';
import { StatusBadge } from '../components/ui/StatusBadge';
import { PrimaryButton } from '../components/ui/Buttons';
import { Trash2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './Watchlists.css';

interface FaceEntry {
  id: number;
  label: string;
  reference: string;
  threshold: number;
  enabled: boolean;
  created_at: string;
}

interface PlateEntry {
  id: number;
  plate_text: string;
  reason: string;
  enabled: boolean;
  created_at: string;
}

export const Watchlists: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'FACES' | 'PLATES'>('FACES');
  const { canAdmin, role } = useAuth();
  
  // Data
  const [faces, setFaces] = useState<FaceEntry[]>([]);
  const [plates, setPlates] = useState<PlateEntry[]>([]);
  
  // Forms
  const [faceLabel, setFaceLabel] = useState('');
  const [faceThreshold, setFaceThreshold] = useState(0.6);
  const [faceEnabled, setFaceEnabled] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [plateText, setPlateText] = useState('');
  const [plateReason, setPlateReason] = useState('');
  const [plateEnabled, setPlateEnabled] = useState(true);
  
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchFaces();
    fetchPlates();
  }, []);

  const fetchFaces = async () => {
    try {
      const res = await fetch('/api/v1/watchlists/faces');
      if (res.ok) setFaces(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchPlates = async () => {
    try {
      const res = await fetch('/api/v1/watchlists/plates');
      if (res.ok) setPlates(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const handleFaceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file || !faceLabel) {
      alert('File and label are required');
      return;
    }
    
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('label', faceLabel);
    formData.append('threshold', faceThreshold.toString());
    formData.append('enabled', faceEnabled.toString());

    try {
      const res = await fetch('/api/v1/watchlists/faces', {
        method: 'POST',
        headers: {
          'X-User-Role': role
        },
        body: formData
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to enroll face');
      }
      
      // Reset
      setFaceLabel('');
      setFaceThreshold(0.6);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchFaces();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePlateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!plateText) return;
    
    setLoading(true);
    try {
      const res = await fetch('/api/v1/watchlists/plates', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Role': role
        },
        body: JSON.stringify({
          plate_text: plateText,
          reason: plateReason,
          enabled: plateEnabled
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to enroll plate');
      }
      
      setPlateText('');
      setPlateReason('');
      fetchPlates();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteFace = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/watchlists/faces/${id}`, { 
        method: 'DELETE',
        headers: { 'X-User-Role': role }
      });
      if (res.ok) fetchFaces();
    } catch (e) {
      console.error(e);
    }
  };

  const deletePlate = async (id: number) => {
    try {
      const res = await fetch(`/api/v1/watchlists/plates/${id}`, { 
        method: 'DELETE',
        headers: { 'X-User-Role': role }
      });
      if (res.ok) fetchPlates();
    } catch (e) {
      console.error(e);
    }
  };

  const faceColumns = [
    { key: 'id', header: 'ID' },
    { key: 'label', header: 'LABEL' },
    { key: 'threshold', header: 'THRESHOLD' },
    { 
      key: 'enabled', 
      header: 'STATUS',
      render: (f: FaceEntry) => <StatusBadge status={f.enabled ? 'ACTIVE' : 'INACTIVE'} />
    },
    { 
      key: 'created_at', 
      header: 'ENROLLED',
      render: (f: FaceEntry) => new Date(f.created_at).toLocaleDateString()
    },
    {
      key: 'actions',
      header: '',
      render: (f: FaceEntry) => canAdmin ? (
        <button className="icon-btn" onClick={() => deleteFace(f.id)}>
          <Trash2 size={14} />
        </button>
      ) : null
    }
  ];

  const plateColumns = [
    { key: 'plate_text', header: 'PLATE' },
    { key: 'reason', header: 'REASON' },
    { 
      key: 'enabled', 
      header: 'STATUS',
      render: (p: PlateEntry) => <StatusBadge status={p.enabled ? 'ACTIVE' : 'INACTIVE'} />
    },
    { 
      key: 'created_at', 
      header: 'ENROLLED',
      render: (p: PlateEntry) => new Date(p.created_at).toLocaleDateString()
    },
    {
      key: 'actions',
      header: '',
      render: (p: PlateEntry) => canAdmin ? (
        <button className="icon-btn" onClick={() => deletePlate(p.id)}>
          <Trash2 size={14} />
        </button>
      ) : null
    }
  ];

  return (
    <PageContainer>
      <div className="watchlists-container">
        <div className="watchlists-tabs">
          <button 
            className={`tab-btn ${activeTab === 'FACES' ? 'active' : ''}`}
            onClick={() => setActiveTab('FACES')}
          >
            FACE WATCHLIST
          </button>
          <button 
            className={`tab-btn ${activeTab === 'PLATES' ? 'active' : ''}`}
            onClick={() => setActiveTab('PLATES')}
          >
            PLATE WATCHLIST
          </button>
        </div>

        <div className="watchlists-content">
          {canAdmin && (
            <Panel className="enrollment-panel">
              <SectionHeader title={`Enroll New ${activeTab === 'FACES' ? 'Face' : 'Plate'}`} />
              
              {activeTab === 'FACES' ? (
                <form className="enroll-form" onSubmit={handleFaceSubmit}>
                  <div className="form-group">
                    <label>Reference Image</label>
                    <input type="file" ref={fileInputRef} accept="image/*" />
                  </div>
                  <div className="form-group">
                    <label>Subject Label / Name</label>
                    <input 
                      type="text" 
                      value={faceLabel} 
                      onChange={e => setFaceLabel(e.target.value)} 
                      placeholder="e.g. John Doe"
                    />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Match Threshold</label>
                      <input 
                        type="number" 
                        step="0.01" 
                        min="0" max="1"
                        value={faceThreshold} 
                        onChange={e => setFaceThreshold(parseFloat(e.target.value) || 0.6)} 
                      />
                    </div>
                    <div className="form-group checkbox-group">
                      <label>Enabled</label>
                      <input 
                        type="checkbox" 
                        checked={faceEnabled} 
                        onChange={e => setFaceEnabled(e.target.checked)} 
                      />
                    </div>
                  </div>
                  <PrimaryButton type="submit" disabled={loading} style={{ marginTop: '16px' }}>
                    {loading ? 'ENROLLING...' : 'ENROLL FACE'}
                  </PrimaryButton>
                </form>
              ) : (
                <form className="enroll-form" onSubmit={handlePlateSubmit}>
                  <div className="form-group">
                    <label>Plate Text</label>
                    <input 
                      type="text" 
                      value={plateText} 
                      onChange={e => setPlateText(e.target.value)} 
                      placeholder="e.g. MH01AB1234"
                    />
                  </div>
                  <div className="form-group">
                    <label>Reason / Owner</label>
                    <input 
                      type="text" 
                      value={plateReason} 
                      onChange={e => setPlateReason(e.target.value)} 
                      placeholder="e.g. Stolen Vehicle"
                    />
                  </div>
                  <div className="form-group checkbox-group">
                    <label>Enabled</label>
                    <input 
                      type="checkbox" 
                      checked={plateEnabled} 
                      onChange={e => setPlateEnabled(e.target.checked)} 
                    />
                  </div>
                  <PrimaryButton type="submit" disabled={loading} style={{ marginTop: '16px' }}>
                    {loading ? 'ENROLLING...' : 'ENROLL PLATE'}
                  </PrimaryButton>
                </form>
              )}
            </Panel>
          )}

          <div className="enrolled-list">
            <Panel className="list-panel">
              <SectionHeader title="Enrolled Entities" />
              <div className="table-wrapper">
                {activeTab === 'FACES' ? (
                  <DataTable columns={faceColumns} data={faces} />
                ) : (
                  <DataTable columns={plateColumns} data={plates} />
                )}
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
