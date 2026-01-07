import React, { useState } from 'react';
import { AlertCircle, CheckCircle } from 'lucide-react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';

export function Onboarding() {
  const { setPhone } = useAuth();
  const [step, setStep] = useState<'phone' | 'optional' | 'success'>('phone');
  const [phone, setPhoneLocal] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handlePhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!phone.trim()) {
      setError('Phone number is required');
      return;
    }

    try {
      setLoading(true);
      await api.createUser(phone);
      setStep('optional');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  const handleOptionalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (email && !email.includes('@')) {
      setError('Invalid email format');
      return;
    }

    if (password && password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      setLoading(true);
      await api.createUser(phone, email || undefined, password || undefined);
      setPhone(phone);
      setStep('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set up account');
    } finally {
      setLoading(false);
    }
  };

  const handleSkipOptional = async () => {
    try {
      setLoading(true);
      setPhone(phone);
      setStep('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete setup');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'success') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-6" />
          <h1 className="text-3xl font-bold text-gray-900 mb-3">All Set!</h1>
          <p className="text-gray-600 mb-8">
            Your account is ready. You can now start uploading bank statements to analyze your finances.
          </p>
          <div className="bg-white rounded-lg shadow p-4 text-left">
            <p className="text-sm text-gray-600">
              <span className="font-semibold">Phone:</span> {phone}
            </p>
            {email && (
              <p className="text-sm text-gray-600 mt-2">
                <span className="font-semibold">Email:</span> {email}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (step === 'optional') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Secure Your Account
            </h1>
            <p className="text-gray-600">
              Add email and password for better security (optional)
            </p>
          </div>

          <form onSubmit={handleOptionalSubmit} className="space-y-4">
            {error && (
              <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Email <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password <span className="text-gray-400">(optional)</span>
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 characters"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {password && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm password"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-2 rounded-lg transition"
            >
              {loading ? 'Setting up...' : 'Continue'}
            </button>

            <button
              type="button"
              onClick={handleSkipOptional}
              disabled={loading}
              className="w-full bg-gray-200 hover:bg-gray-300 disabled:opacity-50 text-gray-700 font-semibold py-2 rounded-lg transition"
            >
              Skip for Now
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Finance Analyzer
          </h1>
          <p className="text-gray-600">
            Understand your spending with AI-powered insights
          </p>
        </div>

        <form onSubmit={handlePhoneSubmit} className="space-y-4">
          {error && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhoneLocal(e.target.value)}
              placeholder="9999999999"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-3 rounded-lg transition text-lg"
          >
            {loading ? 'Creating account...' : 'Get Started'}
          </button>
        </form>

        <p className="text-center text-gray-600 text-sm mt-6">
          Already have an account?{' '}
          <a href="#login" className="text-blue-600 hover:underline font-semibold">
            Log in
          </a>
        </p>
      </div>
    </div>
  );
}
