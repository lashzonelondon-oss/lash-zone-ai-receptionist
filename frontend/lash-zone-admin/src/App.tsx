import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Calls } from './pages/Calls';
import { FAQs } from './pages/FAQs';
import { Settings } from './pages/Settings';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="calls" element={<Calls />} />
          <Route path="appointments" element={<Appointments />} />
          <Route path="escalations" element={<Escalations />} />
          <Route path="faqs" element={<FAQs />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

// Placeholder components for routes not yet implemented
function Appointments() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Appointments</h1>
        <p className="text-gray-500 mt-1">View and manage appointments</p>
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
        <p className="text-gray-500">Calendar integration coming soon</p>
      </div>
    </div>
  );
}

function Escalations() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Escalations</h1>
        <p className="text-gray-500 mt-1">View and manage escalation requests</p>
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
        <p className="text-gray-500">Escalations view available in Settings</p>
      </div>
    </div>
  );
}

export default App;
