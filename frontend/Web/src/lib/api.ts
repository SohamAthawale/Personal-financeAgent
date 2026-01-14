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
  /* =========================
     Auth / User
     ========================= */

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

  /* =========================
     Statements
     ========================= */

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
          onProgress?.((e.loaded / e.total) * 100);
        }
      });

      xhr.onload = () => {
        try {
          const res = JSON.parse(xhr.responseText);
          xhr.status >= 200 && xhr.status < 300
            ? resolve(res)
            : reject(new Error(res.message || 'Upload failed'));
        } catch {
          reject(new Error('Invalid response'));
        }
      };

      xhr.onerror = () => reject(new Error('Network error'));

      xhr.open('POST', `${API_BASE}/api/statement/parse`);
      xhr.send(formData);
    });
  },

  /* =========================
     Analytics
     ========================= */

  async getAnalytics(
    phone: string,
    params: { month?: string; period?: string }
  ): Promise<AnalyticsApiResponse> {
    const searchParams = new URLSearchParams({ phone });

    if (params.month) searchParams.append('month', params.month);
    if (params.period) searchParams.append('period', params.period);

    const response = await fetch(
      `${API_BASE}/api/statement/analytics?${searchParams}`,
      { headers: { 'Content-Type': 'application/json' } }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to fetch analytics');
    }

    return response.json();
  },

  /* =========================
     Insights (with hard refresh)
     ========================= */

  async getInsights(
    phone: string,
    forceRefresh = false
  ): Promise<InsightsApiResponse> {
    const params = new URLSearchParams({ phone });
    if (forceRefresh) params.append('force_refresh', 'true');

    const response = await fetch(
      `${API_BASE}/api/statement/insights?${params}`,
      { headers: { 'Content-Type': 'application/json' } }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to fetch insights');
    }

    return response.json();
  },

  /* =========================
     Goals (REMEMBERED)
     ========================= */

  async getGoals(phone: string): Promise<{ goals: Goal[] }> {
    const response = await fetch(
      `${API_BASE}/api/goals?phone=${phone}`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to fetch goals');
    }

    return response.json();
  },

  async createGoals(phone: string, goals: Goal[]): Promise<{ saved: number }> {
    const response = await fetch(`${API_BASE}/api/goals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, goals }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to save goals');
    }

    return response.json();
  },

  async deleteGoal(phone: string, goalId: number): Promise<void> {
    const response = await fetch(
      `${API_BASE}/api/goals/${goalId}?phone=${phone}`,
      { method: 'DELETE' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to delete goal');
    }
  },

  /* =========================
     Agent Recommendations
     ========================= */

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

  /* =========================
     Health
     ========================= */

  async healthCheck(): Promise<{ db: string }> {
    const response = await fetch(`${API_BASE}/health/db`);
    if (!response.ok) throw new Error('Health check failed');
    return response.json();
  },
};
