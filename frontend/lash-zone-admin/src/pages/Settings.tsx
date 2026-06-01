import { useState, useEffect } from 'react';
import { Save, Phone, MessageSquare, Bot, Building, Bell } from 'lucide-react';
import { getConfig, updateConfig, getEscalations, resolveEscalation, Escalation } from '@/lib/api';

interface ConfigData {
  studio_name: string;
  studio_phone: string;
  studio_address: string;
  ai_name: string;
  ai_voice: string;
  booking_url: string;
  owner_phone: string;
  opening_hours: string;
  [key: string]: string;
}

const voiceOptions = [
  { value: 'alloy', label: 'Alloy - Neutral & Professional' },
  { value: 'echo', label: 'Echo - Friendly & Warm' },
  { value: 'fable', label: 'Fable - British & Elegant' },
  { value: 'onyx', label: 'Onyx - Deep & Authoritative' },
  { value: 'nova', label: 'Nova - Energetic & Bright' },
  { value: 'shimmer', label: 'Shimmer - Soft & Calm' },
];

export function Settings() {
  const [config, setConfig] = useState<ConfigData>({
    studio_name: '',
    studio_phone: '',
    studio_address: '',
    ai_name: '',
    ai_voice: 'alloy',
    booking_url: '',
    owner_phone: '',
    opening_hours: '',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [escalations, setEscalations] = useState<Escalation[]>([]);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [cfg, escalationsData] = await Promise.all([
        getConfig(),
        getEscalations('pending'),
      ]);
      setConfig({
        studio_name: cfg.studio_name || '',
        studio_phone: cfg.studio_phone || '',
        studio_address: cfg.studio_address || '',
        ai_name: cfg.ai_name || 'Luna',
        ai_voice: cfg.ai_voice || 'alloy',
        booking_url: cfg.booking_url || '',
        owner_phone: cfg.owner_phone || '',
        opening_hours: cfg.opening_hours || '',
      });
      setEscalations(escalationsData);
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (section: string) => {
    setSaving(true);
    setMessage('');

    try {
      for (const [key, value] of Object.entries(config)) {
        await updateConfig(key, value);
      }
      setMessage(`${section} saved successfully!`);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error saving:', error);
      setMessage('Error saving settings');
    } finally {
      setSaving(false);
    }
  };

  const handleResolveEscalation = async (id: string) => {
    try {
      await resolveEscalation(id);
      setEscalations(escalations.filter((e) => e.id !== id));
    } catch (error) {
      console.error('Error resolving:', error);
    }
  };

  const parseOpeningHours = () => {
    try {
      const hours = JSON.parse(config.opening_hours || '{}');
      return Object.entries(hours)
        .map(([day, time]) => `${day.charAt(0).toUpperCase() + day.slice(1)}: ${time}`)
        .join('\n');
    } catch {
      return config.opening_hours;
    }
  };

  const formatOpeningHours = (text: string) => {
    const lines = text.split('\n').filter(Boolean);
    const hours: Record<string, string> = {};
    lines.forEach((line) => {
      const [day, ...timeParts] = line.split(':');
      if (day && timeParts.length) {
        hours[day.trim().toLowerCase()] = timeParts.join(':').trim();
      }
    });
    return JSON.stringify(hours);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Configure your AI receptionist</p>
      </div>

      {message && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
          {message}
        </div>
      )}

      {/* Studio Information */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <Building className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">Studio Information</h2>
            <p className="text-sm text-gray-500">Basic information about your business</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Studio Name</label>
            <input
              type="text"
              value={config.studio_name}
              onChange={(e) => setConfig({ ...config, studio_name: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
            <input
              type="text"
              value={config.studio_phone}
              onChange={(e) => setConfig({ ...config, studio_phone: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
            <input
              type="text"
              value={config.studio_address}
              onChange={(e) => setConfig({ ...config, studio_address: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Opening Hours (one per line, e.g., "Monday: 9:00-18:00")
            </label>
            <textarea
              value={parseOpeningHours()}
              onChange={(e) => setConfig({ ...config, opening_hours: formatOpeningHours(e.target.value) })}
              rows={7}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent resize-none font-mono text-sm"
            />
          </div>

          <button
            onClick={() => handleSave('Studio information')}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2.5 bg-pink-500 text-white rounded-lg hover:bg-pink-600 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* AI Configuration */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-pink-100 rounded-lg flex items-center justify-center">
            <Bot className="w-5 h-5 text-pink-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">AI Configuration</h2>
            <p className="text-sm text-gray-500">Customize your AI receptionist</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">AI Name</label>
            <input
              type="text"
              value={config.ai_name}
              onChange={(e) => setConfig({ ...config, ai_name: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
              placeholder="Luna"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">AI Voice</label>
            <select
              value={config.ai_voice}
              onChange={(e) => setConfig({ ...config, ai_voice: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
            >
              {voiceOptions.map((voice) => (
                <option key={voice.value} value={voice.value}>
                  {voice.label}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => handleSave('AI configuration')}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2.5 bg-pink-500 text-white rounded-lg hover:bg-pink-600 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Booking & Notifications */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">Booking & Notifications</h2>
            <p className="text-sm text-gray-500">Configure booking links and alerts</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Booking URL</label>
            <input
              type="url"
              value={config.booking_url}
              onChange={(e) => setConfig({ ...config, booking_url: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
              placeholder="https://your-booking-site.com"
            />
            <p className="mt-1 text-xs text-gray-500">
              Luna will send this link via SMS when clients want to book
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Owner/Management Phone</label>
            <input
              type="tel"
              value={config.owner_phone}
              onChange={(e) => setConfig({ ...config, owner_phone: e.target.value })}
              className="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
              placeholder="+44..."
            />
            <p className="mt-1 text-xs text-gray-500">
              Escalations and alerts will be sent here
            </p>
          </div>

          <button
            onClick={() => handleSave('Booking & notifications')}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2.5 bg-pink-500 text-white rounded-lg hover:bg-pink-600 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Pending Escalations */}
      {escalations.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-red-200 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <Bell className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">Pending Escalations</h2>
              <p className="text-sm text-gray-500">{escalations.length} requiring attention</p>
            </div>
          </div>

          <div className="space-y-4">
            {escalations.map((escalation) => (
              <div
                key={escalation.id}
                className="p-4 bg-red-50 rounded-lg border border-red-100"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-gray-900">{escalation.client_name}</span>
                      <span className="text-sm text-gray-500">{escalation.client_phone}</span>
                    </div>
                    <p className="text-gray-700">{escalation.issue_summary}</p>
                    <p className="text-xs text-gray-500 mt-2">
                      {new Date(escalation.created_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleResolveEscalation(escalation.id)}
                    className="px-3 py-1.5 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm"
                  >
                    Mark Resolved
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
