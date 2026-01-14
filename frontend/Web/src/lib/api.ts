import {
  AuthResponse,
  LoginResponse,
  InsightsApiResponse,
  RecommendationsApiResponse,
  ParseResponse,
  Goal,
  AnalyticsApiResponse
} from '../types';

const API_BASE =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';

/* =========================
   Helpers
   ========================= */

function authHeaders(token?: string) {
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

/* =========================
   API
   ========================= */

export const api = {
  /* =========================
     Auth
     ========================= */

  async register(
    email: string,
    password: string,
    phone?: string
  ): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ email, password, phone }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Registration failed');
    }

    return res.json();
  },

  async login(
    email: string,
    password: string
  ): Promise<LoginResponse> {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Login failed');
    }

    return res.json();
  },

  /* =========================
     Statements
     ========================= */

  async uploadStatement(
    file: File,
    token: string,
    onProgress?: (progress: number) => void
  ): Promise<ParseResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();

    return new Promise((resolve, reject) => {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          onProgress?.((e.loaded / e.total) * 100);
        }
      };

      xhr.onload = () => {
        try {
          const res = JSON.parse(xhr.responseText);
          xhr.status >= 200 && xhr.status < 300
            ? resolve(res)
            : reject(new Error(res.message || 'Upload failed'));
        } catch {
          reject(new Error('Invalid server response'));
        }
      };

      xhr.onerror = () => reject(new Error('Network error'));

      xhr.open('POST', `${API_BASE}/api/statement/parse`);
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      xhr.send(formData);
    });
  },

  /* =========================
     Analytics
     ========================= */

  async getAnalytics(
    token: string,
    params: { month?: string; period?: string }
  ): Promise<AnalyticsApiResponse> {
    const search = new URLSearchParams();

    if (params.month) search.append('month', params.month);
    if (params.period) search.append('period', params.period);

    const res = await fetch(
      `${API_BASE}/api/statement/analytics?${search}`,
      { headers: authHeaders(token) }
    );

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Failed to fetch analytics');
    }

    return res.json();
  },

  /* =========================
     Insights
     ========================= */

  async getInsights(
    token: string,
    forceRefresh = false
  ): Promise<InsightsApiResponse> {
    const params = new URLSearchParams();
    if (forceRefresh) params.append('force_refresh', 'true');

    const res = await fetch(
      `${API_BASE}/api/statement/insights?${params}`,
      { headers: authHeaders(token) }
    );

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Failed to fetch insights');
    }

    return res.json();
  },

  /* =========================
     Goals
     ========================= */

  async getGoals(token: string): Promise<{ goals: Goal[] }> {
    const res = await fetch(
      `${API_BASE}/api/goals`,
      { headers: authHeaders(token) }
    );

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Failed to fetch goals');
    }

    return res.json();
  },

  async createGoals(
    token: string,
    goals: Goal[]
  ): Promise<void> {
    const res = await fetch(`${API_BASE}/api/goals`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify({ goals }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Failed to save goals');
    }
  },

  async deleteGoal(
    token: string,
    goalId: number
  ): Promise<void> {
    const res = await fetch(
      `${API_BASE}/api/goals/${goalId}`,
      {
        method: 'DELETE',
        headers: authHeaders(token),
      }
    );

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Failed to delete goal');
    }
  },

  /* =========================
     Agent Recommendations
     ========================= */

  async getRecommendations(
    token: string,
    goals?: Goal[]
  ): Promise<RecommendationsApiResponse> {
    const res = await fetch(
      `${API_BASE}/api/agent/recommendations`,
      {
        method: 'POST',
        headers: authHeaders(token),
        body: JSON.stringify({ ...(goals && { goals }) }),
      }
    );

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Failed to fetch recommendations');
    }

    return res.json();
  },

  /* =========================
     Health
     ========================= */

  async healthCheck(): Promise<{ db: string }> {
    const res = await fetch(`${API_BASE}/health/db`);
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },
};
