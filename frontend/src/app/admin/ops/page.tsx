'use client';

import { useEffect, useState } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';
import { fetchHealth } from '@/lib/api';

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
        ok
          ? 'bg-green-100 text-green-800'
          : 'bg-red-100 text-red-800'
      }`}
    >
      {ok ? 'OK' : 'NOT CONFIGURED'}
    </span>
  );
}

export default function OpsPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setError('Unable to reach backend'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AdminLayout>
      <div className="max-w-lg mx-auto">
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
    </AdminLayout>
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
