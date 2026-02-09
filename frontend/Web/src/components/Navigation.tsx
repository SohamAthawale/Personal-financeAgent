import React from 'react';
import { LogOut, Menu, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

/**
 * Central page type (must match App.tsx)
 */
export type Page = 'dashboard' | 'analytics' | 'insights' | 'goals';

interface NavigationProps {
  currentPage: Page;
  onPageChange: (page: Page) => void;
}

export function Navigation({
  currentPage,
  onPageChange,
}: NavigationProps) {
  const { logout, auth } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const pages: { id: Page; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'analytics', label: 'Analytics' },
    { id: 'insights', label: 'Insights' },
    { id: 'goals', label: 'Goals' },
  ];

  const handlePageChange = (pageId: Page) => {
    onPageChange(pageId);
    setMobileMenuOpen(false);
  };

  const handleLogout = () => {
    logout(); // 🔐 Auth gate will redirect automatically
    setMobileMenuOpen(false);
  };

  const userLabel =
    auth?.user?.phone ||
    auth?.user?.email ||
    'Logged in';

  const getInitials = (value: string) => {
    const cleaned = value.replace(/[^a-zA-Z0-9 ]/g, ' ').trim();
    if (!cleaned) return 'U';
    const parts = cleaned.split(/\s+/);
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return cleaned.slice(0, 2).toUpperCase();
  };

  return (
    <nav className="nav-shell">
      <div className="app-container px-6">
        <div className="flex flex-wrap items-center justify-between gap-4 py-4">
          <div className="flex items-center gap-3">
            <img
              src="/brand-mark.svg"
              alt="Personal Finance Agent"
              className="h-10 w-10"
            />
            <div className="leading-tight">
              <p className="text-base font-semibold text-ink">
                Personal Finance Agent
              </p>
              <p className="text-xs uppercase tracking-[0.3em] text-muted">
                Clarity first
              </p>
            </div>
          </div>

          {/* Desktop menu */}
          <div className="hidden md:flex items-center gap-2 rounded-full border border-line bg-white/70 p-1 shadow-soft">
            {pages.map((page) => (
              <button
                key={page.id}
                onClick={() => handlePageChange(page.id)}
                className={`nav-pill ${
                  currentPage === page.id ? 'nav-pill-active' : ''
                }`}
                aria-current={currentPage === page.id ? 'page' : undefined}
              >
                {page.label}
              </button>
            ))}
          </div>

          {/* Desktop user info */}
          <div className="hidden md:flex items-center gap-3">
            <div className="flex items-center gap-3 rounded-full border border-line bg-white px-3 py-2 shadow-soft">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-white">
                {getInitials(userLabel)}
              </div>
              <div className="leading-tight">
                <p className="text-xs uppercase tracking-[0.3em] text-muted">
                  Signed in
                </p>
                <p className="text-sm font-semibold text-ink">
                  {userLabel}
                </p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="btn-ghost"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>

          {/* Mobile menu toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden rounded-full border border-line bg-white p-2 text-muted shadow-soft"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden space-y-3 border-t border-line pb-4 pt-4">
            <div className="grid gap-2 rounded-3xl border border-line bg-white/80 p-2 shadow-soft">
              {pages.map((page) => (
                <button
                  key={page.id}
                  onClick={() => handlePageChange(page.id)}
                  className={`nav-pill text-left ${
                    currentPage === page.id ? 'nav-pill-active' : ''
                  }`}
                >
                  {page.label}
                </button>
              ))}
            </div>

            <div className="flex items-center justify-between rounded-3xl border border-line bg-white/80 px-4 py-3 shadow-soft">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-white">
                  {getInitials(userLabel)}
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-muted">
                    Signed in
                  </p>
                  <p className="text-sm font-semibold text-ink">
                    {userLabel}
                  </p>
                </div>
              </div>
              <button onClick={handleLogout} className="btn-ghost">
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
