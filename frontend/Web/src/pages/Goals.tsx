import { useState } from 'react';
import {
  Loader,
  AlertCircle,
  Plus,
  X,
  Sparkles,
} from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { Goal } from '../types';

/* =======================
   Local API response type
   ======================= */

type StructuredRecommendation = {
  message: string;
  action?: string;
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info';
  confidence?: number;
};

type RecommendationsApiResponse = {
  responses: string[];
  actions: string[];
  forecast_balance: number;

  goal_evaluations: Array<{
    goal: string;
    feasible: boolean;
    months_remaining: number;
    required_monthly_saving: number;
    current_monthly_saving: number;
  }>;

  recommendations?: {
    critical?: StructuredRecommendation[];
    forecast?: StructuredRecommendation[];
    goals?: StructuredRecommendation[];
  };

  state: {
    avg_monthly_income: number;
    avg_monthly_expense: number;
    current_balance: number;
    liquidity_days: number;
    savings_rate: number;
  };
};

export function Goals() {
  const { phone } = useAuth();

  const [goals, setGoals] = useState<Goal[]>([]);
  const [recommendations, setRecommendations] =
    useState<RecommendationsApiResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [newGoal, setNewGoal] = useState<Goal>({
    name: '',
    target_amount: 0,
    deadline: '',
    priority: 'medium',
  });

  /* =======================
     Goal handlers
     ======================= */

  const handleAddGoal = () => {
    if (!newGoal.name.trim()) {
      setError('Goal name is required');
      return;
    }
    if (newGoal.target_amount <= 0) {
      setError('Target amount must be greater than 0');
      return;
    }
    if (!newGoal.deadline) {
      setError('Deadline is required');
      return;
    }

    setGoals([...goals, { ...newGoal }]);
    setNewGoal({
      name: '',
      target_amount: 0,
      deadline: '',
      priority: 'medium',
    });
    setError('');
  };

  const handleRemoveGoal = (index: number) => {
    setGoals(goals.filter((_, i) => i !== index));
  };

  /* =======================
     Fetch recommendations
     ======================= */

  const handleGetRecommendations = async () => {
    if (!phone) {
      setError('User phone not found');
      return;
    }

    try {
      setLoading(true);
      setError('');

      const result = (await api.getRecommendations(
        phone,
        goals.length > 0 ? goals : undefined
      )) as RecommendationsApiResponse;

      setRecommendations(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to get recommendations'
      );
      setRecommendations(null);
    } finally {
      setLoading(false);
    }
  };

  /* =======================
     Render helpers
     ======================= */

  const renderBlock = (
    title: string,
    items?: StructuredRecommendation[],
    color = 'gray'
  ) => {
    if (!items || items.length === 0) return null;

    const colorMap: Record<string, string> = {
      red: 'bg-red-50 border-red-200 text-red-700',
      yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
      green: 'bg-green-50 border-green-200 text-green-700',
      blue: 'bg-blue-50 border-blue-200 text-blue-700',
      gray: 'bg-gray-50 border-gray-200 text-gray-700',
    };

    return (
      <div className={`border rounded-lg p-4 mb-4 ${colorMap[color]}`}>
        <p className="font-semibold mb-2">{title}</p>
        <ul className="list-disc pl-5 space-y-1">
          {items.map((r, i) => (
            <li key={i}>{r.message}</li>
          ))}
        </ul>
      </div>
    );
  };

  /* =======================
     Render
     ======================= */

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Goals & Recommendations
          </h1>
          <p className="text-gray-600">
            Set financial goals and get AI-powered recommendations
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-700">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* =======================
              Goals column
              ======================= */}
          <div>
            {/* Create goal */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h3 className="text-lg font-semibold mb-6">Create a Goal</h3>

              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Goal name"
                  value={newGoal.name}
                  onChange={(e) =>
                    setNewGoal({ ...newGoal, name: e.target.value })
                  }
                  className="w-full px-4 py-2 border rounded-lg"
                />

                <input
                  type="number"
                  placeholder="Target amount"
                  value={newGoal.target_amount}
                  onChange={(e) =>
                    setNewGoal({
                      ...newGoal,
                      target_amount: Number(e.target.value),
                    })
                  }
                  className="w-full px-4 py-2 border rounded-lg"
                />

                <input
                  type="date"
                  value={newGoal.deadline}
                  onChange={(e) =>
                    setNewGoal({ ...newGoal, deadline: e.target.value })
                  }
                  className="w-full px-4 py-2 border rounded-lg"
                />

                <select
                  value={newGoal.priority}
                  onChange={(e) =>
                    setNewGoal({
                      ...newGoal,
                      priority: e.target.value as 'low' | 'medium' | 'high',
                    })
                  }
                  className="w-full px-4 py-2 border rounded-lg"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>

                <button
                  onClick={handleAddGoal}
                  className="w-full bg-blue-600 text-white py-2 rounded-lg flex justify-center gap-2"
                >
                  <Plus className="w-4 h-4" /> Add Goal
                </button>
              </div>
            </div>

            {/* Goal list */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold mb-4">
                Your Goals ({goals.length})
              </h3>

              {goals.length === 0 ? (
                <p className="text-gray-600 text-center">
                  No goals added yet
                </p>
              ) : (
                goals.map((goal, idx) => (
                  <div
                    key={idx}
                    className="border rounded-lg p-4 mb-3 flex justify-between"
                  >
                    <div>
                      <p className="font-semibold">{goal.name}</p>
                      <p className="text-sm text-gray-600">
                        ₹{goal.target_amount} by{' '}
                        {new Date(goal.deadline).toLocaleDateString()}
                      </p>
                    </div>
                    <button onClick={() => handleRemoveGoal(idx)}>
                      <X className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* =======================
              Recommendations column
              ======================= */}
          <div>
            <button
              onClick={handleGetRecommendations}
              disabled={loading}
              className="w-full mb-6 bg-blue-600 text-white py-3 rounded-lg flex justify-center gap-2"
            >
              {loading ? (
                <Loader className="w-5 h-5 animate-spin" />
              ) : (
                <Sparkles className="w-5 h-5" />
              )}
              {loading ? 'Generating...' : 'Get AI Recommendations'}
            </button>

            {recommendations && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold mb-4">
                  AI Recommendations
                </h3>

                {/* NEW structured recommendations */}
                {renderBlock(
                  'Critical alerts',
                  recommendations.recommendations?.critical,
                  'red'
                )}

                {renderBlock(
                  'Forecast insights',
                  recommendations.recommendations?.forecast,
                  'yellow'
                )}

                {renderBlock(
                  'Goal insights',
                  recommendations.recommendations?.goals,
                  'green'
                )}

                {/* Goal evaluation math (unchanged) */}
                {recommendations.goal_evaluations.map((g, idx) => (
                  <div key={idx} className="mt-4 text-sm">
                    {!g.feasible && (
                      <p className="text-red-600 font-medium">
                        ⚠ Goal "{g.goal}" is not feasible at current savings
                      </p>
                    )}
                    <p>
                      Required: ₹{g.required_monthly_saving}/month · Current:{' '}
                      ₹{g.current_monthly_saving}/month
                    </p>
                  </div>
                ))}
              </div>
            )}

            {!loading && !recommendations && (
              <div className="bg-blue-50 border rounded-lg p-6 text-center">
                Click above to get AI-powered recommendations.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
