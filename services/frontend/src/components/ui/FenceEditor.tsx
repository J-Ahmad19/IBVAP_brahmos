import React, { useState, useEffect, useRef } from 'react';
import { PrimaryButton, SecondaryButton } from './Buttons';
import { Trash2 } from 'lucide-react';
import './FenceEditor.css';

interface Point {
  x: number;
  y: number;
}

interface Fence {
  id?: number;
  camera_id: string;
  name: string;
  polygon: { points: [number, number][] };
  direction: string;
  debounce_frames: number;
  enabled: boolean;
}

interface FenceEditorProps {
  cameraId: string;
}

export const FenceEditor: React.FC<FenceEditorProps> = ({ cameraId }) => {
  
  const [activeFence, setActiveFence] = useState<Fence | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [draggedPointIdx, setDraggedPointIdx] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  
  // States
  const [isDrawing, setIsDrawing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchFences();
  }, [cameraId]);

  const [, setFences] = useState<any[]>([]);
  const fetchFences = async () => {
    try {
      const res = await fetch(`/api/v1/fences/${cameraId}`);
      if (res.ok) {
        const data = await res.json();
        setFences(data);
        if (data.length > 0) {
          loadFence(data[0]);
        }
      }
    } catch (err) {
      console.error('Error fetching fences:', err);
    }
  };

  const loadFence = (fence: Fence) => {
    setActiveFence(fence);
    const pts = (fence.polygon?.points || []).map(p => ({ x: p[0], y: p[1] }));
    setPoints(pts);
    setIsDrawing(false);
  };

  const getSvgCoordinates = (e: React.MouseEvent | React.TouchEvent) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const CTM = svgRef.current.getScreenCTM();
    if (!CTM) return { x: 0, y: 0 };

    let clientX, clientY;
    if ('touches' in e) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = (e as React.MouseEvent).clientX;
      clientY = (e as React.MouseEvent).clientY;
    }

    return {
      x: (clientX - CTM.e) / CTM.a,
      y: (clientY - CTM.f) / CTM.d
    };
  };

  const handleSvgClick = (e: React.MouseEvent) => {
    if (!isDrawing) return;
    
    // Prevent adding point if we're clicking on an existing vertex (handled by onMouseDown)
    if (draggedPointIdx !== null) return;

    const coords = getSvgCoordinates(e);
    // Normalize coordinates (0-1)
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const normalized = {
      x: coords.x / rect.width,
      y: coords.y / rect.height
    };
    
    setPoints([...points, normalized]);
  };

  const handlePointerDown = (idx: number, e: React.MouseEvent | React.TouchEvent) => {
    e.stopPropagation();
    setDraggedPointIdx(idx);
  };

  const handlePointerMove = (e: React.MouseEvent | React.TouchEvent) => {
    if (draggedPointIdx === null) return;
    
    const coords = getSvgCoordinates(e);
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const normalized = {
      x: Math.max(0, Math.min(1, coords.x / rect.width)),
      y: Math.max(0, Math.min(1, coords.y / rect.height))
    };

    const newPoints = [...points];
    newPoints[draggedPointIdx] = normalized;
    setPoints(newPoints);
  };

  const handlePointerUp = () => {
    setDraggedPointIdx(null);
  };

  const startNewFence = () => {
    setIsDrawing(true);
    setPoints([]);
    setActiveFence(null);
  };

  const saveFence = async () => {
    if (points.length < 3) {
      alert("A fence must have at least 3 points.");
      return;
    }

    setIsSaving(true);
    const payload = {
      camera_id: cameraId,
      name: activeFence?.name || "Zone 1",
      polygon: { points: points.map(p => [p.x, p.y]) },
      direction: activeFence?.direction || "BOTH",
      debounce_frames: activeFence?.debounce_frames || 3,
      enabled: true
    };

    try {
      let res;
      if (activeFence?.id) {
        res = await fetch(`/api/v1/fences/${activeFence.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch(`/api/v1/fences`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      
      if (res.ok) {
        setIsDrawing(false);
        fetchFences();
      } else {
        const err = await res.json();
        alert(`Error saving fence: ${err.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Error saving fence', err);
    } finally {
      setIsSaving(false);
    }
  };

  const deleteFence = async () => {
    if (!activeFence?.id) return;
    try {
      const res = await fetch(`/api/v1/fences/${activeFence.id}`, { method: 'DELETE' });
      if (res.ok) {
        setPoints([]);
        setActiveFence(null);
        fetchFences();
      }
    } catch (err) {
      console.error('Error deleting fence', err);
    }
  };

  const cancelDrawing = () => {
    setIsDrawing(false);
    if (activeFence) {
      loadFence(activeFence);
    } else {
      setPoints([]);
    }
  };

  // Convert normalized points back to SVG coordinates for rendering
  const renderPoints = () => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return [];
    return points.map(p => ({ x: p.x * rect.width, y: p.y * rect.height }));
  };

  const absolutePoints = svgRef.current ? renderPoints() : [];
  const polygonPointsString = absolutePoints.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <div className="fence-editor-container">
      <div className="fence-editor-canvas">
        <svg 
          ref={svgRef}
          className="fence-svg"
          onClick={handleSvgClick}
          onMouseMove={handlePointerMove}
          onMouseUp={handlePointerUp}
          onMouseLeave={handlePointerUp}
          onTouchMove={handlePointerMove}
          onTouchEnd={handlePointerUp}
        >
          {absolutePoints.length > 0 && (
            <polygon 
              points={polygonPointsString} 
              className={`fence-polygon ${isDrawing ? 'drawing' : ''}`}
            />
          )}
          
          {absolutePoints.map((p, idx) => (
            <circle
              key={idx}
              cx={p.x}
              cy={p.y}
              r={6}
              className="fence-vertex"
              onMouseDown={(e) => handlePointerDown(idx, e)}
              onTouchStart={(e) => handlePointerDown(idx, e)}
            />
          ))}
        </svg>
        
        {isDrawing && points.length === 0 && (
          <div className="fence-instruction">
            Click on the preview to start drawing a fence.
          </div>
        )}
      </div>
      
      <div className="fence-editor-controls">
        {!isDrawing && !activeFence && (
          <PrimaryButton onClick={startNewFence}>DRAW FENCE</PrimaryButton>
        )}
        
        {!isDrawing && activeFence && (
          <>
            <SecondaryButton onClick={() => setIsDrawing(true)}>EDIT POINTS</SecondaryButton>
            <button className="icon-btn delete-btn" onClick={deleteFence}>
              <Trash2 size={16} />
            </button>
          </>
        )}
        
        {isDrawing && (
          <>
            <SecondaryButton onClick={cancelDrawing}>CANCEL</SecondaryButton>
            <PrimaryButton onClick={saveFence} disabled={isSaving || points.length < 3}>
              {isSaving ? 'SAVING...' : 'SAVE'}
            </PrimaryButton>
          </>
        )}
      </div>
    </div>
  );
};
