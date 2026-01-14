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
  const { phone } = useAuth();

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
    if (!phone) return;

    api
      .getGoals(phone)
      .then((res) => setGoals(res.goals))
      .catch(() => setError('Failed to load goals'));
  }, [phone]);

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
    if (!phone) return;

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
      await api.createGoals(phone, [newGoal]);
      const refreshed = await api.getGoals(phone);
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
    if (!phone) return;

    try {
      await api.deleteGoal(phone, goalId);
      setGoals((prev) => prev.filter((g) => g.id !== goalId));
    } catch {
      setError('Failed to delete goal');
    }
  };

  /* =======================
     Get analytics + AI
     ======================= */

  const handleGetRecommendations = async () => {
    if (!phone) return;

    try {
      setLoading(true);
      const res = await api.getRecommendations(phone);
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

  return (
    <div className="min-h-screen bg-slate-100 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Target className="text-indigo-600" size={32} />
          <h1 className="text-4xl font-bold text-slate-800">
            Financial Goals
          </h1>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 p-4 rounded text-red-700 flex gap-2">
            <AlertCircle /> {error}
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* =======================
              LEFT – Goals
              ======================= */}
          <div className="xl:col-span-1 space-y-6">
            {/* Create Goal */}
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Plus /> Create Goal
              </h3>

              <input
                className="input mb-2"
                placeholder="Goal name"
                value={newGoal.name}
                onChange={(e) =>
                  setNewGoal({ ...newGoal, name: e.target.value })
                }
              />

              <input
                className="input mb-2"
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
                className="btn-primary mt-4 w-full flex justify-center gap-2"
              >
                <Plus /> Add Goal
              </button>
            </div>

            {/* Goal List */}
            <div className="bg-white p-6 rounded-xl shadow-sm">
              <h3 className="font-semibold mb-4">
                Your Goals ({goals.length})
              </h3>

              {goals.length === 0 && (
                <p className="text-sm text-slate-500">
                  No goals added yet
                </p>
              )}

              {goals.map((g) => (
                <div
                  key={g.id}
                  className="border rounded-lg p-4 mb-3 flex justify-between items-center"
                >
                  <div>
                    <p className="font-semibold">{g.name}</p>
                    <p className="text-sm text-slate-600">
                      ₹{g.target_amount} •{' '}
                      {new Date(g.deadline).toLocaleDateString()}
                    </p>
                  </div>
                  <button onClick={() => handleDeleteGoal(g.id!)}>
                    <X className="text-red-500" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* =======================
              RIGHT – Analytics & AI
              ======================= */}
          <div className="xl:col-span-2 space-y-6">
            <button
              onClick={handleGetRecommendations}
              className="btn-primary w-full flex justify-center gap-2"
              disabled={loading}
            >
              {loading ? <Loader className="animate-spin" /> : <Sparkles />}
              {loading ? 'Analyzing finances...' : 'Run Analytics'}
            </button>

            {/* Metrics */}
            {metrics && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard label="Income" value={metrics.monthly_income} />
                <MetricCard
                  label="Expenses"
                  value={metrics.monthly_expense}
                />
                <MetricCard
                  label="Savings"
                  value={metrics.monthly_savings}
                />
                <MetricCard
                  label="Savings Rate"
                  value={`${(metrics.savings_rate * 100).toFixed(1)}%`}
                />
              </div>
            )}

            {/* AI Insights */}
            {recommendations?.recommendations?.goals && (
              <div className="bg-white p-6 rounded-xl shadow-sm">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <TrendingUp /> AI Insights
                </h3>
                <ul className="list-disc pl-5 text-sm space-y-1">
                  {recommendations.recommendations.goals.map((r, i) => (
                    <li key={i}>{r.message}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Goal Evaluations */}
            {safeGoalEvaluations.map((g, i) => (
              <div
                key={i}
                className={`bg-white p-6 rounded-xl shadow-sm border ${
                  g.feasible
                    ? 'border-green-200'
                    : 'border-yellow-200'
                }`}
              >
                <div className="flex items-center gap-2 font-semibold mb-2">
                  {g.feasible ? (
                    <CheckCircle className="text-green-600" />
                  ) : (
                    <AlertTriangle className="text-yellow-600" />
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
                          stroke="#4f46e5"
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
    <div className="bg-white p-4 rounded-xl shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-xl font-semibold text-slate-800">
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
      <p className="text-xs text-slate-500">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  );
}
