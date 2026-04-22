'use client';

import { useEffect, useState } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';
import { fetchHealth, runEngagementWorker, fetchHandoffQueue, resolveHandoff } from '@/lib/api';
import { getToken } from '@/lib/auth';
import type { EngagementWorkerResult, HandoffQueueResponse } from '@/types/admin';

interface HealthData {
  status: string;
  database: string;
  twilio_configured: boolean;
  smtp_configured: boolean;
  claude_configured: boolean;
}

function Badge({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
        ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      }`}
    >
      {ok ? 'OK' : 'NOT CONFIGURED'}
    </span>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-5 py-4">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      {children}
    </div>
  );
}

export default function OpsPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Engagement worker state
  const [workerRunning, setWorkerRunning] = useState(false);
  const [workerResult, setWorkerResult] = useState<EngagementWorkerResult | null>(null);
  const [workerError, setWorkerError] = useState('');

  // Handoff queue
  const [handoffQueue, setHandoffQueue] = useState<HandoffQueueResponse | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setError('Unable to reach backend'))
      .finally(() => setLoading(false));

    const token = getToken();
    if (token) {
      fetchHandoffQueue(token)
        .then(setHandoffQueue)
        .catch(() => {/* silently ignore — queue is non-critical */});
    }
  }, []);

  const handleRunWorker = async () => {
    const token = getToken();
    if (!token) return;

    setWorkerRunning(true);
    setWorkerError('');
    setWorkerResult(null);

    try {
      const result = await runEngagementWorker(token);
      setWorkerResult(result);
    } catch (err: unknown) {
      setWorkerError(err instanceof Error ? err.message : 'Worker run failed');
    } finally {
      setWorkerRunning(false);
    }
  };

  const handleResolve = async (leadId: string) => {
    const token = getToken();
    if (!token) return;
    setResolvingId(leadId);
    try {
      await resolveHandoff(token, leadId);
      const updated = await fetchHandoffQueue(token);
      setHandoffQueue(updated);
    } catch {
      // silently ignore
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <AdminLayout>
      <div className="max-w-lg mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-6">System Status</h1>

          {loading && <div className="text-gray-500 py-8 text-center">Checking...</div>}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          {health && (
            <div className="bg-white rounded-lg shadow-sm border divide-y">
              <Row label="System Status">
                <Badge ok={health.status === 'ok'} />
              </Row>
              <Row label="Database">
                <Badge ok={health.database === 'connected'} />
              </Row>
              <Row label="Twilio (SMS/Voice)">
                <Badge ok={health.twilio_configured} />
              </Row>
              <Row label="SMTP (Email)">
                <Badge ok={health.smtp_configured} />
              </Row>
              <Row label="Claude AI (Scoring)">
                <Badge ok={health.claude_configured} />
              </Row>
            </div>
          )}

          <p className="text-xs text-gray-400 mt-4 text-center">
            Services marked NOT CONFIGURED will gracefully degrade. No crashes.
          </p>
        </div>

        {/* Engagement Engine Controls */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Engagement Engine</h2>
          <div className="bg-white rounded-lg shadow-sm border p-5">
            <p className="text-sm text-gray-500 mb-4">
              Manually process all due engagement steps. Use this to trigger delivery when
              the automatic inline worker has not run yet.
            </p>

            <button
              onClick={handleRunWorker}
              disabled={workerRunning}
              className="bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {workerRunning ? 'Running...' : 'Run Due Engagement Steps'}
            </button>

            {workerError && (
              <div className="mt-3 text-sm text-red-600">{workerError}</div>
            )}

            {workerResult && (
              <div className="mt-4 border-t pt-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Run Result
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <StatBox label="Processed" value={workerResult.processed} color="text-gray-900" />
                  <StatBox label="Sent" value={workerResult.sent} color="text-green-700" />
                  <StatBox label="Skipped" value={workerResult.skipped_missing_config} color="text-orange-600" />
                  <StatBox label="Failed" value={workerResult.failed} color="text-red-600" />
                </div>
                {workerResult.processed === 0 && (
                  <p className="text-xs text-gray-400 mt-3">No due steps found — all caught up.</p>
                )}
              </div>
            )}
          </div>

          <p className="text-xs text-gray-400 mt-2">
            V1.1 — admin-triggered only. Automatic cron scheduler is not yet enabled.
          </p>
        </div>

        {/* Human Handoff Queue */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Human Handoff Queue</h2>
          <div className="bg-white rounded-lg shadow-sm border p-5">
            {handoffQueue === null ? (
              <p className="text-sm text-gray-400">Loading...</p>
            ) : handoffQueue.count === 0 ? (
              <p className="text-sm text-gray-500">No leads currently need human follow-up.</p>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl font-bold text-red-600">{handoffQueue.count}</span>
                  <span className="text-sm text-gray-500">
                    lead{handoffQueue.count !== 1 ? 's' : ''} need human follow-up
                  </span>
                </div>
                {handoffQueue.leads.length > 0 && (
                  <div className="space-y-2 border-t pt-4">
                    {handoffQueue.leads.map((lead) => (
                      <div key={lead.id} className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
                        <div className="min-w-0">
                          <span className="text-sm font-medium text-gray-900">
                            {lead.name ?? 'Unknown'}
                          </span>
                          <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <span className="text-xs text-gray-500 capitalize">{lead.stage}</span>
                            {lead.handoff_reason && (
                              <span className="text-xs text-red-600 capitalize">
                                · {lead.handoff_reason.replace(/_/g, ' ')}
                              </span>
                            )}
                            {lead.owner_email && (
                              <span className="text-xs text-gray-500">
                                · {lead.owner_email}
                              </span>
                            )}
                          </div>
                          {lead.handoff_at && (
                            <span className="text-xs text-gray-400 block mt-0.5">
                              {new Date(lead.handoff_at).toLocaleString()}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => handleResolve(lead.id)}
                          disabled={resolvingId === lead.id}
                          className="ml-4 shrink-0 bg-white border border-red-300 text-red-700 py-1 px-3 rounded-md text-xs font-medium hover:bg-red-50 disabled:opacity-50"
                        >
                          {resolvingId === lead.id ? 'Resolving...' : 'Resolve'}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}

function StatBox({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
