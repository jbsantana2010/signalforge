'use client';

import { useEffect, useState } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';
import { getToken } from '@/lib/auth';
import { fetchDashboard, fetchCampaigns } from '@/lib/api';
import type { DashboardMetrics } from '@/types/admin';

function fmt$(n: number) {
  return '$' + n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtTime(seconds: number | null) {
  if (seconds === null) return '—';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="w-full bg-gray-100 rounded-full h-5 overflow-hidden">
      <div className={`h-5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [actualRoas, setActualRoas] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      const token = getToken();
      if (!token) return;
      try {
        const data = await fetchDashboard(token);
        setMetrics(data.metrics);

        // Calculate actual ROAS from campaigns
        try {
          const campData = await fetchCampaigns(token);
          const campaigns = campData.campaigns ?? [];
          if (campaigns.length > 0) {
            const totalActualRevenue = campaigns.reduce((sum: number, c: { actual_revenue?: number }) => sum + (c.actual_revenue ?? 0), 0);
            const totalSpend = campaigns.reduce((sum: number, c: { ad_spend?: number }) => sum + (c.ad_spend ?? 0), 0);
            if (totalSpend > 0) {
              setActualRoas(Math.round((totalActualRevenue / totalSpend) * 100) / 100);
            }
          }
        } catch {
          // campaigns optional for ROAS
        }
      } catch {
        setError('Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const aiTotal = metrics
    ? metrics.ai_hot_count + metrics.ai_warm_count + metrics.ai_cold_count
    : 0;

  return (
    <AdminLayout>
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

        {loading && <div className="text-gray-500 py-12 text-center">Loading...</div>}
        {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">{error}</div>}

        {metrics && (
          <div className="space-y-6">
            {/* KPI Cards - Row 1: Core */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="Total Leads" value={String(metrics.total_leads)} />
              <KpiCard label="Leads (7 Days)" value={String(metrics.leads_last_7_days)} />
              <KpiCard label="Est. Revenue" value={fmt$(metrics.estimated_revenue)} sub="estimated" />
              <KpiCard label="Contacted" value={`${metrics.contacted_percent}%`} />
            </div>

            {/* KPI Cards - Row 2: Actual Revenue */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="Actual Revenue" value={fmt$(metrics.actual_revenue)} accent="green" />
              <KpiCard label="Won Deals" value={String(metrics.won_deals)} accent="green" />
              <KpiCard label="Pipeline Value" value={fmt$(metrics.pipeline_value)} sub="qualified + appointment" />
              {actualRoas !== null ? (
                <KpiCard
                  label="Actual ROAS"
                  value={`${actualRoas.toFixed(2)}x`}
                  accent={actualRoas >= 3 ? 'green' : actualRoas < 1 ? 'red' : undefined}
                />
              ) : (
                <KpiCard label="Close Rate (Actual)" value={`${metrics.actual_close_rate}%`} />
              )}
            </div>

            {/* Detail Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* AI Distribution */}
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h2 className="text-sm font-semibold text-gray-600 mb-4">AI Lead Distribution</h2>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-red-600 font-medium">Hot (70+)</span>
                      <span>{metrics.ai_hot_count}</span>
                    </div>
                    <Bar value={metrics.ai_hot_count} max={aiTotal || 1} color="bg-red-500" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-yellow-600 font-medium">Warm (40–69)</span>
                      <span>{metrics.ai_warm_count}</span>
                    </div>
                    <Bar value={metrics.ai_warm_count} max={aiTotal || 1} color="bg-yellow-400" />
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-blue-600 font-medium">Cold (&lt;40)</span>
                      <span>{metrics.ai_cold_count}</span>
                    </div>
                    <Bar value={metrics.ai_cold_count} max={aiTotal || 1} color="bg-blue-400" />
                  </div>
                </div>
                {aiTotal === 0 && (
                  <p className="text-xs text-gray-400 mt-3">No AI-scored leads yet</p>
                )}
              </div>

              {/* Response & Call */}
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h2 className="text-sm font-semibold text-gray-600 mb-4">Performance</h2>
                <div className="space-y-5">
                  <div>
                    <div className="text-sm text-gray-500">Avg Response Time</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {fmtTime(metrics.avg_response_seconds)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Call Connect Rate</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {metrics.call_connect_rate}%
                    </div>
                  </div>
                  <div className="pt-2 border-t">
                    <div className="text-xs text-gray-400">Revenue Settings</div>
                    <div className="text-sm text-gray-600">
                      Deal Value: {fmt$(metrics.avg_deal_value)} &middot; Close Rate: {metrics.close_rate_percent}%
                    </div>
                  </div>
                  {(metrics.won_deals > 0 || metrics.lost_deals > 0) && (
                    <div className="pt-2 border-t">
                      <div className="text-xs text-gray-400">Pipeline Summary</div>
                      <div className="text-sm text-gray-600">
                        Won: {metrics.won_deals} &middot; Lost: {metrics.lost_deals} &middot; Actual Close: {metrics.actual_close_rate}%
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}

function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  const accentClass = accent === 'green'
    ? 'text-green-700'
    : accent === 'red'
    ? 'text-red-700'
    : 'text-gray-900';

  return (
    <div className="bg-white rounded-lg shadow-sm border p-5">
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${accentClass}`}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  );
}
