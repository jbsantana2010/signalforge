'use client';

import { useState, useEffect, useCallback } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';
import { getToken } from '@/lib/auth';
import { fetchLeads } from '@/lib/api';
import { LeadListItem, LeadsResponse } from '@/types/admin';

export default function LeadsListPage() {
  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [search, setSearch] = useState('');
  const [languageFilter, setLanguageFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadLeads = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    setLoading(true);
    try {
      const data: LeadsResponse = await fetchLeads(token, {
        page,
        per_page: perPage,
        language: languageFilter || undefined,
        search: search || undefined,
      });
      setLeads(data.leads);
      setTotal(data.total);
    } catch {
      setError('Failed to load leads');
    } finally {
      setLoading(false);
    }
  }, [page, perPage, search, languageFilter]);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  const totalPages = Math.ceil(total / perPage);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <AdminLayout>
      <div>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
            <p className="text-gray-500 text-sm mt-1">{total} total leads</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Search by name or phone..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <select
              value={languageFilter}
              onChange={(e) => {
                setLanguageFilter(e.target.value);
                setPage(1);
              }}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Languages</option>
              <option value="en">English</option>
              <option value="es">Spanish</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 mb-6">
            {error}
          </div>
        )}

        {/* Table */}
        <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Phone
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Service
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Language
                  </th>
                  <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      Loading...
                    </td>
                  </tr>
                ) : leads.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      No leads found
                    </td>
                  </tr>
                ) : (
                  leads.map((lead) => (
                    <tr key={lead.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {formatDate(lead.created_at)}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {lead.name || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">
                        {lead.phone || '-'}
                      </td>
                      <td className="px-6 py-4">
                        <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                          {lead.service || '-'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700 uppercase">
                        {lead.language}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">
                        {lead.score !== null ? lead.score : '-'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <a
                          href={`/admin/leads/${lead.id}`}
                          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                        >
                          View
                        </a>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-3 border-t bg-gray-50">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-gray-700">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
