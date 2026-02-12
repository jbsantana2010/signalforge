'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import AdminLayout from '@/components/admin/AdminLayout';
import { getToken } from '@/lib/auth';
import { fetchLeadDetail } from '@/lib/api';
import { LeadDetail } from '@/types/admin';

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadLead = async () => {
      const token = getToken();
      if (!token) return;

      try {
        const data = await fetchLeadDetail(token, params.id as string);
        setLead(data);
      } catch {
        setError('Failed to load lead details');
      } finally {
        setLoading(false);
      }
    };
    loadLead();
  }, [params.id]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <AdminLayout>
      <div>
        <button
          onClick={() => router.push('/admin/leads')}
          className="text-blue-600 hover:text-blue-800 text-sm font-medium mb-6 inline-block"
        >
          &larr; Back to Leads
        </button>

        {loading && (
          <div className="text-center text-gray-500 py-12">Loading...</div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {lead && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold text-gray-900">Lead Detail</h1>
              <div className="flex items-center gap-3">
                <span className={`inline-flex px-3 py-1 text-sm font-medium rounded-full ${
                  lead.is_spam
                    ? 'bg-red-100 text-red-800'
                    : 'bg-green-100 text-green-800'
                }`}>
                  {lead.is_spam ? 'Spam' : 'Valid'}
                </span>
                <span className="text-sm text-gray-500">
                  {formatDate(lead.created_at)}
                </span>
              </div>
            </div>

            {/* Answers */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Answers</h2>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {Object.entries(lead.answers_json).map(([key, value]) => (
                  <div key={key} className="border-b pb-3">
                    <dt className="text-sm font-medium text-gray-500 capitalize">
                      {key.replace(/_/g, ' ')}
                    </dt>
                    <dd className="text-sm text-gray-900 mt-1">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>

            {/* Meta Info */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Meta</h2>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border-b pb-3">
                  <dt className="text-sm font-medium text-gray-500">Lead ID</dt>
                  <dd className="text-sm text-gray-900 mt-1 font-mono">{lead.id}</dd>
                </div>
                <div className="border-b pb-3">
                  <dt className="text-sm font-medium text-gray-500">Language</dt>
                  <dd className="text-sm text-gray-900 mt-1 uppercase">{lead.language}</dd>
                </div>
                <div className="border-b pb-3">
                  <dt className="text-sm font-medium text-gray-500">Score</dt>
                  <dd className="text-sm text-gray-900 mt-1">
                    {lead.score !== null ? lead.score : 'Not scored'}
                  </dd>
                </div>
                <div className="border-b pb-3">
                  <dt className="text-sm font-medium text-gray-500">Funnel ID</dt>
                  <dd className="text-sm text-gray-900 mt-1 font-mono">{lead.funnel_id}</dd>
                </div>
              </dl>
            </div>

            {/* Source Data */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Source / Attribution</h2>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {lead.source_json.utm_source && (
                  <div className="border-b pb-3">
                    <dt className="text-sm font-medium text-gray-500">UTM Source</dt>
                    <dd className="text-sm text-gray-900 mt-1">{lead.source_json.utm_source}</dd>
                  </div>
                )}
                {lead.source_json.utm_medium && (
                  <div className="border-b pb-3">
                    <dt className="text-sm font-medium text-gray-500">UTM Medium</dt>
                    <dd className="text-sm text-gray-900 mt-1">{lead.source_json.utm_medium}</dd>
                  </div>
                )}
                {lead.source_json.utm_campaign && (
                  <div className="border-b pb-3">
                    <dt className="text-sm font-medium text-gray-500">UTM Campaign</dt>
                    <dd className="text-sm text-gray-900 mt-1">{lead.source_json.utm_campaign}</dd>
                  </div>
                )}
                {lead.source_json.referrer && (
                  <div className="border-b pb-3">
                    <dt className="text-sm font-medium text-gray-500">Referrer</dt>
                    <dd className="text-sm text-gray-900 mt-1 break-all">{lead.source_json.referrer}</dd>
                  </div>
                )}
                {lead.source_json.landing_url && (
                  <div className="border-b pb-3 sm:col-span-2">
                    <dt className="text-sm font-medium text-gray-500">Landing URL</dt>
                    <dd className="text-sm text-gray-900 mt-1 break-all">{lead.source_json.landing_url}</dd>
                  </div>
                )}
                {!lead.source_json.utm_source &&
                  !lead.source_json.utm_medium &&
                  !lead.source_json.utm_campaign &&
                  !lead.source_json.referrer &&
                  !lead.source_json.landing_url && (
                  <div className="sm:col-span-2">
                    <p className="text-sm text-gray-500 italic">No source data available</p>
                  </div>
                )}
              </dl>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
