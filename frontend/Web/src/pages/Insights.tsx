import { useState, useEffect } from 'react';
import { Loader, AlertCircle, RefreshCw, Lightbulb } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';

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
};

export function Insights() {
  const { phone } = useAuth();

  const [data, setData] = useState<InsightsApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  /* =======================
     Loader
     ======================= */

  const loadInsights = async (refresh?: string) => {
    if (!phone) {
      setError('User phone not found');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError('');

      const result = (await api.getInsights(phone, refresh)) as InsightsApiResponse;

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

  /* =======================
     Initial load (cached)
     ======================= */

  useEffect(() => {
    loadInsights();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phone]);

  /* =======================
     Adapter: API → UI
     ======================= */

  const insights =
    data?.status === 'success'
      ? [
          {
            title: 'Financial Summary',
            content: data.financial_summary?.content,
            icon: '📈',
          },
          {
            title: 'Category Insights',
            content: data.category_insights?.content,
            icon: '🧾',
          },
          {
            title: 'Transaction Patterns',
            content: data.transaction_patterns?.content,
            icon: '🔍',
          },
        ].filter((i) => Boolean(i.content))
      : [];

  /* =======================
     Render
     ======================= */

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Insights</h1>
            <p className="text-gray-600">
              AI-powered analysis of your financial behavior
            </p>
          </div>

          {/* 🔥 FIXED BUTTON */}
          <button
            onClick={() => loadInsights('all')}
            disabled={loading}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-2 px-6 rounded-lg transition"
          >
            <RefreshCw
              className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`}
            />
            Refresh
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4 mb-8">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        )}

        {!loading && insights.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {insights.map((card) => (
              <div
                key={card.title}
                className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition"
              >
                <div className="flex items-start gap-4">
                  <div className="text-3xl">{card.icon}</div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-3">
                      {card.title}
                    </h3>
                    <p className="text-gray-700 whitespace-pre-line leading-relaxed">
                      {card.content}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && insights.length === 0 && !error && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
            <Lightbulb className="w-12 h-12 text-blue-600 mx-auto mb-4" />
            <p className="text-blue-700 font-medium">
              No insights available yet. Upload a bank statement to receive
              personalized financial insights.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
