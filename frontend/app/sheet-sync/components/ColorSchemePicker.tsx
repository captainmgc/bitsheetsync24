/**
 * Color Scheme Picker Component
 * Allows customization of table colors with Poppins font
 */

'use client';

import { useState } from 'react';
import { SyncConfig } from '@/hooks/useSheetSync';

interface ColorSchemePickerProps {
  config: SyncConfig;
}

const PRESET_SCHEMES = [
  {
    name: 'Default',
    colors: { primary: '#1f2937', secondary: '#374151', accent: '#3b82f6' },
  },
  {
    name: 'Ocean',
    colors: { primary: '#0369a1', secondary: '#06b6d4', accent: '#0ea5e9' },
  },
  {
    name: 'Forest',
    colors: { primary: '#065f46', secondary: '#059669', accent: '#10b981' },
  },
  {
    name: 'Sunset',
    colors: { primary: '#92400e', secondary: '#ea580c', accent: '#f97316' },
  },
  {
    name: 'Purple',
    colors: { primary: '#581c87', secondary: '#a21caf', accent: '#d946ef' },
  },
  {
    name: 'Pink',
    colors: { primary: '#831843', secondary: '#be185d', accent: '#ec4899' },
  },
];

export default function ColorSchemePicker({ config }: ColorSchemePickerProps) {
  const [selectedScheme, setSelectedScheme] = useState(0);
  const [customColors, setCustomColors] = useState(config.color_scheme || {});
  const [useCustom, setUseCustom] = useState(false);

  const currentColors = useCustom ? customColors : PRESET_SCHEMES[selectedScheme].colors;

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-2">Color Scheme</h3>
        <p className="text-sm text-slate-600">
          Customize the appearance of your synced data in Google Sheets
        </p>
      </div>

      {/* Font Settings */}
      <div className="mb-8 p-4 bg-slate-50 border border-slate-200 rounded-lg">
        <h4 className="font-semibold text-slate-900 mb-3 text-sm">Typography</h4>
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-900 mb-1">
                Font Family
              </label>
              <select
                disabled
                defaultValue="poppins"
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-600 cursor-not-allowed"
              >
                <option value="poppins">Poppins (Default)</option>
              </select>
              <p className="text-xs text-slate-600 mt-1">
                ✓ Poppins font is applied to all synced tables
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Preset Schemes */}
      <div className="mb-8">
        <h4 className="font-semibold text-slate-900 mb-3 text-sm">Preset Schemes</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {PRESET_SCHEMES.map((scheme, idx) => (
            <button
              key={idx}
              onClick={() => {
                setSelectedScheme(idx);
                setUseCustom(false);
              }}
              className={`p-4 rounded-lg border-2 transition ${
                !useCustom && selectedScheme === idx
                  ? 'border-blue-600 bg-blue-50'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex gap-2 mb-2">
                <div
                  className="w-8 h-8 rounded-lg shadow-sm"
                  style={{ backgroundColor: scheme.colors.primary }}
                />
                <div
                  className="w-8 h-8 rounded-lg shadow-sm"
                  style={{ backgroundColor: scheme.colors.secondary }}
                />
                <div
                  className="w-8 h-8 rounded-lg shadow-sm"
                  style={{ backgroundColor: scheme.colors.accent }}
                />
              </div>
              <p className="text-sm font-medium text-slate-900">{scheme.name}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Colors */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <input
            type="checkbox"
            id="useCustom"
            checked={useCustom}
            onChange={(e) => setUseCustom(e.target.checked)}
            className="w-4 h-4 rounded border-slate-300"
          />
          <label htmlFor="useCustom" className="font-semibold text-slate-900 text-sm cursor-pointer">
            Use Custom Colors
          </label>
        </div>

        {useCustom && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {['primary', 'secondary', 'accent'].map((colorType) => (
              <div key={colorType}>
                <label className="block text-sm font-medium text-slate-900 mb-2 capitalize">
                  {colorType} Color
                </label>
                <div className="flex gap-3">
                  <input
                    type="color"
                    value={customColors[colorType as keyof typeof customColors] || '#000000'}
                    onChange={(e) =>
                      setCustomColors({
                        ...customColors,
                        [colorType]: e.target.value,
                      })
                    }
                    className="w-12 h-12 rounded-lg border border-slate-300 cursor-pointer"
                  />
                  <div>
                    <input
                      type="text"
                      value={customColors[colorType as keyof typeof customColors] || '#000000'}
                      onChange={(e) =>
                        setCustomColors({
                          ...customColors,
                          [colorType]: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="#000000"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Live Preview */}
      <div className="p-6 bg-slate-50 border border-slate-200 rounded-lg">
        <h4 className="font-semibold text-slate-900 mb-4 text-sm">Preview</h4>

        <div className="bg-white rounded-lg overflow-hidden shadow">
          {/* Table Header */}
          <div
            className="px-6 py-4 text-white font-semibold text-sm transition"
            style={{ backgroundColor: currentColors.primary || '#000' }}
          >
            <div className="flex items-center gap-4">
              <div className="flex-1">Contact Name</div>
              <div className="flex-1">Email</div>
              <div className="flex-1">Status</div>
            </div>
          </div>

          {/* Table Rows */}
          <div className="divide-y divide-slate-200">
            {[1, 2].map((row) => (
              <div key={row} className="px-6 py-3 flex items-center gap-4 hover:bg-slate-50 transition">
                <div className="flex-1 text-sm text-slate-900">John Doe</div>
                <div className="flex-1 text-sm text-slate-600">john@example.com</div>
                <div className="flex-1">
                  <span
                    className="inline-block px-3 py-1 rounded-full text-xs font-medium text-white"
                    style={{ backgroundColor: currentColors.accent || '#000' }}
                  >
                    Active
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Secondary Element */}
          <div
            className="px-6 py-3 text-white text-xs font-medium transition"
            style={{ backgroundColor: currentColors.secondary || '#000' }}
          >
            <div className="flex gap-4">
              <button className="px-3 py-1 bg-white bg-opacity-20 hover:bg-opacity-30 rounded transition">
                ↻ Refresh
              </button>
              <button className="px-3 py-1 bg-white bg-opacity-20 hover:bg-opacity-30 rounded transition">
                ⚙ Settings
              </button>
            </div>
          </div>
        </div>

        <p className="text-xs text-slate-600 mt-4">
          Font: Poppins | This preview shows how your synced data will appear
        </p>
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h4 className="font-semibold text-blue-900 mb-2 text-sm">💡 Color Tips</h4>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>✓ Primary: Header background and main elements</li>
          <li>✓ Secondary: Footer and secondary actions</li>
          <li>✓ Accent: Status badges and highlights</li>
          <li>✓ All text automatically uses Poppins font for consistency</li>
        </ul>
      </div>

      {/* Save Button */}
      <div className="mt-6 flex gap-3">
        <button className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition">
          Save Color Scheme
        </button>
        <button className="flex-1 px-6 py-3 bg-slate-200 hover:bg-slate-300 text-slate-900 rounded-lg font-semibold transition">
          Reset to Default
        </button>
      </div>
    </div>
  );
}
