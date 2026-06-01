import { useState, useEffect } from 'react';
import { Phone, PhoneCall, Calendar, AlertTriangle, TrendingUp, Clock } from 'lucide-react';
import { getCalls, getAppointments, getEscalations, getConfig } from '@/lib/api';

export function Dashboard() {
  const [stats, setStats] = useState({
    totalCalls: 0,
    todayCalls: 0,
    pendingEscalations: 0,
    todayAppointments: 0,
  });
  const [recentCalls, setRecentCalls] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<any>({});

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [calls, appointments, escalations, cfg] = await Promise.all([
        getCalls(10),
        getAppointments(),
        getEscalations('pending'),
        getConfig(),
      ]);

      const today = new Date().toISOString().split('T')[0];

      setStats({
        totalCalls: calls.length,
        todayCalls: calls.filter((c: any) => c.created_at?.startsWith(today)).length,
        pendingEscalations: escalations.length,
        todayAppointments: appointments.filter((a: any) => a.requested_date === today).length,
      });

      setRecentCalls(calls.slice(0, 5));
      setConfig(cfg);
    } catch (error) {
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
    });
  };

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case 'booking_completed':
        return 'bg-green-100 text-green-700';
      case 'booking_link_sent':
        return 'bg-blue-100 text-blue-700';
      case 'info_provided':
        return 'bg-gray-100 text-gray-700';
      case 'escalated':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-pink-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Welcome back! {config.studio_name || 'Lash Zone London'} AI Receptionist Overview
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Calls</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.totalCalls}</p>
            </div>
            <div className="w-12 h-12 bg-pink-100 rounded-xl flex items-center justify-center">
              <Phone className="w-6 h-6 text-pink-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1 text-sm text-gray-500">
            <TrendingUp className="w-4 h-4 text-green-500" />
            <span>{stats.todayCalls} today</span>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Active Today</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.todayCalls}</p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <PhoneCall className="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1 text-sm text-gray-500">
            <Clock className="w-4 h-4" />
            <span>Last 24 hours</span>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Appointments</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.todayAppointments}</p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
              <Calendar className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1 text-sm text-gray-500">
            <span>Scheduled for today</span>
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Escalations</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stats.pendingEscalations}</p>
            </div>
            <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-red-600" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-1 text-sm text-gray-500">
            <span>Pending attention</span>
          </div>
        </div>
      </div>

      {/* Recent Calls */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="p-6 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Recent Calls</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {recentCalls.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No calls yet. Your AI receptionist is ready to answer calls!
            </div>
          ) : (
            recentCalls.map((call) => (
              <div key={call.id} className="p-4 flex items-center justify-between hover:bg-gray-50">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                    <Phone className="w-5 h-5 text-gray-400" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{call.caller_number}</p>
                    <p className="text-sm text-gray-500">
                      {formatDate(call.created_at)} at {formatTime(call.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getOutcomeColor(call.outcome)}`}>
                    {call.outcome?.replace('_', ' ') || 'Unknown'}
                  </span>
                  <span className="text-sm text-gray-500">
                    {formatDuration(call.duration_seconds)}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* AI Status */}
      <div className="bg-gradient-to-r from-pink-500 to-purple-600 rounded-xl p-6 text-white">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
            <Phone className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-lg">{config.ai_name || 'Luna'} is Online</h3>
            <p className="text-white/80 text-sm mt-1">
              AI Receptionist is active and ready to answer calls 24/7
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" />
            <span className="text-sm font-medium">Live</span>
          </div>
        </div>
      </div>
    </div>
  );
}
