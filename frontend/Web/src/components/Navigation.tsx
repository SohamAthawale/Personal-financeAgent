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

  return (
    <nav className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-blue-600">
              FA
            </h1>
          </div>

          {/* Desktop menu */}
          <div className="hidden md:flex items-center gap-8">
            {pages.map((page) => (
              <button
                key={page.id}
                onClick={() => handlePageChange(page.id)}
                className={`font-medium transition ${
                  currentPage === page.id
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {page.label}
              </button>
            ))}
          </div>

          {/* Desktop user info */}
          <div className="hidden md:flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {userLabel}
            </span>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-gray-600 hover:text-red-600 transition font-medium"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>

          {/* Mobile menu toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden text-gray-600"
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
          <div className="md:hidden pb-4 border-t border-gray-200">
            {pages.map((page) => (
              <button
                key={page.id}
                onClick={() => handlePageChange(page.id)}
                className={`block w-full text-left py-2 px-4 font-medium transition ${
                  currentPage === page.id
                    ? 'text-blue-600 bg-blue-50'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {page.label}
              </button>
            ))}

            <div className="border-t border-gray-200 mt-4 pt-4">
              <p className="px-4 text-sm text-gray-600 mb-2">
                {userLabel}
              </p>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 w-full text-left py-2 px-4 text-gray-600 hover:text-red-600 transition font-medium"
              >
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
