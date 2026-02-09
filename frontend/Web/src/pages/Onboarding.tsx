import { useState } from 'react';
import { AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../lib/api';

export function Onboarding({
  onBackToLogin,
}: {
  onBackToLogin: () => void;
}) {
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState(''); // optional metadata
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !email.includes('@')) {
      setError('Valid email is required');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      setLoading(true);

      await api.register(email, password, phone || undefined);

      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  /* =======================
     Success screen
     ======================= */

  if (success) {
    return (
      <div className="auth-shell">
        <div className="auth-panel mx-auto max-w-lg text-center">
          <CheckCircle className="w-16 h-16 text-success mx-auto mb-4" />
          <h2 className="text-3xl font-semibold text-ink">
            Account created
          </h2>
          <p className="text-muted mt-2">
            You can now log in with your email and password.
          </p>

          <button onClick={onBackToLogin} className="btn-primary mt-6">
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  /* =======================
     Form
     ======================= */

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
            <p className="eyebrow">New workspace</p>
            <h1 className="text-4xl font-semibold text-ink">
              Build your money command center
            </h1>
            <p className="text-muted">
              Create a secure account to store statements and track progress.
            </p>
          </div>
          <div className="hero-card">
            <p className="text-sm font-semibold text-ink">
              Private by design
            </p>
            <p className="text-sm text-muted">
              Your data stays protected, with clear controls for corrections.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="auth-panel space-y-4">
          <div className="space-y-2">
            <p className="eyebrow">Create account</p>
            <h2 className="text-3xl font-semibold text-ink">
              Start tracking today
            </h2>
            <p className="text-sm text-muted">
              Email and password are required.
            </p>
          </div>

          {error && (
            <div className="flex items-center gap-3 rounded-2xl border border-danger/30 bg-danger/10 p-4">
              <AlertCircle className="w-5 h-5 text-danger" />
              <p className="text-danger text-sm">{error}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-ink mb-1">
              Phone number (optional)
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="9999999999"
              className="input"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              className="input"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Minimum 8 characters"
              className="input"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-ink mb-1">
              Confirm password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter password"
              className="input"
              required
            />
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Creating account...' : 'Create Account'}
          </button>

          <button
            type="button"
            onClick={onBackToLogin}
            disabled={loading}
            className="btn-secondary w-full"
          >
            Return to Login
          </button>
        </form>
      </div>
    </div>
  );
}
