'use client';

import { useState } from 'react';
import { getToken } from '@/lib/auth';
import { generateAdStrategy } from '@/lib/api';
import AdminLayout from '@/components/admin/AdminLayout';

interface Ad {
  primary_text: string;
  headline: string;
  cta: string;
}

interface Strategy {
  angles: string[];
  hooks: string[];
  offers: string[];
  targeting: string[];
  ads: Ad[];
  mode: 'claude' | 'stub';
}

const GOALS = [
  { value: 'sales', label: 'Sales / Lead Generation' },
  { value: 'traffic', label: 'Traffic / Awareness' },
  { value: 'financing', label: 'Financing / Applications' },
];

function Collapsible({ title, count, defaultOpen, children }: {
  title: string; count: number; defaultOpen?: boolean; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
      >
        <span className="font-medium">{title} <span className="text-gray-400 text-sm">({count})</span></span>
        <span className="text-gray-400">{open ? '\u25B2' : '\u25BC'}</span>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button
      onClick={handleCopy}
      className="text-xs text-blue-600 hover:text-blue-800 font-medium shrink-0"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

export default function AIStrategyPage() {
  const [goal, setGoal] = useState('sales');
  const [budget, setBudget] = useState('1000');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [strategy, setStrategy] = useState<Strategy | null>(null);

  const handleGenerate = async () => {
    setError('');
    const token = getToken();
    if (!token) return;

    setLoading(true);
    try {
      const result = await generateAdStrategy(token, {
        goal,
        monthly_budget: parseFloat(budget) || 1000,
        notes: notes || undefined,
      });
      setStrategy(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AdminLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold">AI Campaign Strategy</h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Input Section */}
        <fieldset className="border border-gray-200 rounded-lg p-4 space-y-4">
          <legend className="text-sm font-semibold text-gray-600 px-1">Strategy Parameters</legend>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Goal</label>
              <select
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                {GOALS.map((g) => (
                  <option key={g.value} value={g.value}>{g.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Monthly Budget ($)</label>
              <input
                type="number" min="0" step="100"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              placeholder="e.g. Focus on first-time buyers, emphasize warranty..."
            />
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2.5 px-4 rounded-md font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Generating Strategy...' : 'Generate Campaign Strategy'}
          </button>
        </fieldset>

        {/* Output Section */}
        {strategy && (
          <div className="space-y-4">
            {strategy.mode === 'stub' && (
              <div className="bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 rounded text-sm">
                Running in Safe Mode (Stub AI) — Connect Claude API key for personalized strategies
              </div>
            )}

            <Collapsible title="Angles" count={strategy.angles.length} defaultOpen>
              <ul className="space-y-2">
                {strategy.angles.map((a, i) => (
                  <li key={i} className="flex items-start justify-between gap-2 text-sm">
                    <span>{a}</span>
                    <CopyButton text={a} />
                  </li>
                ))}
              </ul>
            </Collapsible>

            <Collapsible title="Hooks" count={strategy.hooks.length} defaultOpen>
              <ul className="space-y-2">
                {strategy.hooks.map((h, i) => (
                  <li key={i} className="flex items-start justify-between gap-2 text-sm">
                    <span>&ldquo;{h}&rdquo;</span>
                    <CopyButton text={h} />
                  </li>
                ))}
              </ul>
            </Collapsible>

            <Collapsible title="Offer Suggestions" count={strategy.offers.length}>
              <ul className="space-y-2">
                {strategy.offers.map((o, i) => (
                  <li key={i} className="flex items-start justify-between gap-2 text-sm">
                    <span>{o}</span>
                    <CopyButton text={o} />
                  </li>
                ))}
              </ul>
            </Collapsible>

            <Collapsible title="Targeting" count={strategy.targeting.length}>
              <ul className="space-y-2">
                {strategy.targeting.map((t, i) => (
                  <li key={i} className="flex items-start justify-between gap-2 text-sm">
                    <span>{t}</span>
                    <CopyButton text={t} />
                  </li>
                ))}
              </ul>
            </Collapsible>

            <Collapsible title="Ad Variations" count={strategy.ads.length} defaultOpen>
              <div className="space-y-4">
                {strategy.ads.map((ad, i) => (
                  <div key={i} className="border border-gray-100 rounded-lg p-4 bg-gray-50 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-gray-500 uppercase">Ad {i + 1}</span>
                      <CopyButton text={`${ad.headline}\n\n${ad.primary_text}\n\nCTA: ${ad.cta}`} />
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-0.5">Headline</div>
                      <div className="font-semibold">{ad.headline}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-0.5">Primary Text</div>
                      <div className="text-sm text-gray-700">{ad.primary_text}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500 mb-0.5">CTA</div>
                      <div className="inline-block bg-blue-600 text-white text-sm px-3 py-1 rounded font-medium">
                        {ad.cta}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Collapsible>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
