/**
 * Field Mapping Display Component
 * Shows auto-detected mappings and allows manual corrections
 */

'use client';

import { useState } from 'react';
import { SyncConfig, useSheetSync } from '@/hooks/useSheetSync';

interface FieldMappingDisplayProps {
  config: SyncConfig;
}

const BITRIX_FIELDS = {
  contacts: [
    { value: 'TITLE', label: 'Contact Name' },
    { value: 'EMAIL', label: 'Email' },
    { value: 'PHONE', label: 'Phone' },
    { value: 'STATUS_ID', label: 'Status' },
    { value: 'SOURCE_ID', label: 'Source' },
    { value: 'COMMENTS', label: 'Comments' },
  ],
  deals: [
    { value: 'TITLE', label: 'Deal Name' },
    { value: 'STAGE_ID', label: 'Stage' },
    { value: 'ASSIGNED_BY_ID', label: 'Assigned To' },
    { value: 'BEGINDATE', label: 'Start Date' },
    { value: 'CLOSEDATE', label: 'Close Date' },
    { value: 'OPPORTUNITY', label: 'Amount' },
  ],
  companies: [
    { value: 'TITLE', label: 'Company Name' },
    { value: 'PHONE', label: 'Phone' },
    { value: 'EMAIL', label: 'Email' },
    { value: 'WEBSITE', label: 'Website' },
    { value: 'INDUSTRY', label: 'Industry' },
    { value: 'COMMENTS', label: 'Comments' },
  ],
  tasks: [
    { value: 'TITLE', label: 'Task Name' },
    { value: 'DESCRIPTION', label: 'Description' },
    { value: 'PRIORITY', label: 'Priority' },
    { value: 'DEADLINE', label: 'Deadline' },
    { value: 'RESPONSIBLE_ID', label: 'Assigned To' },
    { value: 'STATUS', label: 'Status' },
  ],
};

export default function FieldMappingDisplay({ config }: FieldMappingDisplayProps) {
  const { updateFieldMapping, isLoading } = useSheetSync();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<Record<number, { field: string; updatable: boolean }>>({});

  const handleEdit = (mappingId: number, field: string, updatable: boolean) => {
    setEditingId(mappingId);
    setEditValues({
      [mappingId]: { field, updatable },
    });
  };

  const handleSave = async (mappingId: number) => {
    const values = editValues[mappingId];
    if (!values) return;

    const success = await updateFieldMapping(mappingId, values.field, values.updatable);
    if (success) {
      setEditingId(null);
      setEditValues({});
    }
  };

  const availableFields = BITRIX_FIELDS[config.entity_type] || [];
  const dataTypes = ['string', 'number', 'date', 'boolean'];

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-2">Field Mappings</h3>
        <p className="text-sm text-slate-600">
          Map your Google Sheets columns to Bitrix24 fields. Green = auto-detected, Blue = manual mapping
        </p>
      </div>

      {/* Mappings Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                Sheet Column
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                Data Type
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                Bitrix24 Field
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                Updatable
              </th>
              <th className="text-left px-4 py-3 font-semibold text-slate-900 text-sm">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {config.field_mappings.map((mapping) => (
              <tr key={mapping.id} className="hover:bg-slate-50 transition">
                {/* Sheet Column */}
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-900">{mapping.sheet_column_name}</div>
                  <div className="text-xs text-slate-600">
                    Column {mapping.sheet_column_index + 1}
                  </div>
                </td>

                {/* Data Type */}
                <td className="px-4 py-3">
                  <span
                    className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                      mapping.data_type === 'string'
                        ? 'bg-blue-100 text-blue-800'
                        : mapping.data_type === 'number'
                        ? 'bg-purple-100 text-purple-800'
                        : mapping.data_type === 'date'
                        ? 'bg-orange-100 text-orange-800'
                        : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {mapping.data_type}
                  </span>
                </td>

                {/* Bitrix Field */}
                <td className="px-4 py-3">
                  {editingId === mapping.id ? (
                    <select
                      value={editValues[mapping.id]?.field || mapping.bitrix_field}
                      onChange={(e) =>
                        setEditValues({
                          ...editValues,
                          [mapping.id]: {
                            ...editValues[mapping.id],
                            field: e.target.value,
                          },
                        })
                      }
                      className="w-full px-3 py-1 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">-- Select Field --</option>
                      {availableFields.map((field) => (
                        <option key={field.value} value={field.value}>
                          {field.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div>
                      <div className="font-medium text-slate-900">
                        {availableFields.find((f) => f.value === mapping.bitrix_field)?.label ||
                          mapping.bitrix_field ||
                          '—'}
                      </div>
                      <div className="text-xs text-slate-600">{mapping.bitrix_field}</div>
                    </div>
                  )}
                </td>

                {/* Updatable */}
                <td className="px-4 py-3">
                  {editingId === mapping.id ? (
                    <input
                      type="checkbox"
                      checked={editValues[mapping.id]?.updatable ?? mapping.is_updatable}
                      onChange={(e) =>
                        setEditValues({
                          ...editValues,
                          [mapping.id]: {
                            ...editValues[mapping.id],
                            updatable: e.target.checked,
                          },
                        })
                      }
                      className="w-4 h-4 rounded border-slate-300"
                    />
                  ) : (
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                        mapping.is_updatable
                          ? 'bg-green-100 text-green-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      {mapping.is_updatable ? '✓ Yes' : '✗ No'}
                    </span>
                  )}
                </td>

                {/* Actions */}
                <td className="px-4 py-3">
                  {editingId === mapping.id ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSave(mapping.id)}
                        disabled={isLoading}
                        className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-slate-400 text-white text-sm rounded-lg font-medium transition"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => {
                          setEditingId(null);
                          setEditValues({});
                        }}
                        className="px-3 py-1 bg-slate-200 hover:bg-slate-300 text-slate-900 text-sm rounded-lg font-medium transition"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() =>
                        handleEdit(mapping.id, mapping.bitrix_field, mapping.is_updatable)
                      }
                      className="px-3 py-1 bg-blue-100 hover:bg-blue-200 text-blue-800 text-sm rounded-lg font-medium transition"
                    >
                      Edit
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Empty State */}
      {config.field_mappings.length === 0 && (
        <div className="text-center py-12">
          <svg
            className="w-12 h-12 text-slate-300 mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-slate-600 font-medium">No field mappings found</p>
          <p className="text-sm text-slate-600 mt-1">
            Check that your sheet has headers in the first row
          </p>
        </div>
      )}

      {/* Info Box */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h4 className="font-semibold text-blue-900 mb-2 text-sm">💡 Tips</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>✓ Green badges show auto-detected fields</li>
          <li>✓ Click "Edit" to correct any mappings</li>
          <li>✓ Only fields marked as "Updatable" will sync changes to Bitrix24</li>
          <li>✓ Disable updates for read-only fields (like ID numbers)</li>
        </ul>
      </div>
    </div>
  );
}
