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
    '#0f766e',
    '#f97316',
    '#1d4ed8',
    '#c2410c',
    '#0ea5e9',
    '#16a34a',
    '#db2777',
    '#9333ea',
    '#ca8a04',
    '#334155',
  ];

  /* =======================
     Guards
  ======================= */

  if (!auth) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted">Please log in to view analytics.</p>
      </div>
    );
  }

  /* =======================
     Render
  ======================= */

  return (
    <div className="app-container space-y-8">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="eyebrow">Analytics</p>
          <h1 className="text-4xl font-semibold text-ink">
            Trends and cash flow
          </h1>
          <p className="text-muted">
            Track income, expenses, and category shifts over time.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <LlmStatusBadge status={llmStatus} />

          <button
            type="button"
            onClick={handleRerun}
            disabled={reprocessing || loading}
            className="btn-secondary"
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

      <div className="card p-6">
        <h3 className="section-title mb-4">Filter data</h3>

        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm mb-2 text-ink">
              Filter type
            </label>
            <div className="flex gap-4 text-sm text-muted">
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
              className="input"
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
              className="input"
            />
          )}
        </div>
      </div>

        {/* Errors */}
      {error && (
        <div className="card p-4 flex items-center gap-3 border-danger/20 bg-danger/10 text-danger">
          <AlertCircle className="text-danger" />
          {error}
        </div>
      )}

        {/* Loading */}
      {loading && (
        <div className="flex justify-center py-12">
          <Loader className="animate-spin text-primary" />
        </div>
      )}

        {/* Summary Cards */}
      {!loading && data?.metrics && (
        <div className="grid md:grid-cols-3 gap-6">
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
            <Line dataKey="income" stroke="#0f766e" />
            <Line dataKey="expense" stroke="#c2410c" />
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
                          categoryColors[index % categoryColors.length],
                      }}
                    />
                    <span className="font-medium text-ink">
                      {item.category}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-ink">
                      ₹{item.expense.toLocaleString()}
                    </div>
                    <div className="text-xs text-muted">
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
            <Bar dataKey="income" fill="#0f766e" />
            <Bar dataKey="expense" fill="#c2410c" />
          </BarChart>
        </ChartCard>
      )}
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
    <div className="card p-6">
      <h3 className="section-title mb-4">{title}</h3>
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
    green: 'text-success',
    red: 'text-danger',
    blue: 'text-primary',
  };

  const isUp = invertTrend ? trend! < 0 : trend! > 0;

  return (
    <div className="card p-6">
      <p className="text-sm text-muted mb-2">{label}</p>

      <div className="flex items-center gap-2">
        <p className={`text-3xl font-semibold ${colors[color]}`}>
          ₹{value.toLocaleString()}
        </p>

        {trend !== undefined && trend !== 0 && (
          isUp ? (
            <ArrowUp className="text-success" size={20} />
          ) : (
            <ArrowDown className="text-danger" size={20} />
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
      ? 'badge badge-success'
      : status.status === 'disabled'
        ? 'badge'
        : status.status === 'unavailable'
          ? 'badge badge-warning'
          : 'badge badge-danger'
    : 'badge';

  return (
    <div className="flex flex-col gap-1">
      <div
        className={`${classes} uppercase tracking-wide`}
      >
        {label}
      </div>
      {status?.message ? (
        <span className="text-xs text-muted">
          {status.message}
        </span>
      ) : !status ? (
        <span className="text-xs text-muted">
          Run reprocess to check the LLM.
        </span>
      ) : null}
    </div>
  );
}
