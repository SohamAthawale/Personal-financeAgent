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
  status: 'success';
  access_token: string;
  user: User;
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

export type Goal = {
  id?: number; // ✅ optional (important!)
  name: string;
  target_amount: number;
  deadline: string;
  priority: 'low' | 'medium' | 'high';
};


export interface RecommendationsResponse {
  status: string;
  recommendations?: string;
  message?: string;
}

export interface ParseTraceCandidate {
  variant?: string;
  confidence?: number;
  schema_type?: string | null;
}

export interface ParseTrace {
  initial?: {
    confidence?: number;
    schema_type?: string | null;
  };
  retry?: {
    decision?: string;
    candidates?: ParseTraceCandidate[];
  };
  arbitration?: {
    used?: boolean;
    status?: string;
    winner_variant?: string;
    winner_confidence?: number;
  };
  final?: {
    confidence?: number;
    variant?: string;
    schema_type?: string | null;
  };
}

export interface ParseResponse {
  status: string;
  message?: string;
  transactions_count?: number;
  transaction_count?: number;
  statement_id?: number;
  schema_confidence?: number;
  schema_variant?: string;
  trace?: ParseTrace;
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

  snapshot?: {
    month: string;
    created_at: string;
  };

  message?: string;
}

export interface InsightSnapshot {
  month: string;
  created_at: string;
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
  metrics?: Record<string, unknown>;
}

export interface InsightsHistoryResponse {
  status: 'success' | 'error';
  snapshots?: InsightSnapshot[];
  message?: string;
}
// ===== Goal engine & analytics =====

export type StructuredRecommendation = {
  message: string;
  action?: string;
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info';
};

export type ProjectionPoint = {
  month: string;
  amount: number;
};

export type GoalProjection = {
  status: 'projected' | 'impossible';
  achieved_by?: string;
  months_before_deadline?: number;
  overshoots_deadline?: boolean;
  achieves_early?: boolean;
};

export type GoalEvaluation = {
  goal: string;
  feasible: boolean;
  months_remaining: number;
  required_monthly_saving: number;
  current_monthly_saving: number;

  projection?: GoalProjection;

  // 📈 chart input (from backend)
  projection_series?: ProjectionPoint[];
};

export type Metrics = {
  monthly_income: number;
  monthly_expense: number;
  monthly_savings: number;
  savings_rate: number;
};

export interface RecommendationsApiResponse {
  status: 'success' | 'no_data' | 'error';

  // 📊 deterministic analytics
  metrics?: Metrics;

  // 🎯 goal math
  goal_evaluations: GoalEvaluation[];

  // 🧠 rules + LLM
  recommendations?: {
    goals?: StructuredRecommendation[];
  };

  message?: string;
}
