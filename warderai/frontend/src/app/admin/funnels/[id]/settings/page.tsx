'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import AdminLayout from '@/components/admin/AdminLayout';
import { getToken } from '@/lib/auth';
import { fetchFunnelDetail, updateFunnelSettings, fetchDashboard, updateOrgSettings } from '@/lib/api';
import { FunnelDetail, FunnelUpdateRequest, RoutingRule } from '@/types/admin';

export default function FunnelSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const [funnel, setFunnel] = useState<FunnelDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [autoEmail, setAutoEmail] = useState(false);
  const [autoSms, setAutoSms] = useState(false);
  const [autoCall, setAutoCall] = useState(false);
  const [notificationEmails, setNotificationEmails] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [repPhone, setRepPhone] = useState('');
  const [twilioFrom, setTwilioFrom] = useState('');
  const [hoursStart, setHoursStart] = useState(9);
  const [hoursEnd, setHoursEnd] = useState(17);
  const [routingRules, setRoutingRules] = useState<RoutingRule[]>([]);
  const [sequenceEnabled, setSequenceEnabled] = useState(false);
  const [sequenceConfig, setSequenceConfig] = useState('');
  const [avgDealValue, setAvgDealValue] = useState(0);
  const [closeRate, setCloseRate] = useState(0);

  useEffect(() => {
    const load = async () => {
      const token = getToken();
      if (!token) return;

      try {
        const data: FunnelDetail = await fetchFunnelDetail(token, params.id as string);
        setFunnel(data);
        setAutoEmail(data.auto_email_enabled);
        setAutoSms(data.auto_sms_enabled);
        setAutoCall(data.auto_call_enabled);
        setNotificationEmails(data.notification_emails?.join(', ') || '');
        setWebhookUrl(data.webhook_url || '');
        setRepPhone(data.rep_phone_number || '');
        setTwilioFrom(data.twilio_from_number || '');
        setHoursStart(data.working_hours_start);
        setHoursEnd(data.working_hours_end);
        setRoutingRules(data.routing_rules?.rules || []);
        setSequenceEnabled(data.sequence_enabled || false);
        setSequenceConfig(
          data.sequence_config
            ? JSON.stringify(data.sequence_config, null, 2)
            : JSON.stringify({
                steps: [
                  { delay_minutes: 0, message: "Thanks for your request!" },
                  { delay_minutes: 1440, message: "Just checking in!" },
                  { delay_minutes: 4320, message: "Last chance to connect!" }
                ]
              }, null, 2)
        );
        // Load org metrics too
        fetchDashboard(token).then((d) => {
          setAvgDealValue(d.metrics.avg_deal_value ?? 0);
          setCloseRate(d.metrics.close_rate_percent ?? 0);
        }).catch(() => {});
      } catch {
        setError('Failed to load funnel settings');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [params.id]);

  const addRule = () => {
    setRoutingRules([
      ...routingRules,
      { when: { field: '', equals: '' }, then: { tag: '', priority: 'medium' } },
    ]);
  };

  const removeRule = (index: number) => {
    setRoutingRules(routingRules.filter((_, i) => i !== index));
  };

  const updateRule = (index: number, rule: RoutingRule) => {
    const updated = [...routingRules];
    updated[index] = rule;
    setRoutingRules(updated);
  };

  const handleSave = async () => {
    const token = getToken();
    if (!token) return;

    setSaving(true);
    setError('');
    setSuccess('');

    const emails = notificationEmails
      .split(',')
      .map((e) => e.trim())
      .filter(Boolean);

    let parsedSequenceConfig;
    if (sequenceEnabled && sequenceConfig) {
      try {
        parsedSequenceConfig = JSON.parse(sequenceConfig);
      } catch {
        setError('Invalid JSON in sequence config');
        setSaving(false);
        return;
      }
    }

    const payload: FunnelUpdateRequest = {
      auto_email_enabled: autoEmail,
      auto_sms_enabled: autoSms,
      auto_call_enabled: autoCall,
      notification_emails: emails,
      webhook_url: webhookUrl || undefined,
      rep_phone_number: repPhone || undefined,
      twilio_from_number: twilioFrom || undefined,
      working_hours_start: hoursStart,
      working_hours_end: hoursEnd,
      routing_rules: { rules: routingRules },
      sequence_enabled: sequenceEnabled,
      sequence_config: parsedSequenceConfig,
    };

    try {
      await updateFunnelSettings(token, params.id as string, payload as unknown as Record<string, unknown>);
      await updateOrgSettings(token, { avg_deal_value: avgDealValue, close_rate_percent: closeRate });
      setSuccess('Settings saved successfully');
    } catch {
      setError('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <AdminLayout>
      <div>
        <button
          onClick={() => router.push('/admin/funnels')}
          className="text-blue-600 hover:text-blue-800 text-sm font-medium mb-6 inline-block"
        >
          &larr; Back to Funnels
        </button>

        {loading && (
          <div className="text-center text-gray-500 py-12">Loading...</div>
        )}

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 mb-6">
            {error}
          </div>
        )}

        {success && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 mb-6">
            {success}
          </div>
        )}

        {funnel && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Funnel Settings: {funnel.name}
              </h1>
              <p className="text-gray-500 text-sm mt-1">
                Slug: {funnel.slug}
              </p>
            </div>

            {/* Automation Toggles */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Automation</h2>
              <div className="space-y-4">
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={autoEmail}
                    onChange={(e) => setAutoEmail(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Auto Email</span>
                </label>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={autoSms}
                    onChange={(e) => setAutoSms(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Auto SMS</span>
                </label>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={autoCall}
                    onChange={(e) => setAutoCall(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Auto Call</span>
                </label>
              </div>
            </div>

            {/* SMS Sequences */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">SMS Follow-up Sequence</h2>
              <div className="space-y-4">
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={sequenceEnabled}
                    onChange={(e) => setSequenceEnabled(e.target.checked)}
                    className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700">Enable SMS Sequences</span>
                </label>
                {sequenceEnabled && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Sequence Config (JSON)
                    </label>
                    <textarea
                      value={sequenceConfig}
                      onChange={(e) => setSequenceConfig(e.target.value)}
                      rows={10}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder='{"steps": [{"delay_minutes": 0, "message": "Thanks!"}]}'
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Each step: delay_minutes (0 = immediate, 1440 = 24h), message text
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Contact Settings */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Contact Settings</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Notification Emails (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={notificationEmails}
                    onChange={(e) => setNotificationEmails(e.target.value)}
                    placeholder="admin@example.com, sales@example.com"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Webhook URL
                  </label>
                  <input
                    type="text"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    placeholder="https://example.com/webhook"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Rep Phone Number
                  </label>
                  <input
                    type="text"
                    value={repPhone}
                    onChange={(e) => setRepPhone(e.target.value)}
                    placeholder="+1234567890"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Twilio From Number
                  </label>
                  <input
                    type="text"
                    value={twilioFrom}
                    onChange={(e) => setTwilioFrom(e.target.value)}
                    placeholder="+1234567890"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Working Hours */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Working Hours</h2>
              <div className="flex gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Start Hour (0-23)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={23}
                    value={hoursStart}
                    onChange={(e) => setHoursStart(Number(e.target.value))}
                    className="w-24 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    End Hour (0-23)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={23}
                    value={hoursEnd}
                    onChange={(e) => setHoursEnd(Number(e.target.value))}
                    className="w-24 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Routing Rules */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">Routing Rules</h2>
                <button
                  onClick={addRule}
                  className="px-3 py-1 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                >
                  + Add Rule
                </button>
              </div>
              {routingRules.length === 0 ? (
                <p className="text-sm text-gray-500 italic">No routing rules configured</p>
              ) : (
                <div className="space-y-3">
                  {routingRules.map((rule, index) => (
                    <div key={index} className="flex flex-wrap items-end gap-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex-1 min-w-[120px]">
                        <label className="block text-xs font-medium text-gray-500 mb-1">Field</label>
                        <input
                          type="text"
                          value={rule.when.field}
                          onChange={(e) =>
                            updateRule(index, {
                              ...rule,
                              when: { ...rule.when, field: e.target.value },
                            })
                          }
                          placeholder="service"
                          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div className="flex-1 min-w-[120px]">
                        <label className="block text-xs font-medium text-gray-500 mb-1">Equals</label>
                        <input
                          type="text"
                          value={rule.when.equals}
                          onChange={(e) =>
                            updateRule(index, {
                              ...rule,
                              when: { ...rule.when, equals: e.target.value },
                            })
                          }
                          placeholder="roofing"
                          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div className="flex-1 min-w-[120px]">
                        <label className="block text-xs font-medium text-gray-500 mb-1">Tag</label>
                        <input
                          type="text"
                          value={rule.then.tag}
                          onChange={(e) =>
                            updateRule(index, {
                              ...rule,
                              then: { ...rule.then, tag: e.target.value },
                            })
                          }
                          placeholder="roofing-lead"
                          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div className="min-w-[120px]">
                        <label className="block text-xs font-medium text-gray-500 mb-1">Priority</label>
                        <select
                          value={rule.then.priority}
                          onChange={(e) =>
                            updateRule(index, {
                              ...rule,
                              then: { ...rule.then, priority: e.target.value },
                            })
                          }
                          className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                        </select>
                      </div>
                      <button
                        onClick={() => removeRule(index)}
                        className="px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 rounded hover:bg-red-100"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Revenue Settings (Org-level) */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Revenue Settings</h2>
              <p className="text-xs text-gray-500 mb-4">These values apply to the entire org and are used for estimated revenue on the dashboard.</p>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Avg Deal Value ($)
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={100}
                    value={avgDealValue}
                    onChange={(e) => setAvgDealValue(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Close Rate (%)
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    step={0.5}
                    value={closeRate}
                    onChange={(e) => setCloseRate(Number(e.target.value))}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Save */}
            <div className="flex justify-end">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
