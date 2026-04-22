'use client';

import { useEffect, useState } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';
import { getToken } from '@/lib/auth';
import { fetchDashboard, fetchCampaigns, fetchPipelineMetrics, fetchDashboardInsights } from '@/lib/api';
import type { DashboardMetrics, PipelineMetrics, OrgInsights } from '@/types/admin';

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
  const [pipeline, setPipeline] = useState<PipelineMetrics | null>(null);
  const [insights, setInsights] = useState<OrgInsights | null>(null);
  const [actualRoas, setActualRoas] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      const token = getToken();
      if (!token) return;
      try {
        const [data, pipelineData, insightsData] = await Promise.all([
          fetchDashboard(token),
          fetchPipelineMetrics(token).catch(() => null),
          fetchDashboardInsights(token).catch(() => null),
        ]);
        setMetrics(data.metrics);
        if (pipelineData) setPipeline(pipelineData);
        if (insightsData) setInsights(insightsData);

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
              <KpiCard label="Pipeline Value" value={fmt$(metrics.pipeline_value)} sub="qualified + proposal" />
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

            {/* AI Insights (Sprint 8) */}
            {insights && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-gray-600">AI Insights</h2>
                  {insights.mode === 'stub' && (
                    <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700">
                      Basic
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-800 mb-3">{insights.summary}</p>
                <ul className="space-y-1.5">
                  {insights.highlights.map((h, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="text-blue-500 mt-0.5 shrink-0">&#8226;</span>
                      {h}
                    </li>
                  ))}
                </ul>
              </div>
            )}

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

            {/* Pipeline Metrics (Sprint 7) */}
            {pipeline && (
              <>
                {/* Pipeline KPIs */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <KpiCard label="Conversion Rate" value={`${pipeline.totals.conversion_rate}%`} accent={pipeline.totals.conversion_rate >= 20 ? 'green' : undefined} />
                  <KpiCard label="Pipeline Value" value={fmt$(pipeline.pipeline.total_value)} sub="qualified + proposal" />
                  <KpiCard label="Won Value" value={fmt$(pipeline.pipeline.won_value)} accent="green" />
                  <KpiCard label="Avg Deal (Won)" value={fmt$(pipeline.pipeline.avg_deal_value)} />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Stage Distribution */}
                  <div className="bg-white rounded-lg shadow-sm border p-6">
                    <h2 className="text-sm font-semibold text-gray-600 mb-4">Stage Distribution</h2>
                    <div className="space-y-2">
                      {(['new', 'contacted', 'qualified', 'proposal', 'won', 'lost'] as const).map((s) => {
                        const count = pipeline.stages[s];
                        const total = pipeline.totals.leads || 1;
                        const pct = Math.round((count / total) * 100);
                        const colors: Record<string, string> = {
                          new: 'bg-gray-400', contacted: 'bg-blue-500', qualified: 'bg-purple-500',
                          proposal: 'bg-orange-500', won: 'bg-green-500', lost: 'bg-red-400',
                        };
                        return (
                          <div key={s}>
                            <div className="flex justify-between text-sm mb-0.5">
                              <span className="capitalize text-gray-700">{s}</span>
                              <span className="text-gray-500">{count} ({pct}%)</span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                              <div className={`h-3 rounded-full ${colors[s]}`} style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Velocity */}
                  <div className="bg-white rounded-lg shadow-sm border p-6">
                    <h2 className="text-sm font-semibold text-gray-600 mb-4">Velocity</h2>
                    <div className="space-y-4">
                      <div>
                        <div className="text-sm text-gray-500">Avg Days to Close</div>
                        <div className="text-2xl font-bold text-gray-900">
                          {pipeline.velocity.avg_days_to_close !== null
                            ? `${pipeline.velocity.avg_days_to_close}d`
                            : '—'}
                        </div>
                      </div>
                      <div className="border-t pt-3">
                        <div className="text-xs text-gray-400 mb-2">Avg Days in Stage</div>
                        <div className="space-y-1.5">
                          {(['new', 'contacted', 'qualified', 'proposal'] as const).map((s) => (
                            <div key={s} className="flex justify-between text-sm">
                              <span className="capitalize text-gray-600">{s}</span>
                              <span className="font-medium text-gray-900">
                                {pipeline.velocity.avg_days_in_stage[s] !== null
                                  ? `${pipeline.velocity.avg_days_in_stage[s]}d`
                                  : '—'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actionability */}
                  <div className="bg-white rounded-lg shadow-sm border p-6">
                    <h2 className="text-sm font-semibold text-gray-600 mb-4">Action Needed</h2>
                    <div className="space-y-5">
                      <div>
                        <div className="text-sm text-gray-500">Overdue Actions</div>
                        <div className={`text-2xl font-bold ${pipeline.actionability.overdue_next_actions > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                          {pipeline.actionability.overdue_next_actions}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">next_action_at &lt; now</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Stale Leads</div>
                        <div className={`text-2xl font-bold ${pipeline.actionability.stale_leads > 0 ? 'text-yellow-600' : 'text-gray-900'}`}>
                          {pipeline.actionability.stale_leads}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">No contact in 7+ days</div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
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
