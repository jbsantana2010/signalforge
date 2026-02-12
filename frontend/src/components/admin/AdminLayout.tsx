'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { removeToken, isAuthenticated, getToken, getActiveOrgId, setActiveOrgId } from '@/lib/auth';
import { fetchAgencyOrgs } from '@/lib/api';
import type { OrgListItem } from '@/types/admin';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [orgs, setOrgs] = useState<OrgListItem[]>([]);
  const [activeOrgId, setActiveOrgIdState] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/admin/login');
      return;
    }
    setChecked(true);
    setActiveOrgIdState(getActiveOrgId());

    const token = getToken();
    if (token) {
      fetchAgencyOrgs(token)
        .then((data) => {
          setOrgs(data.orgs);
          // If no active org set yet, default to first
          if (!getActiveOrgId() && data.orgs.length > 0) {
            setActiveOrgId(data.orgs[0].id);
            setActiveOrgIdState(data.orgs[0].id);
          }
        })
        .catch(() => {});
    }
  }, [router]);

  const handleLogout = () => {
    removeToken();
    router.push('/admin/login');
  };

  const handleOrgSwitch = (orgId: string) => {
    setActiveOrgId(orgId);
    setActiveOrgIdState(orgId);
    // Reload data by navigating to current path
    window.location.reload();
  };

  const activeOrg = orgs.find((o) => o.id === activeOrgId);
  const primaryColor = activeOrg?.primary_color ?? '#2563eb';

  if (!checked) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50" style={{ '--brand-color': primaryColor } as React.CSSProperties}>
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center space-x-8">
              {activeOrg?.logo_url ? (
                <a href="/admin/leads" className="flex items-center space-x-2">
                  <img src={activeOrg.logo_url} alt="" className="h-8 w-auto" />
                  <span className="text-xl font-bold" style={{ color: primaryColor }}>
                    {activeOrg.display_name ?? activeOrg.name}
                  </span>
                </a>
              ) : (
                <a href="/admin/leads" className="text-xl font-bold" style={{ color: primaryColor }}>
                  {activeOrg?.display_name ?? activeOrg?.name ?? 'LeadForge'}
                </a>
              )}
              <a
                href="/admin/leads"
                className="text-gray-700 hover:text-blue-600 font-medium"
              >
                Leads
              </a>
              <a
                href="/admin/funnels"
                className="text-gray-700 hover:text-blue-600 font-medium"
              >
                Funnels
              </a>
            </div>
            <div className="flex items-center space-x-4">
              {orgs.length > 1 && (
                <select
                  value={activeOrgId ?? ''}
                  onChange={(e) => handleOrgSwitch(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {orgs.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.display_name ?? org.name}
                    </option>
                  ))}
                </select>
              )}
              <button
                onClick={handleLogout}
                className="text-gray-500 hover:text-gray-700 text-sm font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
