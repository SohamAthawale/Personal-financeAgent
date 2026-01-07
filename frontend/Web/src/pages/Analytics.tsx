import { useState, useEffect } from 'react';
import { Loader, AlertCircle } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { AnalyticsData } from '../types';

/* =======================
   Types LOCAL to page
   ======================= */

type FilterType = 'month' | 'period';

type AnalyticsApiResponse = {
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
};

/* =======================
   Component
   ======================= */

export function Analytics() {
  const { phone } = useAuth();

  const [filterType, setFilterType] = useState<FilterType>('period');
  const [selectedMonth, setSelectedMonth] = useState(
    new Date().toISOString().slice(0, 7)
  );
  const [selectedPeriod, setSelectedPeriod] = useState('3m');

  const [data, setData] = useState<AnalyticsApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType, selectedMonth, selectedPeriod]);

  const loadAnalytics = async () => {
    if (!phone) {
      setError('User phone not found');
      return;
    }

    try {
      setLoading(true);
      setError('');

      const params =
        filterType === 'month'
          ? { month: selectedMonth }
          : { period: selectedPeriod };

      const result = (await api.getAnalytics(
        phone,
        params
      )) as AnalyticsApiResponse;

      if (result.status !== 'success') {
        setError(result.message ?? 'Failed to load analytics');
        setData(null);
        return;
      }

      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  /* =======================
     Adapter: API → UI
     ======================= */

  const analytics: AnalyticsData['data'] | null =
    data?.status === 'success' && data.metrics && data.categories
      ? {
          period:
            filterType === 'month' ? selectedMonth : selectedPeriod,
          total_income: data.metrics.total_income,
          total_expenses: data.metrics.total_expense,
          balance: data.metrics.net_cashflow,
          categories: Object.fromEntries(
            data.categories.map((c) => [c.category, c.expense])
          ),
          transactions: [],
        }
      : null;

  /* =======================
     Render
     ======================= */

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Analytics</h1>
          <p className="text-gray-600">
            View your spending patterns and financial overview
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Filter Data
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter Type
              </label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={filterType === 'period'}
                    onChange={() => setFilterType('period')}
                  />
                  Period
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    checked={filterType === 'month'}
                    onChange={() => setFilterType('month')}
                  />
                  Month
                </label>
              </div>
            </div>

            {filterType === 'period' ? (
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
                className="px-4 py-2 border rounded-lg"
              >
                <option value="3m">Last 3 Months</option>
                <option value="6m">Last 6 Months</option>
                <option value="12m">Last 12 Months</option>
              </select>
            ) : (
              <input
                type="month"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="px-4 py-2 border rounded-lg"
              />
            )}
          </div>
        </div>

        {/* Errors */}
        {error && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-12">
            <Loader className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        )}

        {/* Analytics */}
        {!loading && analytics && (
          <>
            <div className="grid md:grid-cols-3 gap-6 mb-6">
              <Stat label="Total Income" value={analytics.total_income} color="green" />
              <Stat label="Total Expenses" value={analytics.total_expenses} color="red" />
              <Stat label="Net Balance" value={analytics.balance} color="blue" />
            </div>

            {Object.keys(analytics.categories).length > 0 && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="font-semibold mb-4">Spending by Category</h3>
                {Object.entries(analytics.categories).map(([k, v]) => (
                  <div key={k} className="flex justify-between mb-2">
                    <span>{k}</span>
                    <span>₹{v.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {!loading && !analytics && !error && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
            No analytics data available.
          </div>
        )}
      </div>
    </div>
  );
}

/* =======================
   Small helper component
   ======================= */

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: 'green' | 'red' | 'blue';
}) {
  const colors: Record<typeof color, string> = {
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <p className="text-sm text-gray-600 mb-1">{label}</p>
      <p className={`text-3xl font-bold ${colors[color]}`}>
        ₹{value.toLocaleString()}
      </p>
    </div>
  );
}
