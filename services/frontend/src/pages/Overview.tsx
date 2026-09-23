import React from 'react';
import { useNavigate } from 'react-router-dom';
import { PrimaryButton, SecondaryButton } from '../components/ui/Buttons';
import { Panel } from '../components/ui/Panel';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Activity, Camera, Eye, Zap, Search, Bell, AlertTriangle } from 'lucide-react';
import './Overview.css';

export const Overview: React.FC = () => {
  const navigate = useNavigate();

  const handleOpenMissionControl = () => {
    navigate('/dashboard');
  };

  const handleExploreArchitecture = () => {
    document.getElementById('architecture')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="overview-container">
      {/* SECTION 1: HERO */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="eyebrow">INTELLIGENT BORDER VIDEO ANALYTICS PLATFORM</div>
          <h1 className="main-headline">TURN EXISTING CCTV INTO BORDER INTELLIGENCE</h1>
          <p className="supporting-copy">
            Transform existing CCTV infrastructure into an AI-powered surveillance network for detection, tracking, identity analysis and real-time response.
          </p>
          <div className="hero-actions">
            <PrimaryButton onClick={handleOpenMissionControl} className="cta-btn pulse">
              OPEN MISSION CONTROL →
            </PrimaryButton>
            <SecondaryButton onClick={handleExploreArchitecture} className="cta-btn">
              EXPLORE ARCHITECTURE
            </SecondaryButton>
          </div>
        </div>
        <div className="hero-visual">
          {/* Mock Mission Control Panel */}
          <Panel className="mock-console">
            <div className="console-header">
              <span>BOP-07 LIVE FEED</span>
              <StatusBadge status="ACTIVE" />
            </div>
            <div className="console-video-placeholder">
              <div className="tracking-box">
                <span className="track-label">PERSON #102 | 0.94</span>
              </div>
              <div className="tracking-box vehicle">
                <span className="track-label">VEHICLE #103 | 0.88</span>
              </div>
              <div className="virtual-fence-line" />
            </div>
            <div className="console-telemetry">
              <div className="t-row">
                <span>SYS.FPS</span>
                <span className="t-val">30.0</span>
              </div>
              <div className="t-row">
                <span>LAST.EVT</span>
                <span className="t-val warning">VIRTUAL FENCE INTRUSION</span>
              </div>
            </div>
          </Panel>
        </div>
      </section>

      {/* SECTION 2: PROBLEM */}
      <section className="problem-section">
        <h2 className="section-headline">CCTV RECORDS.<br/>IBVAP UNDERSTANDS.</h2>
        <div className="comparison-grid">
          <Panel className="comparison-panel traditional">
            <div className="comp-title">TRADITIONAL CCTV</div>
            <ul className="comp-list">
              <li>Live feed</li>
              <li>Manual monitoring</li>
              <li>Multiple screens</li>
              <li>Missed events</li>
              <li>No contextual intelligence</li>
            </ul>
          </Panel>
          <Panel className="comparison-panel ibvap-side">
            <div className="comp-title">IBVAP</div>
            <ul className="comp-list">
              <li>Detect</li>
              <li>Track</li>
              <li>Analyze</li>
              <li>Reason</li>
              <li>Alert</li>
              <li>Review</li>
            </ul>
          </Panel>
        </div>
      </section>

      {/* SECTION 3: TECHNICAL FLOW */}
      <section className="flow-section" id="architecture">
        <h2 className="section-headline">FROM VIDEO FRAME TO ACTIONABLE EVENT</h2>
        <div className="technical-flow">
          <div className="flow-node">CCTV</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node">SCHEDULER</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node highlight">YOLO</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node highlight">BYTETRACK</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node conditional">CONDITIONAL AI</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node">RULE ENGINE</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node alert-node">EVENT</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node">EVIDENCE</div>
          <div className="flow-arrow">→</div>
          <div className="flow-node operator">OPERATOR</div>
        </div>
        <div className="flow-annotations">
          <span className="annotation">CPU-FIRST</span>
          <span className="annotation">CONDITIONAL INFERENCE</span>
          <span className="annotation">EVIDENCE-FIRST</span>
        </div>
      </section>

      {/* SECTION 4: CAPABILITIES */}
      <section className="capabilities-section">
        <div className="cap-grid">
          <Panel className="cap-card">
            <Eye size={20} className="cap-icon" />
            <h3>HUMAN TRACKING</h3>
            <p>Persistent trajectory reasoning across video frames.</p>
          </Panel>
          <Panel className="cap-card">
            <Camera size={20} className="cap-icon" />
            <h3>VEHICLE ANALYTICS</h3>
            <p>Detect and track vehicles crossing restricted zones.</p>
          </Panel>
          <Panel className="cap-card">
            <Search size={20} className="cap-icon" />
            <h3>ANPR</h3>
            <p>Conditional Indian license plate recognition and formatting.</p>
          </Panel>
          <Panel className="cap-card">
            <Activity size={20} className="cap-icon" />
            <h3>FACE WATCHLIST</h3>
            <p>Identify watchlisted individuals via embedding search.</p>
          </Panel>
          <Panel className="cap-card">
            <AlertTriangle size={20} className="cap-icon" />
            <h3>VIRTUAL FENCE</h3>
            <p>Interactive polygon drawing for intrusion detection.</p>
          </Panel>
          <Panel className="cap-card">
            <Zap size={20} className="cap-icon" />
            <h3>LOITERING</h3>
            <p>Alert when subjects remain in a designated area for too long.</p>
          </Panel>
          <Panel className="cap-card">
            <Eye size={20} className="cap-icon" />
            <h3>NIGHT MOVEMENT</h3>
            <p>Adaptive low-light enhancement for robust detection.</p>
          </Panel>
          <Panel className="cap-card">
            <Bell size={20} className="cap-icon" />
            <h3>EVENT INTELLIGENCE</h3>
            <p>Normalized events converging on a centralized message bus.</p>
          </Panel>
        </div>
      </section>

      {/* SECTION 5: ARCHITECTURE */}
      <section className="arch-section">
        <h2 className="section-headline">THE INTELLIGENCE IS IN THE PLATFORM</h2>
        <div className="arch-principles">
          <div className="arch-principle">
            <h4>COMPUTE-AWARE SCHEDULING</h4>
            <p>Shared inference budget to prioritize high-value frames.</p>
          </div>
          <div className="arch-principle">
            <h4>CONDITIONAL AI</h4>
            <p>Expensive models run only when strictly relevant to the track.</p>
          </div>
          <div className="arch-principle">
            <h4>PERSISTENT TRACKS</h4>
            <p>YOLO + ByteTrack feed continuous trajectory reasoning.</p>
          </div>
          <div className="arch-principle">
            <h4>NORMALIZED EVENTS</h4>
            <p>All intelligence converges on one strict event contract.</p>
          </div>
          <div className="arch-principle">
            <h4>EVIDENCE-FIRST ALERTS</h4>
            <p>Alert + context + supporting media for the operator.</p>
          </div>
        </div>
      </section>

      {/* SECTION 6: CPU-FIRST */}
      <section className="cpu-section">
        <h2 className="section-headline">DESIGNED FOR REALISTIC EDGE CONSTRAINTS</h2>
        <div className="cpu-flow">
          <div className="cpu-step">CPU</div>
          <div className="cpu-arrow">↓</div>
          <div className="cpu-step">Lightweight models</div>
          <div className="cpu-arrow">↓</div>
          <div className="cpu-step">Frame sampling</div>
          <div className="cpu-arrow">↓</div>
          <div className="cpu-step">Conditional inference</div>
          <div className="cpu-arrow">↓</div>
          <div className="cpu-step">Rules</div>
          <div className="cpu-arrow">↓</div>
          <div className="cpu-step">Events</div>
        </div>
        <p className="technical-note">
          "Prototype runs on CPU with webcam and prerecorded camera feeds; the camera abstraction is designed for later RTSP deployment."
        </p>
      </section>

      {/* SECTION 7: LIVE MISSION CONTROL PREVIEW */}
      <section className="preview-section">
        <Panel className="large-preview">
          <div className="preview-layout">
            <div className="preview-cams">
              <div className="p-cam" />
              <div className="p-cam" />
              <div className="p-cam" />
              <div className="p-cam" />
            </div>
            <div className="preview-sidebar">
              <div className="p-alert">
                <span className="p-alert-title">VIRTUAL FENCE INTRUSION</span>
                <span className="p-alert-meta">BOP-07 | TRACK #184 | CONFIDENCE 0.94</span>
              </div>
            </div>
          </div>
        </Panel>
      </section>

      {/* SECTION 8: DEPLOYMENT CONTINUITY */}
      <section className="deployment-section">
        <div className="deployment-split">
          <Panel className="deploy-box now">
            <div className="deploy-label">NOW</div>
            <ul className="deploy-list">
              <li>Laptop</li>
              <li>Webcam / Video Files</li>
              <li>Docker Compose</li>
              <li>CPU</li>
            </ul>
          </Panel>
          <Panel className="deploy-box later">
            <div className="deploy-label">FUTURE</div>
            <ul className="deploy-list">
              <li>RTSP / IP CCTV</li>
              <li>Edge Compute</li>
              <li>Central C2</li>
              <li>Store-and-forward</li>
            </ul>
          </Panel>
        </div>
      </section>

      {/* SECTION 9: CTA */}
      <section className="cta-section">
        <h2 className="section-headline">FROM EXISTING CCTV<br/>TO INTELLIGENT BORDER RESPONSE</h2>
        <div className="hero-actions center-actions">
          <PrimaryButton onClick={handleOpenMissionControl} className="cta-btn pulse">
            OPEN MISSION CONTROL
          </PrimaryButton>
          <SecondaryButton onClick={handleExploreArchitecture} className="cta-btn">
            VIEW TECHNICAL ARCHITECTURE
          </SecondaryButton>
        </div>
        <div className="bottom-logo">
          IBVAP<br/>
          <span>Intelligent Border Video Analytics Platform</span>
        </div>
      </section>
    </div>
  );
};
