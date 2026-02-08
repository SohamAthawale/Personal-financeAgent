import { useState, useEffect } from 'react';
import {
  Loader,
  AlertCircle,
  ArrowUp,
  ArrowDown,
  RefreshCw,
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';

/* =======================
   Types
======================= */

type FilterType = 'month' | 'period';

type LlmStatus = {
  status: 'ok' | 'disabled' | 'unavailable' | 'error';
  message?: string;
  provider?: string;
  model?: string;
  checked_at?: string;
};

type AnalyticsApiResponse = {
  status: 'success' | 'error' | 'no_data';
  message?: string;
  metrics?: {
    total_income: number;
    total_expense: number;
    net_cashflow: number;
  };
  categories?: {
    category: string;
    expense?: number;
    total_expense?: number;
  }[];
  trends?: {
    monthly?: {
      month: string;
      income: number;
      expense: number;
      savings: number;
    }[];
    yearly?: {
      year: string;
      income: number;
      expense: number;
      savings: number;
    }[];
  };
  llm_status?: LlmStatus;
};

/* =======================
   Component
======================= */

export function Analytics() {
  const { auth } = useAuth();

  const [filterType, setFilterType] = useState<FilterType>('period');
  const [selectedMonth, setSelectedMonth] = useState(
    new Date().toISOString().slice(0, 7)
  );
  const [selectedPeriod, setSelectedPeriod] = useState('3m');

  const [data, setData] = useState<AnalyticsApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [error, setError] = useState('');
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null);

  /* =======================
     Load analytics
  ======================= */

  useEffect(() => {
    if (!auth?.token) return;
    loadAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth, filterType, selectedMonth, selectedPeriod]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError('');

      const params =
        filterType === 'month'
          ? { month: selectedMonth }
          : { period: selectedPeriod };

      const result = (await api.getAnalytics(
        auth!.token,
        params
      )) as AnalyticsApiResponse;

      if (result.status !== 'success') {
        setError(result.message ?? 'No analytics data');
        setData(null);
        return;
      }

      setData(result);
      if (result.llm_status) {
        setLlmStatus(result.llm_status);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRerun = async () => {
    if (!auth?.token) return;

    try {
      setReprocessing(true);
      setError('');

      const params =
        filterType === 'month'
          ? { month: selectedMonth }
          : { period: selectedPeriod };

      const result = (await api.rerunAnalytics(
        auth.token,
        params
      )) as AnalyticsApiResponse;

      if (result.status !== 'success') {
        setError(result.message ?? 'No analytics data');
        setData(null);
        if (result.llm_status) {
          setLlmStatus(result.llm_status);
        }
        return;
      }

      setData(result);
      if (result.llm_status) {
        setLlmStatus(result.llm_status);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to reprocess analytics'
      );
    } finally {
      setReprocessing(false);
    }
  };

  /* =======================
     Trend helpers (UI only)
  ======================= */

  const monthly = data?.trends?.monthly ?? [];
  const yearly = data?.trends?.yearly ?? [];
  const categories = data?.categories ?? [];

  const lastMonth =
    monthly.length > 0 ? monthly[monthly.length - 1] : undefined;

  const prevMonth =
    monthly.length > 1 ? monthly[monthly.length - 2] : undefined;

  const incomeTrend =
    lastMonth && prevMonth
      ? lastMonth.income - prevMonth.income
      : 0;

  const expenseTrend =
    lastMonth && prevMonth
      ? lastMonth.expense - prevMonth.expense
      : 0;

  const totalCategoryExpense = categories.reduce(
    (sum, item) => sum + (item.expense ?? item.total_expense ?? 0),
    0
  );

  const categoryBreakdown = categories
    .map((item) => {
      const expense = item.expense ?? item.total_expense ?? 0;
      return {
        ...item,
        expense,
        percent: totalCategoryExpense
          ? (expense / totalCategoryExpense) * 100
          : 0,
      };
    })
    .sort((a, b) => b.expense - a.expense);

  const categoryColors = [
    '#16a34a',
    '#2563eb',
    '#f97316',
    '#dc2626',
    '#8b5cf6',
    '#06b6d4',
    '#facc15',
    '#14b8a6',
    '#e11d48',
    '#64748b',
  ];

  /* =======================
     Guards
  ======================= */

  if (!auth) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-slate-500">Please log in to view analytics.</p>
      </div>
    );
  }

  /* =======================
     Render
  ======================= */

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-6">
          <h1 className="text-4xl font-bold">Analytics</h1>

          <div className="flex flex-wrap items-center gap-3">
            <LlmStatusBadge status={llmStatus} />

            <button
              type="button"
              onClick={handleRerun}
              disabled={reprocessing || loading}
              className="inline-flex items-center gap-2 rounded border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {reprocessing ? (
                <Loader className="animate-spin" size={16} />
              ) : (
                <RefreshCw size={16} />
              )}
              {reprocessing ? 'Reprocessing...' : 'Reprocess All Data'}
            </button>
          </div>
        </div>

        {/* =======================
            FILTERS (RESTORED)
        ======================= */}
        <div className="bg-white p-6 rounded shadow mb-8">
          <h3 className="font-semibold mb-4">Filter Data</h3>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-2">Filter Type</label>
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
                className="border px-3 py-2 rounded"
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
                className="border px-3 py-2 rounded"
              />
            )}
          </div>
        </div>

        {/* Errors */}
        {error && (
          <div className="bg-red-50 border border-red-200 p-4 rounded mb-6 flex gap-2">
            <AlertCircle className="text-red-600" />
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-12">
            <Loader className="animate-spin text-blue-600" />
          </div>
        )}

        {/* Summary Cards */}
        {!loading && data?.metrics && (
          <div className="grid md:grid-cols-3 gap-6 mb-10">
            <Stat
              label="Total Income"
              value={data.metrics.total_income}
              color="green"
              trend={incomeTrend}
            />
            <Stat
              label="Total Expenses"
              value={data.metrics.total_expense}
              color="red"
              trend={expenseTrend}
              invertTrend
            />
            <Stat
              label="Net Balance"
              value={data.metrics.net_cashflow}
              color="blue"
            />
          </div>
        )}

        {/* Month-to-Month Graph */}
        {monthly.length > 0 && (
          <ChartCard title="Month-to-Month Comparison">
            <LineChart data={monthly}>
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Line dataKey="income" stroke="#16a34a" />
              <Line dataKey="expense" stroke="#dc2626" />
            </LineChart>
          </ChartCard>
        )}

        {/* Category Distribution */}
        {categoryBreakdown.length > 0 && (
          <ChartCard title="Category Distribution" noContainer>
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr),260px]">
              <div className="h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryBreakdown}
                      dataKey="expense"
                      nameKey="category"
                      innerRadius={70}
                      outerRadius={110}
                      paddingAngle={2}
                    >
                      {categoryBreakdown.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            categoryColors[index % categoryColors.length]
                          }
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value, _name, props) => {
                        const raw = Array.isArray(value)
                          ? value[0]
                          : value;
                        const payload = props.payload as {
                          percent: number;
                        };
                        return [
                          `₹${Number(raw).toLocaleString()} (${payload.percent.toFixed(1)}%)`,
                          'Spend',
                        ];
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-3">
                {categoryBreakdown.map((item, index) => (
                  <div
                    key={item.category}
                    className="flex items-center justify-between gap-3 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{
                          backgroundColor:
                            categoryColors[
                              index % categoryColors.length
                            ],
                        }}
                      />
                      <span className="font-medium text-slate-700">
                        {item.category}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-slate-700">
                        ₹{item.expense.toLocaleString()}
                      </div>
                      <div className="text-xs text-slate-500">
                        {item.percent.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>
        )}

        {/* Yearly Graph */}
        {yearly.length > 0 && (
          <ChartCard title="Yearly Comparison">
            <BarChart data={yearly}>
              <XAxis dataKey="year" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="income" fill="#22c55e" />
              <Bar dataKey="expense" fill="#ef4444" />
            </BarChart>
          </ChartCard>
        )}
      </div>
    </div>
  );
}

