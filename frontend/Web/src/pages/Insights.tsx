import { useState, useEffect } from 'react';
import {
  Loader,
  AlertCircle,
  RefreshCw,
  Lightbulb,
  Sparkles,
  LineChart,
  Fingerprint,
} from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import type { InsightSnapshot } from '../types';

/* =======================
   Local API response type
   ======================= */

type InsightsApiResponse = {
  status: 'success' | 'error';
  message?: string;

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
};

export function Insights() {
  const { auth } = useAuth();

  const [data, setData] = useState<InsightsApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<InsightSnapshot[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState('');

  /* =======================
     Load insights
     ======================= */

  const loadInsights = async (forceRefresh = false) => {
    if (!auth) {
      setError('You must be logged in to view insights');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError('');

      const result = (await api.getInsights(
        auth.token,
        forceRefresh
      )) as InsightsApiResponse;

      if (result.status !== 'success') {
        setError(result.message ?? 'Failed to load insights');
        setData(null);
        return;
      }

      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load insights');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    if (!auth) {
      setHistoryLoading(false);
      return;
    }

    try {
      setHistoryLoading(true);
      setHistoryError('');
      const result = await api.getInsightsHistory(auth.token, 12);
      if (result.status !== 'success') {
        setHistoryError(result.message ?? 'Failed to load history');
        setHistory([]);
        return;
      }
      setHistory(result.snapshots ?? []);
    } catch (err) {
      setHistoryError(
        err instanceof Error ? err.message : 'Failed to load history'
      );
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  /* =======================
     Initial load (soft)
     ======================= */

  useEffect(() => {
    if (auth) {
      loadInsights(false);
      loadHistory();
    } else {
      setLoading(false);
      setHistoryLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth]);

  /* =======================
     Adapter: API → UI
     ======================= */

  const insights =
    data?.status === 'success'
      ? [
          {
            title: 'Financial Summary',
            content: data.financial_summary?.content,
            icon: LineChart,
          },
          {
            title: 'Category Insights',
            content: data.category_insights?.content,
            icon: Sparkles,
          },
          {
            title: 'Transaction Patterns',
            content: data.transaction_patterns?.content,
            icon: Fingerprint,
          },
        ].filter((i) => Boolean(i.content))
      : [];

  const formatMonth = (value: string) => {
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return value;
    return dt.toLocaleString('en-US', {
      month: 'long',
      year: 'numeric',
    });
  };

  /* =======================
     Render
     ======================= */

  if (!auth && !loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted">
          Please log in to view your insights.
        </p>
      </div>
    );
  }

  return (
    <div className="app-container space-y-10">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="eyebrow">Insights</p>
          <h1 className="text-4xl font-semibold text-ink">
            AI powered clarity
          </h1>
          <p className="text-muted">
            Narrative summaries to guide your next decisions.
          </p>
        </div>

        <button
          onClick={() => loadInsights(true)}
          disabled={loading}
          className="btn-primary"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="card p-4 flex items-center gap-3 border-danger/20 bg-danger/10 text-danger">
          <AlertCircle className="w-5 h-5 text-danger" />
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader className="w-8 h-8 text-primary animate-spin" />
        </div>
      )}

      {!loading && insights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {insights.map((card) => {
            const Icon = card.icon;
            return (
              <div key={card.title} className="card p-6 space-y-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-surface-muted text-primary">
                    <Icon className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-ink">
                      {card.title}
                    </h3>
                    <p className="text-xs uppercase tracking-[0.25em] text-muted">
                      AI generated
                    </p>
                  </div>
                </div>
                <p className="text-sm text-ink/80 whitespace-pre-line leading-relaxed">
                  {card.content}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {!loading && insights.length === 0 && !error && (
        <div className="card-muted p-8 text-center">
          <Lightbulb className="w-12 h-12 text-primary mx-auto mb-4" />
          <p className="text-ink font-medium">
            No insights available yet. Upload a bank statement to receive
            personalized financial insights.
          </p>
        </div>
      )}

      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-ink">
          Insights history
        </h2>

        {historyError && (
          <div className="card p-4 flex items-center gap-3 border-danger/20 bg-danger/10 text-danger">
            <AlertCircle className="w-5 h-5 text-danger" />
            <p>{historyError}</p>
          </div>
        )}

        {historyLoading && (
          <div className="flex items-center justify-center py-6">
            <Loader className="w-6 h-6 text-primary animate-spin" />
          </div>
        )}

        {!historyLoading && history.length === 0 && !historyError && (
          <div className="card p-6 text-muted">
            No historical snapshots yet.
          </div>
        )}

        {!historyLoading && history.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {history.map((snapshot) => (
              <div key={snapshot.month} className="card p-6 space-y-4">
                <div className="text-xs uppercase tracking-[0.3em] text-muted">
                  {formatMonth(snapshot.month)}
                </div>
                <div className="space-y-4 text-sm">
                  {snapshot.financial_summary?.content && (
                    <div>
                      <div className="text-xs uppercase text-muted mb-1">
                        Financial Summary
                      </div>
                      <p className="text-ink/80 whitespace-pre-line">
                        {snapshot.financial_summary.content}
                      </p>
                    </div>
                  )}
                  {snapshot.category_insights?.content && (
                    <div>
                      <div className="text-xs uppercase text-muted mb-1">
                        Category Insights
                      </div>
                      <p className="text-ink/80 whitespace-pre-line">
                        {snapshot.category_insights.content}
                      </p>
                    </div>
                  )}
                  {snapshot.transaction_patterns?.content && (
                    <div>
                      <div className="text-xs uppercase text-muted mb-1">
                        Transaction Patterns
                      </div>
                      <p className="text-ink/80 whitespace-pre-line">
                        {snapshot.transaction_patterns.content}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
