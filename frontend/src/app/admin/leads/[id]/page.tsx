'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import AdminLayout from '@/components/admin/AdminLayout';
import { getToken } from '@/lib/auth';
import { fetchLeadDetail, fetchLeadSequences, fetchLeadEvents, updateLeadStage, generateLeadAssist } from '@/lib/api';
import { LeadDetail, LeadSequenceItem } from '@/types/admin';

interface AutomationEvent {
  event_type: string;
  status: string;
  detail_json: Record<string, unknown> | null;
  created_at: string;
}

const STAGES = ['new', 'contacted', 'qualified', 'appointment', 'won', 'lost'] as const;

const STAGE_COLORS: Record<string, string> = {
  new: 'bg-gray-100 text-gray-800',
  contacted: 'bg-blue-100 text-blue-800',
  qualified: 'bg-purple-100 text-purple-800',
  appointment: 'bg-orange-100 text-orange-800',
  won: 'bg-green-100 text-green-800',
  lost: 'bg-red-100 text-red-800',
};

function StageBadge({ stage }: { stage: string }) {
  return (
    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full capitalize ${STAGE_COLORS[stage] || 'bg-gray-100 text-gray-700'}`}>
      {stage}
    </span>
  );
}

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
  const [events, setEvents] = useState<AutomationEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Stage management
  const [selectedStage, setSelectedStage] = useState('new');
  const [dealAmount, setDealAmount] = useState('');
  const [stageSaving, setStageSaving] = useState(false);
  const [stageError, setStageError] = useState('');
  const [stageSuccess, setStageSuccess] = useState('');

  // AI Conversion Assist
  const [assist, setAssist] = useState<{ mode: string; data: { next_action: string; sms_script: string; email_script: string; call_talking_points: string[] } } | null>(null);
  const [assistLoading, setAssistLoading] = useState(false);
  const [assistError, setAssistError] = useState('');
  const [copied, setCopied] = useState('');

  useEffect(() => {
    const loadLead = async () => {
      const token = getToken();
      if (!token) return;

      try {
        const data = await fetchLeadDetail(token, params.id as string);
        setLead(data);
        setSelectedStage(data.stage || 'new');
        setDealAmount(data.deal_amount ? String(data.deal_amount) : '');
        try {
          const seqs = await fetchLeadSequences(token, params.id as string);
          setSequences(seqs);
        } catch {
          // Sequences are optional, don't show error
        }
        try {
          const ev = await fetchLeadEvents(token, params.id as string);
          setEvents(ev.events ?? []);
        } catch {
          // Events are optional
        }
      } catch {
        setError('Failed to load lead details');
      } finally {
        setLoading(false);
      }
    };
    loadLead();
  }, [params.id]);

  const handleStageSave = async () => {
    const token = getToken();
    if (!token || !lead) return;

    setStageError('');
    setStageSuccess('');
    setStageSaving(true);

    try {
      const payload: { stage: string; deal_amount?: number } = { stage: selectedStage };
      if (selectedStage === 'won') {
        if (!dealAmount || parseFloat(dealAmount) <= 0) {
          setStageError('Deal amount is required for won deals');
          setStageSaving(false);
          return;
        }
        payload.deal_amount = parseFloat(dealAmount);
      }

      const updated = await updateLeadStage(token, lead.id, payload);
      setLead(updated);
      setSelectedStage(updated.stage || 'new');
      setDealAmount(updated.deal_amount ? String(updated.deal_amount) : '');
      setStageSuccess('Stage updated');
      setTimeout(() => setStageSuccess(''), 3000);
    } catch (err: unknown) {
      setStageError(err instanceof Error ? err.message : 'Failed to update stage');
    } finally {
      setStageSaving(false);
    }
  };

  const handleGenerateAssist = async () => {
    const token = getToken();
    if (!token || !lead) return;
    setAssistError('');
    setAssistLoading(true);
    try {
      const result = await generateLeadAssist(token, lead.id);
      setAssist(result);
    } catch (err: unknown) {
      setAssistError(err instanceof Error ? err.message : 'Failed to generate assist');
    } finally {
      setAssistLoading(false);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(label);
      setTimeout(() => setCopied(''), 2000);
    });
  };

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
                <StageBadge stage={lead.stage || 'new'} />
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

            {/* Pipeline Stage Manager */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Stage</h2>

              {/* Visual pipeline */}
              <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-2">
                {STAGES.map((s, i) => {
                  const currentIdx = STAGES.indexOf((lead.stage || 'new') as typeof STAGES[number]);
                  const isActive = i <= currentIdx;
                  const isCurrent = s === (lead.stage || 'new');
                  return (
                    <div key={s} className="flex items-center">
                      <div className={`px-3 py-1.5 rounded text-xs font-medium capitalize whitespace-nowrap ${
                        isCurrent
                          ? STAGE_COLORS[s]
                          : isActive
                          ? 'bg-gray-200 text-gray-700'
                          : 'bg-gray-50 text-gray-400'
                      }`}>
                        {s}
                      </div>
                      {i < STAGES.length - 1 && (
                        <div className={`w-4 h-px mx-0.5 ${isActive ? 'bg-gray-400' : 'bg-gray-200'}`} />
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Stage</label>
                  <select
                    value={selectedStage}
                    onChange={(e) => setSelectedStage(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    {STAGES.map((s) => (
                      <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
                    ))}
                  </select>
                </div>

                {selectedStage === 'won' && (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Deal Amount ($) *</label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={dealAmount}
                      onChange={(e) => setDealAmount(e.target.value)}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                      placeholder="e.g. 8400"
                    />
                  </div>
                )}

                <div>
                  <button
                    onClick={handleStageSave}
                    disabled={stageSaving}
                    className="bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                  >
                    {stageSaving ? 'Saving...' : 'Save Stage'}
                  </button>
                </div>
              </div>

              {stageError && (
                <div className="mt-3 text-sm text-red-600">{stageError}</div>
              )}
              {stageSuccess && (
                <div className="mt-3 text-sm text-green-600">{stageSuccess}</div>
              )}

              {lead.deal_amount != null && (
                <div className="mt-4 pt-4 border-t text-sm text-gray-600">
                  Deal Value: <span className="font-semibold text-gray-900">${lead.deal_amount.toLocaleString()}</span>
                  {lead.stage_updated_at && (
                    <span className="ml-4 text-xs text-gray-400">
                      Updated: {new Date(lead.stage_updated_at).toLocaleString()}
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* AI Conversion Assist */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">AI Conversion Assist</h2>
                <div className="flex items-center gap-2">
                  {assist?.mode === 'stub' && (
                    <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">
                      Safe Mode
                    </span>
                  )}
                  <button
                    onClick={handleGenerateAssist}
                    disabled={assistLoading}
                    className="bg-purple-600 text-white py-1.5 px-4 rounded-md text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
                  >
                    {assistLoading ? 'Generating...' : assist ? 'Regenerate' : 'Generate Assist'}
                  </button>
                </div>
              </div>

              {assistError && (
                <div className="text-sm text-red-600 mb-3">{assistError}</div>
              )}

              {assistLoading && (
                <div className="text-center text-gray-400 py-6">Generating personalized scripts...</div>
              )}

              {assist && !assistLoading && (
                <div className="space-y-5">
                  {/* Next Action */}
                  <div>
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Next Best Action</div>
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-900">
                      {assist.data.next_action}
                    </div>
                  </div>

                  {/* SMS Script */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">SMS Script</div>
                      <button
                        onClick={() => copyToClipboard(assist.data.sms_script, 'sms')}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {copied === 'sms' ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                    <div className="bg-gray-50 border rounded-lg p-3 text-sm text-gray-800 font-mono whitespace-pre-wrap">
                      {assist.data.sms_script}
                    </div>
                  </div>

                  {/* Email Script */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Email Script</div>
                      <button
                        onClick={() => copyToClipboard(assist.data.email_script, 'email')}
                        className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                      >
                        {copied === 'email' ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                    <div className="bg-gray-50 border rounded-lg p-3 text-sm text-gray-800 whitespace-pre-wrap">
                      {assist.data.email_script}
                    </div>
                  </div>

                  {/* Call Talking Points */}
                  <div>
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Call Talking Points</div>
                    <ul className="bg-gray-50 border rounded-lg p-3 space-y-1.5">
                      {assist.data.call_talking_points.map((point, i) => (
                        <li key={i} className="text-sm text-gray-800 flex gap-2">
                          <span className="text-gray-400 shrink-0">{i + 1}.</span>
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {!assist && !assistLoading && !assistError && (
                <p className="text-sm text-gray-400">Click &quot;Generate Assist&quot; to get AI-powered next actions, SMS/email scripts, and call talking points for this lead.</p>
              )}
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

            {/* Automation Timeline */}
            {events.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Automation Timeline</h2>
                <div className="relative">
                  <div className="absolute left-3 top-0 bottom-0 w-px bg-gray-200" />
                  <div className="space-y-4">
                    {events.map((ev, i) => (
                      <TimelineEntry key={i} event={ev} />
                    ))}
                  </div>
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

function TimelineEntry({ event }: { event: AutomationEvent }) {
  const [open, setOpen] = useState(false);

  const statusColor: Record<string, string> = {
    success: 'bg-green-100 text-green-800',
    sent: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    skipped_missing_config: 'bg-yellow-100 text-yellow-800',
  };

  const dotColor: Record<string, string> = {
    success: 'bg-green-500',
    sent: 'bg-green-500',
    failed: 'bg-red-500',
    skipped_missing_config: 'bg-yellow-500',
  };

  const label = event.event_type.replace(/_/g, ' ');
  const ts = new Date(event.created_at).toLocaleString();

  return (
    <div className="relative pl-8">
      <div className={`absolute left-1.5 top-1.5 w-3 h-3 rounded-full ${dotColor[event.status] ?? 'bg-gray-400'}`} />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-900 capitalize">{label}</span>
            <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusColor[event.status] ?? 'bg-gray-100 text-gray-700'}`}>
              {event.status}
            </span>
          </div>
          <span className="text-xs text-gray-400">{ts}</span>
        </div>
        {event.detail_json && (
          <button
            onClick={() => setOpen(!open)}
            className="text-xs text-blue-600 hover:text-blue-800 whitespace-nowrap"
          >
            {open ? 'Hide' : 'Details'}
          </button>
        )}
      </div>
      {open && event.detail_json && (
        <pre className="mt-1 text-xs bg-gray-50 rounded p-2 overflow-x-auto text-gray-600">
          {JSON.stringify(event.detail_json, null, 2)}
        </pre>
      )}
    </div>
  );
}
