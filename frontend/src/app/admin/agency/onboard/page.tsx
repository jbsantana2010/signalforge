'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, setActiveOrgId } from '@/lib/auth';
import { createAgencyOrg, createOrgFunnel } from '@/lib/api';
import AdminLayout from '@/components/admin/AdminLayout';

export default function OnboardClientPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    org_name: '',
    org_slug: '',
    display_name: '',
    primary_color: '#2563eb',
    support_email: '',
    logo_url: '',
    funnel_name: '',
    funnel_slug: '',
    enable_sequences: true,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const set = (key: string, value: string | boolean) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const token = getToken();
    if (!token) return;

    if (!form.org_name || !form.org_slug || !form.funnel_name || !form.funnel_slug) {
      setError('Org name, slug, funnel name and funnel slug are required.');
      return;
    }

    setLoading(true);
    try {
      // 1) Create the org
      const org = await createAgencyOrg(token, {
        name: form.org_name,
        slug: form.org_slug,
        display_name: form.display_name || undefined,
        primary_color: form.primary_color || undefined,
        support_email: form.support_email || undefined,
        logo_url: form.logo_url || undefined,
      });

      // 2) Create the default funnel
      await createOrgFunnel(token, org.id, {
        name: form.funnel_name,
        slug: form.funnel_slug,
        enable_sequences: form.enable_sequences,
      });

      // 3) Switch to new org
      setActiveOrgId(org.id);

      // 4) Redirect
      router.push('/admin/funnels');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Onboarding failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="max-w-xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Onboard New Client</h1>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Org section */}
          <fieldset className="border border-gray-200 rounded-lg p-4 space-y-3">
            <legend className="text-sm font-semibold text-gray-600 px-1">Organization</legend>
            <div>
              <label className="block text-sm font-medium mb-1">Client Org Name *</label>
              <input
                type="text" required value={form.org_name}
                onChange={(e) => set('org_name', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Acme Solar"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Slug *</label>
              <input
                type="text" required value={form.org_slug}
                onChange={(e) => set('org_slug', e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono"
                placeholder="acme-solar"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Display Name</label>
              <input
                type="text" value={form.display_name}
                onChange={(e) => set('display_name', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1">Primary Color</label>
                <input
                  type="color" value={form.primary_color}
                  onChange={(e) => set('primary_color', e.target.value)}
                  className="w-full h-9 border border-gray-300 rounded-md cursor-pointer"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Support Email</label>
                <input
                  type="email" value={form.support_email}
                  onChange={(e) => set('support_email', e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Logo URL</label>
              <input
                type="url" value={form.logo_url}
                onChange={(e) => set('logo_url', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="https://..."
              />
            </div>
          </fieldset>

          {/* Funnel section */}
          <fieldset className="border border-gray-200 rounded-lg p-4 space-y-3">
            <legend className="text-sm font-semibold text-gray-600 px-1">Default Funnel</legend>
            <div>
              <label className="block text-sm font-medium mb-1">Funnel Name *</label>
              <input
                type="text" required value={form.funnel_name}
                onChange={(e) => set('funnel_name', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Main Lead Funnel"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Funnel Slug *</label>
              <input
                type="text" required value={form.funnel_slug}
                onChange={(e) => set('funnel_slug', e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono"
                placeholder="main-funnel"
              />
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox" id="seq" checked={form.enable_sequences}
                onChange={(e) => set('enable_sequences', e.target.checked)}
                className="rounded border-gray-300"
              />
              <label htmlFor="seq" className="text-sm">Enable SMS sequences</label>
            </div>
          </fieldset>

          <button
            type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white py-2.5 px-4 rounded-md font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Onboard Client'}
          </button>
        </form>
      </div>
    </AdminLayout>
  );
}
