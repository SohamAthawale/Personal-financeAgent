import { useEffect, useMemo, useState } from 'react';
import {
  Loader,
  AlertCircle,
  Plus,
  X,
  Sparkles,
  CheckCircle,
  AlertTriangle,
  Target,
  TrendingUp,
} from 'lucide-react';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { Goal } from '../types';

/* =======================
   Types
   ======================= */

type StructuredRecommendation = {
  message: string;
  action?: string;
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info';
};

type ProjectionPoint = {
  month: string;
  amount: number;
};

type GoalEvaluation = {
  goal: string;
  feasible: boolean;
  months_remaining: number;
  required_monthly_saving: number;
  current_monthly_saving: number;
  projection_series?: ProjectionPoint[];
};

type Metrics = {
  monthly_income: number;
  monthly_expense: number;
  monthly_savings: number;
  savings_rate: number;
};

type RecommendationsApiResponse = {
  status: string;
  metrics?: Metrics;
  goal_evaluations: GoalEvaluation[];
  recommendations?: {
    goals?: StructuredRecommendation[];
  };
};

/* =======================
   Component
   ======================= */

export function Goals() {
  const { auth } = useAuth();

  const [goals, setGoals] = useState<Goal[]>([]);
  const [recommendations, setRecommendations] =
    useState<RecommendationsApiResponse | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [newGoal, setNewGoal] = useState<Goal>({
    name: '',
    target_amount: 0,
    deadline: '',
    priority: 'medium',
  });

  /* =======================
     Load goals
     ======================= */

  useEffect(() => {
    if (!auth) return;

    api
      .getGoals(auth.token)
      .then((res) => setGoals(res.goals))
      .catch(() => setError('Failed to load goals'));
  }, [auth]);

  /* =======================
     Safe goal evaluations
     ======================= */

  const safeGoalEvaluations = useMemo(() => {
    return (
      recommendations?.goal_evaluations.map((g) => ({
        ...g,
        projection_series: Array.isArray(g.projection_series)
          ? g.projection_series
          : [],
      })) ?? []
    );
  }, [recommendations]);

  /* =======================
     Create goal
     ======================= */

  const handleAddGoal = async () => {
    if (!auth) return;

    if (
      !newGoal.name.trim() ||
      !newGoal.deadline ||
      newGoal.target_amount <= 0
    ) {
      setError('All goal fields are required');
      return;
    }

    if (new Date(newGoal.deadline) <= new Date()) {
      setError('Deadline must be in the future');
      return;
    }

    try {
      await api.createGoals(auth.token, [newGoal]);
      const refreshed = await api.getGoals(auth.token);
      setGoals(refreshed.goals);
      setNewGoal({
        name: '',
        target_amount: 0,
        deadline: '',
        priority: 'medium',
      });
      setError('');
    } catch {
      setError('Failed to save goal');
    }
  };

  /* =======================
     Delete goal
     ======================= */

  const handleDeleteGoal = async (goalId: number) => {
    if (!auth) return;

    try {
      await api.deleteGoal(auth.token, goalId);
      setGoals((prev) => prev.filter((g) => g.id !== goalId));
    } catch {
      setError('Failed to delete goal');
    }
  };

  /* =======================
     Get analytics + AI
     ======================= */

  const handleGetRecommendations = async () => {
    if (!auth) return;

    try {
      setLoading(true);
      const res = await api.getRecommendations(auth.token);
      setRecommendations(res);
      setMetrics(res.metrics ?? null);
      setError('');
    } catch {
      setError('Failed to get analytics & recommendations');
    } finally {
      setLoading(false);
    }
  };

  /* =======================
     Render
     ======================= */

  if (!auth) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted">Please log in to view goals.</p>
      </div>
    );
  }

  return (
    <div className="app-container space-y-8">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="eyebrow">Goals</p>
          <h1 className="text-4xl font-semibold text-ink">
            Financial goals studio
          </h1>
          <p className="text-muted">
            Model targets, track feasibility, and plan savings with AI support.
          </p>
        </div>
        <div className="flex items-center gap-2 text-muted">
          <Target className="text-primary" size={28} />
          <span className="text-sm uppercase tracking-[0.25em]">
            Plan ahead
          </span>
        </div>
      </div>

      {error && (
        <div className="card p-4 flex items-center gap-2 border-danger/20 bg-danger/10 text-danger">
          <AlertCircle /> {error}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-1 space-y-6">
          <div className="card p-6 space-y-4">
            <h3 className="section-title flex items-center gap-2">
              <Plus /> Create Goal
            </h3>

            <input
              className="input"
              placeholder="Goal name"
              value={newGoal.name}
              onChange={(e) =>
                setNewGoal({ ...newGoal, name: e.target.value })
              }
            />

            <input
              className="input"
              type="number"
              placeholder="Target amount"
              value={newGoal.target_amount}
              onChange={(e) =>
                setNewGoal({
                  ...newGoal,
                  target_amount: Number(e.target.value),
                })
              }
            />

            <input
              className="input"
              type="date"
              value={newGoal.deadline}
              onChange={(e) =>
                setNewGoal({ ...newGoal, deadline: e.target.value })
              }
            />

            <button
              onClick={handleAddGoal}
              className="btn-primary w-full flex justify-center gap-2"
            >
              <Plus /> Add Goal
            </button>
          </div>

          <div className="card p-6 space-y-4">
            <h3 className="section-title">
              Your Goals ({goals.length})
            </h3>

            {goals.length === 0 && (
              <p className="text-sm text-muted">
                No goals added yet.
              </p>
            )}

            {goals.map((g) => (
              <div
                key={g.id}
                className="flex items-center justify-between rounded-2xl border border-line bg-white/80 px-4 py-3"
              >
                <div>
                  <p className="font-semibold text-ink">{g.name}</p>
                  <p className="text-sm text-muted">
                    ₹{g.target_amount} ·{' '}
                    {new Date(g.deadline).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => handleDeleteGoal(g.id!)}
                  className="btn-danger"
                >
                  <X className="text-danger" />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="xl:col-span-2 space-y-6">
          <button
            onClick={handleGetRecommendations}
            className="btn-primary w-full flex justify-center gap-2"
            disabled={loading}
          >
            {loading ? <Loader className="animate-spin" /> : <Sparkles />}
            {loading ? 'Analyzing finances...' : 'Run Analytics'}
          </button>

          {metrics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="Income" value={metrics.monthly_income} />
              <MetricCard label="Expenses" value={metrics.monthly_expense} />
              <MetricCard label="Savings" value={metrics.monthly_savings} />
              <MetricCard
                label="Savings Rate"
                value={`${(metrics.savings_rate * 100).toFixed(1)}%`}
              />
            </div>
          )}

          {recommendations?.recommendations?.goals && (
            <div className="card p-6">
              <h3 className="section-title flex items-center gap-2 mb-3">
                <TrendingUp /> AI Insights
              </h3>
              <ul className="list-disc pl-5 text-sm space-y-1 text-muted">
                {recommendations.recommendations.goals.map((r, i) => (
                  <li key={i}>{r.message}</li>
                ))}
              </ul>
            </div>
          )}

          {safeGoalEvaluations.map((g, i) => (
            <div
              key={i}
              className={`card p-6 border ${
                g.feasible ? 'border-success/30' : 'border-warning/40'
              }`}
            >
              <div className="flex items-center gap-2 font-semibold mb-2 text-ink">
                {g.feasible ? (
                  <CheckCircle className="text-success" />
                ) : (
                  <AlertTriangle className="text-warning" />
                )}
                {g.goal}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-4">
                <Info label="Months Left" value={g.months_remaining} />
                <Info
                  label="Required / mo"
                  value={`₹${g.required_monthly_saving}`}
                />
                <Info
                  label="Current / mo"
                  value={`₹${g.current_monthly_saving}`}
                />
              </div>

              {g.projection_series.length > 0 && (
                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={g.projection_series}>
                      <XAxis dataKey="month" hide />
                      <YAxis />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="amount"
                        stroke="#0f766e"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* =======================
   Small UI helpers
   ======================= */

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="card p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="text-xl font-semibold text-ink">
        {typeof value === 'number' ? `₹${value}` : value}
      </p>
    </div>
  );
}

function Info({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className="font-semibold text-ink">{value}</p>
    </div>
  );
}
