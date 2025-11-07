/**
 * Google Sheet Connect Component
 * Handles OAuth connection flow
 */

'use client';

import { useState } from 'react';
import { useSheetSync } from '@/hooks/useSheetSync';

export default function GoogleSheetConnect() {
  const { startOAuth, isLoading, error } = useSheetSync();
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnect = async () => {
    setIsConnecting(true);
    await startOAuth();
    setIsConnecting(false);
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8 text-center border border-slate-200">
        {/* Google Sheets Icon */}
        <div className="mb-6 flex justify-center">
          <div className="w-20 h-20 bg-gradient-to-br from-green-50 to-blue-50 rounded-lg flex items-center justify-center">
            <svg
              className="w-10 h-10"
              viewBox="0 0 48 48"
              fill="none"
            >
              <rect width="48" height="48" fill="#34A853" rx="6" />
              <path
                d="M24 10v28M10 24h28"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </div>
        </div>

        <h2 className="text-2xl font-bold text-slate-900 mb-2">
          Connect Google Sheets
        </h2>
        <p className="text-slate-600 mb-6">
          Authorize access to your Google Sheets to start syncing with Bitrix24
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Connect Button */}
        <button
          onClick={handleConnect}
          disabled={isLoading || isConnecting}
          className="w-full mb-4 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white rounded-lg font-semibold transition flex items-center justify-center gap-2"
        >
          {isConnecting ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Connecting...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                />
              </svg>
              Connect with Google
            </>
          )}
        </button>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-left">
          <h3 className="font-semibold text-blue-900 mb-2 text-sm">
            What permissions are needed?
          </h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>✓ Read access to your Google Sheets</li>
            <li>✓ Monitor sheet changes in real-time</li>
            <li>✓ Create webhooks for sync notifications</li>
          </ul>
        </div>

        {/* Privacy Notice */}
        <p className="text-xs text-slate-500 mt-6">
          Your data is secure. We only access sheets you authorize.
          <br />
          <a href="#" className="text-blue-600 hover:underline">
            Privacy Policy
          </a>
        </p>
      </div>
    </div>
  );
}
