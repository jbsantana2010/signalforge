'use client';

import { useState, useEffect, useCallback } from 'react';
import { getToken } from '@/lib/auth';
import { fetchCampaigns, createCampaign, updateCampaignSpend } from '@/lib/api';
import AdminLayout from '@/components/admin/AdminLayout';

interface CampaignMetric {
  id: string;
  campaign_name: string;
  source: string;
  utm_campaign: string;
  leads: number;
  avg_ai_score: number;
  estimated_revenue: number;
  ad_spend: number;
  cost_per_lead: number | null;
  roas: number | null;
  won_deals: number;
  actual_revenue: number;
  actual_roas: number | null;
}

const SOURCE_OPTIONS = ['facebook', 'google', 'tiktok', 'manual'];

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<CampaignMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    campaign_name: '',
    source: 'google',
    utm_campaign: '',
    ad_spend: '',
  });
  const [creating, setCreating] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [editSpend, setEditSpend] = useState('');

  const loadCampaigns = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      const data = await fetchCampaigns(token);
      // Sort by ROAS descending (nulls last)
      const sorted = [...data.campaigns].sort((a: CampaignMetric, b: CampaignMetric) => {
        const ra = a.roas ?? -1;
        const rb = b.roas ?? -1;
        return rb - ra;
      });
      setCampaigns(sorted);
    } catch {
      setError('Failed to load campaigns');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const token = getToken();
    if (!token) return;

    if (!form.campaign_name || !form.utm_campaign) {
      setError('Campaign name and UTM campaign key are required.');
      return;
    }

    setCreating(true);
    try {
      await createCampaign(token, {
        campaign_name: form.campaign_name,
        source: form.source,
        utm_campaign: form.utm_campaign,
        ad_spend: form.ad_spend ? parseFloat(form.ad_spend) : 0,
      });
      setForm({ campaign_name: '', source: 'google', utm_campaign: '', ad_spend: '' });
      await loadCampaigns();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create campaign');
    } finally {
      setCreating(false);
    }
  };

  const handleSpendSave = async (campaignId: string) => {
    const token = getToken();
    if (!token) return;
    try {
      await updateCampaignSpend(token, campaignId, parseFloat(editSpend) || 0);
      setEditId(null);
      await loadCampaigns();
    } catch {
      setError('Failed to update spend');
    }
  };

  const roasColor = (roas: number | null) => {
    if (roas === null) return '';
    if (roas > 3) return 'text-green-700 bg-green-50';
    if (roas < 1) return 'text-red-700 bg-red-50';
    return '';
  };

  const set = (key: string, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <AdminLayout>
      <div className="space-y-8">
        <h1 className="text-2xl font-bold">Campaign Attribution</h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Create Campaign Form */}
        <fieldset className="border border-gray-200 rounded-lg p-4">
          <legend className="text-sm font-semibold text-gray-600 px-1">Create Campaign</legend>
          <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-5 gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Campaign Name *</label>
              <input
                type="text" required value={form.campaign_name}
                onChange={(e) => set('campaign_name', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="Summer Solar Push"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Source *</label>
              <select
                value={form.source}
                onChange={(e) => set('source', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                {SOURCE_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">UTM Campaign *</label>
              <input
                type="text" required value={form.utm_campaign}
                onChange={(e) => set('utm_campaign', e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ''))}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono"
                placeholder="solar-summer"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Ad Spend ($)</label>
              <input
                type="number" min="0" step="0.01" value={form.ad_spend}
                onChange={(e) => set('ad_spend', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                placeholder="0.00"
              />
            </div>
            <button
              type="submit" disabled={creating}
              className="bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Add Campaign'}
            </button>
          </form>
        </fieldset>

        {/* Campaign Table */}
        {loading ? (
          <div className="text-gray-500">Loading campaigns...</div>
        ) : campaigns.length === 0 ? (
          <div className="text-gray-500 text-center py-12">
            No campaigns yet. Create one above and use matching <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">utm_campaign</code> values in your funnel links.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Campaign</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Source</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Leads</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Won</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Avg AI</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Est Revenue</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Actual Rev</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Spend</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">CPL</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Est ROAS</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Actual ROAS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {campaigns.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{c.campaign_name}</div>
                      <div className="text-xs text-gray-400 font-mono">{c.utm_campaign}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{c.source}</td>
                    <td className="px-4 py-3 text-right font-mono">{c.leads}</td>
                    <td className="px-4 py-3 text-right font-mono">{c.won_deals}</td>
                    <td className="px-4 py-3 text-right font-mono">{c.avg_ai_score}</td>
                    <td className="px-4 py-3 text-right font-mono">${c.estimated_revenue.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-green-700">${c.actual_revenue.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">
                      {editId === c.id ? (
                        <div className="flex items-center justify-end gap-1">
                          <input
                            type="number" min="0" step="0.01"
                            value={editSpend}
                            onChange={(e) => setEditSpend(e.target.value)}
                            className="w-24 border border-gray-300 rounded px-2 py-1 text-sm text-right font-mono"
                            autoFocus
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleSpendSave(c.id);
                              if (e.key === 'Escape') setEditId(null);
                            }}
                          />
                          <button
                            onClick={() => handleSpendSave(c.id)}
                            className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                          >
                            Save
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => { setEditId(c.id); setEditSpend(String(c.ad_spend)); }}
                          className="font-mono hover:underline cursor-pointer"
                          title="Click to edit spend"
                        >
                          ${c.ad_spend.toLocaleString()}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {c.cost_per_lead !== null ? `$${c.cost_per_lead.toFixed(2)}` : '—'}
                    </td>
                    <td className={`px-4 py-3 text-right font-mono font-semibold rounded ${roasColor(c.roas)}`}>
                      {c.roas !== null ? `${c.roas.toFixed(2)}x` : '—'}
                    </td>
                    <td className={`px-4 py-3 text-right font-mono font-semibold rounded ${roasColor(c.actual_roas)}`}>
                      {c.actual_roas !== null ? `${c.actual_roas.toFixed(2)}x` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
