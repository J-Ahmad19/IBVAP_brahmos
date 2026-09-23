import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from './components/layout/MainLayout';
import { Placeholder } from './pages/Placeholder';

import { Overview } from './pages/Overview';
import { Dashboard } from './pages/Dashboard';
import { CameraDetail } from './pages/CameraDetail';
import { Alerts } from './pages/Alerts';
import { EventExplorer } from './pages/EventExplorer';
import { Watchlists } from './pages/Watchlists';
import { SystemHealth } from './pages/SystemHealth';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/overview" element={<Overview />} />
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="cameras" element={<Placeholder title="Cameras" />} />
          <Route path="cameras/:id" element={<CameraDetail />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="events" element={<EventExplorer />} />
          <Route path="fences" element={<Placeholder title="Fences" />} />
          <Route path="watchlists" element={<Watchlists />} />
          <Route path="analytics" element={<Placeholder title="Analytics" />} />
          <Route path="system" element={<SystemHealth />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
