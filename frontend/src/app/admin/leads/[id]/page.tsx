'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import AdminLayout from '@/components/admin/AdminLayout';
import { getToken } from '@/lib/auth';
import { fetchLeadDetail, fetchLeadSequences } from '@/lib/api';
import { LeadDetail, LeadSequenceItem } from '@/types/admin';

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    high: 'bg-red-100 text-red-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-green-100 text-green-800',
  };
  return (
    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${colors[priority] || 'bg-gray-100 text-gray-700'}`}>
      {priority}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    sent: 'bg-green-100 text-green-800',
    delivered: 'bg-green-100 text-green-800',
    completed: 'bg-green-100 text-green-800',
    pending: 'bg-yellow-100 text-yellow-800',
    queued: 'bg-yellow-100 text-yellow-800',
    failed: 'bg-red-100 text-red-800',
    skipped: 'bg-gray-100 text-gray-600',
  };
  return (
    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${colors[status] || 'bg-gray-100 text-gray-700'}`}>
      {status}
    </span>
  );
}

function AiScoreBadge({ score }: { score: number }) {
  let color = 'bg-red-100 text-red-800';
  if (score >= 70) color = 'bg-green-100 text-green-800';
  else if (score >= 50) color = 'bg-yellow-100 text-yellow-800';
  return (
    <span className={`inline-flex px-3 py-1 text-sm font-bold rounded-full ${color}`}>
      {score}
    </span>
  );
}

export default function LeadDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [sequences, setSequences] = useState<LeadSequenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadLead = async () => {
      const token = getToken();
      if (!token) return;

      try {
        const data = await fetchLeadDetail(token, params.id as string);
        setLead(data);
        try {
          const seqs = await fetchLeadSequences(token, params.id as string);
          setSequences(seqs);
        } catch {
          // Sequences are optional, don't show error
        }
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
                {lead.priority && <PriorityBadge priority={lead.priority} />}
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

            {/* AI Insights */}
            {(lead.ai_score != null || lead.ai_summary || (lead.tags && lead.tags.length > 0)) && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Insights</h2>
                <div className="space-y-4">
                  {lead.ai_score != null && (
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-gray-500">AI Score:</span>
                      <AiScoreBadge score={lead.ai_score} />
                    </div>
                  )}
                  {lead.ai_summary && (
                    <div>
                      <span className="text-sm font-medium text-gray-500">AI Summary:</span>
                      <p className="text-sm text-gray-900 mt-1">{lead.ai_summary}</p>
                    </div>
                  )}
                  {lead.tags && lead.tags.length > 0 && (
                    <div>
                      <span className="text-sm font-medium text-gray-500">Tags:</span>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {lead.tags.map((tag) => (
                          <span
                            key={tag}
                            className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Contact Status */}
            {(lead.email_status || lead.sms_status || lead.call_status || lead.contact_status || lead.last_contacted_at) && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Contact Status</h2>
                <dl className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {lead.email_status && (
                    <div className="border-b pb-3">
                      <dt className="text-sm font-medium text-gray-500">Email Status</dt>
                      <dd className="mt-1"><StatusBadge status={lead.email_status} /></dd>
                    </div>
                  )}
                  {lead.sms_status && (
                    <div className="border-b pb-3">
                      <dt className="text-sm font-medium text-gray-500">SMS Status</dt>
                      <dd className="mt-1"><StatusBadge status={lead.sms_status} /></dd>
                    </div>
                  )}
                  {lead.call_status && (
                    <div className="border-b pb-3">
                      <dt className="text-sm font-medium text-gray-500">Call Status</dt>
                      <dd className="mt-1"><StatusBadge status={lead.call_status} /></dd>
                    </div>
                  )}
                  {lead.call_attempts != null && lead.call_attempts > 0 && (
                    <div className="border-b pb-3">
                      <dt className="text-sm font-medium text-gray-500">Call Attempts</dt>
                      <dd className="text-sm text-gray-900 mt-1">{lead.call_attempts}</dd>
                    </div>
                  )}
                  {lead.contact_status && (
                    <div className="border-b pb-3">
                      <dt className="text-sm font-medium text-gray-500">Contact Status</dt>
                      <dd className="mt-1"><StatusBadge status={lead.contact_status} /></dd>
                    </div>
                  )}
                  {lead.last_contacted_at && (
                    <div className="border-b pb-3">
                      <dt className="text-sm font-medium text-gray-500">Last Contacted</dt>
                      <dd className="text-sm text-gray-900 mt-1">{formatDate(lead.last_contacted_at)}</dd>
                    </div>
                  )}
                </dl>
              </div>
            )}

            {/* SMS Sequences */}
            {sequences.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">SMS Sequence</h2>
                <div className="space-y-2">
                  {sequences.map((seq) => (
                    <div key={seq.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-gray-500">Step {seq.step}</span>
                        <span className="text-sm text-gray-700 truncate max-w-md">{seq.message || '-'}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          seq.status === 'sent' ? 'bg-green-100 text-green-800' :
                          seq.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                          seq.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {seq.status}
                        </span>
                        {seq.sent_at && (
                          <span className="text-xs text-gray-500">
                            {new Date(seq.sent_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
