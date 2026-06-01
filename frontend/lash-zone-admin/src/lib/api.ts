/**
 * API client for Lash Zone AI Receptionist
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return { success: false, error: data.error || 'Request failed' };
    }

    return { success: true, data };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : 'Network error' };
  }
}

// ==================== CALLS ====================

export interface Call {
  id: string;
  call_sid: string;
  caller_number: string;
  duration_seconds: number;
  outcome: string;
  transcript_json: any[];
  recording_url?: string;
  created_at: string;
}

export const getCalls = async (limit = 50, offset = 0): Promise<Call[]> => {
  const result = await fetchApi<Call[]>(`/calls?limit=${limit}&offset=${offset}`);
  return result.data || [];
};

export const getCall = async (id: string): Promise<Call | null> => {
  const result = await fetchApi<Call>(`/calls/${id}`);
  return result.data || null;
};

export const searchCalls = async (query: string): Promise<Call[]> => {
  const result = await fetchApi<Call[]>(`/calls/search?q=${encodeURIComponent(query)}`);
  return result.data || [];
};

// ==================== APPOINTMENTS ====================

export interface Appointment {
  id: string;
  client_name: string;
  client_phone: string;
  client_email?: string;
  service: string;
  requested_date: string;
  requested_time: string;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled';
  booked_via: string;
  notes?: string;
  created_at: string;
}

export const getAppointments = async (date?: string, status?: string): Promise<Appointment[]> => {
  const params = new URLSearchParams();
  if (date) params.append('date', date);
  if (status) params.append('status', status);

  const result = await fetchApi<Appointment[]>(`/appointments?${params}`);
  return result.data || [];
};

export const createAppointment = async (data: Partial<Appointment>): Promise<Appointment | null> => {
  const result = await fetchApi<Appointment>('/appointments', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return result.data || null;
};

export const checkAvailability = async (date: string, time: string): Promise<boolean> => {
  const result = await fetchApi<{ available: boolean }>(`/availability?date=${date}&time=${time}`);
  return result.data?.available ?? true;
};

// ==================== ESCALATIONS ====================

export interface Escalation {
  id: string;
  call_id?: string;
  client_name: string;
  client_phone: string;
  issue_summary: string;
  details_json: any;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  status: 'pending' | 'in_progress' | 'resolved';
  resolved_at?: string;
  notes?: string;
  created_at: string;
}

export const getEscalations = async (status?: string): Promise<Escalation[]> => {
  const params = status ? `?status=${status}` : '';
  const result = await fetchApi<Escalation[]>(`/escalations${params}`);
  return result.data || [];
};

export const resolveEscalation = async (id: string, notes?: string): Promise<boolean> => {
  const result = await fetchApi(`/escalations/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ notes }),
  });
  return result.success;
};

// ==================== FAQs ====================

export interface FAQ {
  id: string;
  question_pattern: string;
  answer: string;
  category: string;
  active: boolean;
  created_at: string;
}

export const getFAQs = async (): Promise<FAQ[]> => {
  const result = await fetchApi<FAQ[]>('/faqs');
  return result.data || [];
};

export const createFAQ = async (data: Partial<FAQ>): Promise<FAQ | null> => {
  const result = await fetchApi<FAQ>('/faqs', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  return result.data || null;
};

export const updateFAQ = async (id: string, data: Partial<FAQ>): Promise<boolean> => {
  const result = await fetchApi(`/faqs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
  return result.success;
};

export const deleteFAQ = async (id: string): Promise<boolean> => {
  const result = await fetchApi(`/faqs/${id}`, {
    method: 'DELETE',
  });
  return result.success;
};

// ==================== CONFIG ====================

export interface StudioConfig {
  [key: string]: string;
}

export const getConfig = async (): Promise<StudioConfig> => {
  const result = await fetchApi<StudioConfig>('/config');
  return result.data || {};
};

export const updateConfig = async (key: string, value: string): Promise<boolean> => {
  const result = await fetchApi('/config', {
    method: 'PUT',
    body: JSON.stringify({ key, value }),
  });
  return result.success;
};

// ==================== SMS ====================

export const sendSMS = async (to: string, message: string): Promise<boolean> => {
  const result = await fetchApi('/sms/send', {
    method: 'POST',
    body: JSON.stringify({ to_number: to, message }),
  });
  return result.success;
};
