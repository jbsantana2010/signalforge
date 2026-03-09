'use client';

import { useEffect, useState } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';
import { fetchHealth, runEngagementWorker } from '@/lib/api';
import { getToken } from '@/lib/auth';
import type { EngagementWorkerResult } from '@/types/admin';

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

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setError('Unable to reach backend'))
      .finally(() => setLoading(false));
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
