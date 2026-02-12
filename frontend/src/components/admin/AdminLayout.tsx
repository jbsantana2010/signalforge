'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { removeToken, isAuthenticated } from '@/lib/auth';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/admin/login');
    } else {
      setChecked(true);
    }
  }, [router]);

  const handleLogout = () => {
    removeToken();
    router.push('/admin/login');
  };

  if (!checked) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center space-x-8">
              <a href="/admin/leads" className="text-xl font-bold text-blue-600">
                LeadForge
              </a>
              <a
                href="/admin/leads"
                className="text-gray-700 hover:text-blue-600 font-medium"
              >
                Leads
              </a>
            </div>
            <button
              onClick={handleLogout}
              className="text-gray-500 hover:text-gray-700 text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
