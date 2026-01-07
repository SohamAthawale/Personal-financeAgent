export interface User {
  id: number;
  phone: string;
  email: string;
  has_password: boolean;
}

export interface AuthResponse {
  status: string;
  user: User;
  message?: string;
}

export interface LoginResponse {
  status: string;
  message?: string;
}

export interface AnalyticsData {
  status: string;
  data?: {
    period: string;
    total_income: number;
    total_expenses: number;
    balance: number;
    categories: Record<string, number>;
    transactions: Array<{
      date: string;
      description: string;
      amount: number;
      type: string;
      category: string;
    }>;
  };
  message?: string;
}

export interface InsightsData {
  status: string;
  insights?: {
    spending_trends: string;
    income_stability: string;
    savings_potential: string;
    financial_health: string;
  };
  message?: string;
}

export interface Goal {
  name: string;
  target_amount: number;
  deadline: string;
  priority: 'low' | 'medium' | 'high';
}

export interface RecommendationsResponse {
  status: string;
  recommendations?: string;
  message?: string;
}

export interface ParseResponse {
  status: string;
  message?: string;
  transactions_count?: number;
}
// ===== Raw backend analytics response =====

export interface AnalyticsCategory {
  category: string;
  expense: number;
}

export interface AnalyticsMetrics {
  total_income: number;
  total_expense: number;
  net_cashflow: number;
}

export interface AnalyticsApiResponse {
  status: 'success' | 'error';
  message?: string;

  metrics?: {
    total_income: number;
    total_expense: number;
    net_cashflow: number;
  };

  categories?: Array<{
    category: string;
    expense: number;
  }>;
}
export interface InsightsApiResponse {
  status: 'success' | 'error';

  financial_summary?: {
    content: string;
    model: string;
    type: string;
  };

  category_insights?: {
    content: string;
    model: string;
    type: string;
  };

  transaction_patterns?: {
    content: string;
    model: string;
    type: string;
  };

  message?: string;
}
export interface RecommendationsApiResponse {
  actions: string[];
  forecast_balance: number;
  responses: string[];
  goal_evaluations: Array<{
    goal: string;
    feasible: boolean;
    months_remaining: number;
    required_monthly_saving: number;
    current_monthly_saving: number;
  }>;
  state: {
    avg_monthly_income: number;
    avg_monthly_expense: number;
    current_balance: number;
    liquidity_days: number;
    savings_rate: number;
  };
}

