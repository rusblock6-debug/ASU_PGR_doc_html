import { Navigate, Route, Routes } from 'react-router-dom';
import ShiftTasksManager from './components/ShiftTasksManager';
import WorkTimeMap from './components/WorkTimeMap';
import RoutesOverview from './components/RoutesOverview';

function App() {
  return (
    <Routes>
      <Route path="/" element={<ShiftTasksManager />} />
      <Route path="/work-time-map" element={<WorkTimeMap />} />
      <Route path="/routes" element={<RoutesOverview />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;