/* =======================
   UI Helpers
======================= */

function ChartCard({
  title,
  children,
  noContainer = false,
}: {
  title: string;
  children: React.ReactNode;
  noContainer?: boolean;
}) {
  return (
    <div className="bg-white p-6 rounded shadow mb-10">
      <h3 className="font-semibold mb-4">{title}</h3>
      {noContainer ? (
        children
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          {children}
        </ResponsiveContainer>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  color,
  trend,
  invertTrend = false,
}: {
  label: string;
  value: number;
  color: 'green' | 'red' | 'blue';
  trend?: number;
  invertTrend?: boolean;
}) {
  const colors = {
    green: 'text-green-600',
    red: 'text-red-600',
    blue: 'text-blue-600',
  };

  const isUp = invertTrend ? trend! < 0 : trend! > 0;

  return (
    <div className="bg-white p-6 rounded shadow">
      <p className="text-sm text-gray-600 mb-1">{label}</p>

      <div className="flex items-center gap-2">
        <p className={`text-3xl font-bold ${colors[color]}`}>
          ₹{value.toLocaleString()}
        </p>

        {trend !== undefined && trend !== 0 && (
          isUp ? (
            <ArrowUp className="text-green-500" size={20} />
          ) : (
            <ArrowDown className="text-red-500" size={20} />
          )
        )}
      </div>
    </div>
  );
}

function LlmStatusBadge({
  status,
}: {
  status: LlmStatus | null;
}) {
  const label = status
    ? status.status === 'ok'
      ? 'LLM: Online'
      : status.status === 'disabled'
        ? 'LLM: Disabled'
        : status.status === 'unavailable'
          ? 'LLM: Offline'
          : 'LLM: Error'
    : 'LLM: Not Checked';

  const classes = status
    ? status.status === 'ok'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : status.status === 'disabled'
        ? 'border-slate-200 bg-slate-50 text-slate-600'
        : status.status === 'unavailable'
          ? 'border-amber-200 bg-amber-50 text-amber-700'
          : 'border-red-200 bg-red-50 text-red-700'
    : 'border-slate-200 bg-slate-50 text-slate-600';

  return (
    <div className="flex flex-col gap-1">
      <div
        className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${classes}`}
      >
        {label}
      </div>
      {status?.message ? (
        <span className="text-xs text-slate-500">
          {status.message}
        </span>
      ) : !status ? (
        <span className="text-xs text-slate-500">
          Run reprocess to check the LLM.
        </span>
      ) : null}
    </div>
  );
}
