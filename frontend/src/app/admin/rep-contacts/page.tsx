'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AdminLayout from '@/components/admin/AdminLayout';
import { getToken, isAuthenticated } from '@/lib/auth';
import { fetchRepContacts, upsertRepContact, updateRepContact } from '@/lib/api';
import type { RepContact } from '@/types/admin';

export default function RepContactsPage() {
  const router = useRouter();
  const [contacts, setContacts] = useState<RepContact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Form state
  const [formEmail, setFormEmail] = useState('');
  const [formPhone, setFormPhone] = useState('');
  const [formName, setFormName] = useState('');
  const [formActive, setFormActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState('');

  // Inline edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editPhone, setEditPhone] = useState('');
  const [editName, setEditName] = useState('');
  const [editActive, setEditActive] = useState(true);
  const [editSaving, setEditSaving] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/admin/login');
      return;
    }
    load();
  }, [router]);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const token = getToken()!;
      const data = await fetchRepContacts(token);
      setContacts(data.contacts);
    } catch {
      setError('Failed to load rep contacts.');
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError('');
    setSaveSuccess('');
    try {
      const token = getToken()!;
      await upsertRepContact(token, {
        email: formEmail.trim(),
        phone: formPhone.trim() || null,
        full_name: formName.trim() || null,
        is_active: formActive,
      });
      setSaveSuccess(`Saved: ${formEmail.trim()}`);
      setFormEmail('');
      setFormPhone('');
      setFormName('');
      setFormActive(true);
      await load();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  function startEdit(c: RepContact) {
    setEditingId(c.id);
    setEditPhone(c.phone ?? '');
    setEditName(c.full_name ?? '');
    setEditActive(c.is_active);
  }

  async function handleSaveEdit(c: RepContact) {
    setEditSaving(true);
    try {
      const token = getToken()!;
      await updateRepContact(token, c.id, {
        phone: editPhone.trim() || null,
        full_name: editName.trim() || null,
        is_active: editActive,
      });
      setEditingId(null);
      await load();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setEditSaving(false);
    }
  }

  return (
    <AdminLayout>
      <div className="max-w-3xl">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Rep Contacts</h1>
        <p className="text-sm text-gray-500 mb-6">
          Rep contacts provide phone numbers for SMS handoff notifications. The email must match a
          lead&apos;s <code className="bg-gray-100 px-1 rounded">owner_email</code>.
        </p>

        {/* Add / Upsert form */}
        <div className="bg-white border border-gray-200 rounded-lg p-5 mb-8">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Add or update rep</h2>
          <form onSubmit={handleAdd} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                  placeholder="rep@example.com"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Phone (E.164)</label>
                <input
                  type="tel"
                  value={formPhone}
                  onChange={(e) => setFormPhone(e.target.value)}
                  placeholder="+17875550100"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 items-end">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Full name</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Jane Smith"
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-center space-x-2 pb-0.5">
                <input
                  id="formActive"
                  type="checkbox"
                  checked={formActive}
                  onChange={(e) => setFormActive(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <label htmlFor="formActive" className="text-sm text-gray-700">Active</label>
              </div>
            </div>
            {saveError && <p className="text-sm text-red-600">{saveError}</p>}
            {saveSuccess && <p className="text-sm text-green-600">{saveSuccess}</p>}
            <button
              type="submit"
              disabled={saving}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save rep'}
            </button>
          </form>
        </div>

        {/* Contact list */}
        <h2 className="text-base font-semibold text-gray-800 mb-3">Current reps</h2>

        {loading && <p className="text-sm text-gray-500">Loading...</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && contacts.length === 0 && (
          <p className="text-sm text-gray-500">No rep contacts yet.</p>
        )}

        <div className="space-y-3">
          {contacts.map((c) => (
            <div key={c.id} className="bg-white border border-gray-200 rounded-lg p-4">
              {editingId === c.id ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
                      <input
                        type="tel"
                        value={editPhone}
                        onChange={(e) => setEditPhone(e.target.value)}
                        placeholder="+17875550100"
                        className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Full name</label>
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <label className="flex items-center space-x-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={editActive}
                        onChange={(e) => setEditActive(e.target.checked)}
                        className="rounded border-gray-300"
                      />
                      <span>Active</span>
                    </label>
                    <button
                      onClick={() => handleSaveEdit(c)}
                      disabled={editSaving}
                      className="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                    >
                      {editSaving ? 'Saving...' : 'Save'}
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="text-gray-500 text-sm hover:text-gray-700"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium text-gray-900">
                        {c.full_name ?? c.email}
                      </span>
                      {!c.is_active && (
                        <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                          inactive
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5 space-x-3">
                      <span>{c.email}</span>
                      {c.phone ? (
                        <span className="text-green-700 font-mono">{c.phone}</span>
                      ) : (
                        <span className="text-amber-600">no phone — SMS will be skipped</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => startEdit(c)}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Edit
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </AdminLayout>
  );
}
