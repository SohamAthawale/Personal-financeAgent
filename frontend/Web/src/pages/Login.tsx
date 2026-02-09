import { useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';

interface LoginProps {
  onSignupClick: () => void;
}

export function Login({ onSignupClick }: LoginProps) {
  const { setAuth } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Email and password are required');
      return;
    }

    try {
      setLoading(true);

      const res = await api.login(email, password);

      // Store JWT + user in auth context
      setAuth({
        token: res.access_token,
        user: res.user,
      });

    } catch {
      setError('Incorrect email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-grid">
        <div className="auth-highlight space-y-6">
          <img
            src="/brand-lockup.svg"
            alt="Personal Finance Agent"
            className="h-16"
          />
          <div className="space-y-3">
            <p className="eyebrow">Personal Finance Agent</p>
            <h1 className="text-4xl font-semibold text-ink">
              Confidence for every transaction
            </h1>
            <p className="text-muted">
              Upload bank statements, track trends, and get clear insights
              with a calm, focused workspace.
            </p>
          </div>
          <div className="grid gap-4">
            <div className="hero-card">
              <p className="text-sm font-semibold text-ink">
                Fast parsing
              </p>
              <p className="text-sm text-muted">
                Automatic categorization with review support.
              </p>
            </div>
            <div className="hero-card">
              <p className="text-sm font-semibold text-ink">
                Actionable analytics
              </p>
              <p className="text-sm text-muted">
                See spending patterns across months in seconds.
              </p>
            </div>
          </div>
        </div>

        <div className="auth-panel">
          <div className="mb-6 space-y-2">
            <p className="eyebrow">Welcome back</p>
            <h2 className="text-3xl font-semibold text-ink">
              Log in to your workspace
            </h2>
            <p className="text-sm text-muted">
              Use your email and password to continue.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="flex items-center gap-3 rounded-2xl border border-danger/30 bg-danger/10 p-4">
                <AlertCircle className="w-5 h-5 text-danger flex-shrink-0" />
                <p className="text-danger text-sm">{error}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-ink mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                className="input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-ink mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                className="input"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? 'Logging in...' : 'Log In'}
            </button>
          </form>

          <div className="mt-6 space-y-3">
            <p className="text-sm text-muted">
              Need an account?
            </p>
            <button onClick={onSignupClick} className="btn-secondary w-full">
              Create an Account
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
