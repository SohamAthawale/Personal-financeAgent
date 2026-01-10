import {
  AuthResponse,
  LoginResponse,
  InsightsApiResponse,
  RecommendationsApiResponse,
  ParseResponse,
  Goal,
  AnalyticsApiResponse
} from '../types/index';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';

export const api = {
  async createUser(
    phone: string,
    email?: string,
    password?: string
  ): Promise<AuthResponse> {
    const response = await fetch(`${API_BASE}/api/user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone,
        ...(email && { email }),
        ...(password && { password }),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to create user');
    }

    return response.json();
  },

  async login(phone: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Login failed');
    }

    return response.json();
  },

  async uploadStatement(
    file: File,
    phone: string,
    onProgress?: (progress: number) => void
  ): Promise<ParseResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('phone', phone);

    const xhr = new XMLHttpRequest();

    return new Promise((resolve, reject) => {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const progress = (e.loaded / e.total) * 100;
          onProgress?.(progress);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            reject(new Error('Invalid response format'));
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.message || 'Upload failed'));
          } catch {
            reject(new Error('Upload failed'));
          }
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Network error during upload'));
      });

      xhr.open('POST', `${API_BASE}/api/statement/parse`);
      xhr.send(formData);
    });
  },

  async getAnalytics(
    phone: string,
    params: { month?: string; period?: string }
  ): Promise<AnalyticsApiResponse> {
    const searchParams = new URLSearchParams({ phone });

    if (params.month) {
      searchParams.append('month', params.month);
    } else if (params.period) {
      searchParams.append('period', params.period);
    }

    const response = await fetch(
      `${API_BASE}/api/statement/analytics?${searchParams}`,
      {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to fetch analytics');
    }

    return response.json();
  },

  async getInsights(
  phone: string,
  refresh?: string
): Promise<InsightsApiResponse> {
  const params = new URLSearchParams({ phone });

  if (refresh) {
    params.append('refresh', refresh);
  }

  const response = await fetch(
    `${API_BASE}/api/statement/insights?${params.toString()}`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Failed to fetch insights');
  }

  return response.json();
},

  async getRecommendations(
    phone: string,
    goals?: Goal[]
  ): Promise<RecommendationsApiResponse> {
    const response = await fetch(`${API_BASE}/api/agent/recommendations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        phone,
        ...(goals && { goals }),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to fetch recommendations');
    }

    return response.json();
  },

  async healthCheck(): Promise<{ db: string }> {
    const response = await fetch(`${API_BASE}/health/db`);

    if (!response.ok) {
      throw new Error('Health check failed');
    }

    return response.json();
  },
};
