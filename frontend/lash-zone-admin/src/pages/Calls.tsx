import { useState, useEffect } from 'react';
import { Phone, Search, Play, ChevronRight, Clock, User, Filter } from 'lucide-react';
import { getCalls, searchCalls, Call } from '@/lib/api';

export function Calls() {
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCall, setSelectedCall] = useState<Call | null>(null);

  useEffect(() => {
    loadCalls();
  }, []);

  const loadCalls = async () => {
    try {
      const data = await getCalls(100);
      setCalls(data);
    } catch (error) {
      console.error('Error loading calls:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadCalls();
      return;
    }
    setLoading(true);
    try {
      const data = await searchCalls(searchQuery);
      setCalls(data);
    } catch (error) {
      console.error('Error searching:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }),
      time: date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }),
    };
  };

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case 'booking_completed':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'booking_link_sent':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'info_provided':
        return 'bg-gray-100 text-gray-700 border-gray-200';
      case 'escalated':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Call History</h1>
          <p className="text-gray-500 mt-1">View and search all calls handled by AI</p>
        </div>
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by phone number..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleSearch}
            className="px-4 py-2.5 bg-pink-500 text-white rounded-lg hover:bg-pink-600 transition-colors"
          >
            Search
          </button>
        </div>
      </div>

      {/* Calls List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
          </div>
        ) : calls.length === 0 ? (
          <div className="p-12 text-center">
            <Phone className="w-12 h-12 text-gray-300 mx-auto" />
            <p className="mt-4 text-gray-500">No calls found</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {calls.map((call) => {
              const { date, time } = formatDateTime(call.created_at);
              return (
                <div
                  key={call.id}
                  className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => setSelectedCall(call)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-pink-100 rounded-full flex items-center justify-center">
                        <Phone className="w-6 h-6 text-pink-600" />
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900">{call.caller_number}</p>
                        <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5" />
                            {formatDuration(call.duration)}
                          </span>
                          <span>{date}</span>
                          <span>{time}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-3 py-1.5 rounded-full text-xs font-medium border ${getOutcomeColor(call.outcome)}`}>
                        {call.outcome?.replace('_', ' ') || 'Unknown'}
                      </span>
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Call Detail Modal */}
      {selectedCall && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-xl">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Call Details</h2>
              <button
                onClick={() => setSelectedCall(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                ✕
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
              <div className="space-y-6">
                {/* Call Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500 mb-1">Caller</p>
                    <p className="font-semibold text-gray-900">{selectedCall.caller_number}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500 mb-1">Duration</p>
                    <p className="font-semibold text-gray-900">{formatDuration(selectedCall.duration)}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500 mb-1">Date</p>
                    <p className="font-semibold text-gray-900">{formatDateTime(selectedCall.created_at).date}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500 mb-1">Time</p>
                    <p className="font-semibold text-gray-900">{formatDateTime(selectedCall.created_at).time}</p>
                  </div>
                </div>

                {/* Outcome */}
                <div>
                  <p className="text-sm text-gray-500 mb-2">Outcome</p>
                  <span className={`inline-block px-3 py-1.5 rounded-full text-sm font-medium ${getOutcomeColor(selectedCall.outcome)}`}>
                    {selectedCall.outcome?.replace('_', ' ') || 'Unknown'}
                  </span>
                </div>

                {/* Transcript */}
                {selectedCall.transcript && selectedCall.transcript.length > 0 && (
                  <div>
                    <p className="text-sm text-gray-500 mb-3">Transcript</p>
                    <div className="space-y-3 bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                      {(() => {
                        try {
                          // Try to parse as JSON array
                          const parsed = JSON.parse(selectedCall.transcript);
                          if (Array.isArray(parsed)) {
                            return parsed.map((msg: any, index: number) => (
                              <div
                                key={index}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                              >
                                <div
                                  className={`max-w-[80%] px-4 py-2 rounded-2xl ${
                                    msg.role === 'user'
                                      ? 'bg-pink-500 text-white rounded-br-md'
                                      : 'bg-white border border-gray-200 text-gray-900 rounded-bl-md'
                                  }`}
                                >
                                  <p className="text-sm font-medium mb-1 opacity-70">
                                    {msg.role === 'user' ? 'Caller' : 'AI Receptionist'}
                                  </p>
                                  <p>{msg.content}</p>
                                </div>
                              </div>
                            ));
                          }
                        } catch {
                          // If not JSON, display as plain text
                          return (
                            <div className="text-gray-700 whitespace-pre-wrap">
                              {selectedCall.transcript}
                            </div>
                          );
                        }
                        return null;
                      })()}
                    </div>
                  </div>
                )}

                {/* Recording */}
                {selectedCall.recording_url && (
                  <div>
                    <p className="text-sm text-gray-500 mb-2">Recording</p>
                    <audio
                      src={selectedCall.recording_url}
                      controls
                      className="w-full"
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
