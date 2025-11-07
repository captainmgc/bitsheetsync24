/**
 * OAuth Callback Page
 * Handles Google OAuth callback after user login
 * 
 * URL: /sheet-sync/oauth/callback?code=xxx&state=yyy
 */

'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useSheetSync } from '@/hooks/useSheetSync';
import { useSession } from 'next-auth/react';

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { completeOAuth, isAuthenticating, error: sheetError } = useSheetSync();
  const { status: authStatus } = useSession();
  
  const [isProcessing, setIsProcessing] = useState(true);
  const [message, setMessage] = useState('Processing OAuth callback...');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get authorization code and state
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const authError = searchParams.get('error');

        // Check for errors from Google
        if (authError) {
          const errorDescription = searchParams.get('error_description');
          throw new Error(`OAuth error: ${authError} - ${errorDescription || 'Unknown error'}`);
        }

        if (!code) {
          throw new Error('No authorization code received from Google');
        }

        if (!state) {
          throw new Error('No state parameter received');
        }

        setMessage('Exchanging authorization code for tokens...');

        // Complete OAuth flow
        const success = await completeOAuth(code, state);

        if (success) {
          setMessage('✅ Successfully connected Google Sheets!');
          
          // Redirect back to sheet-sync page
          setTimeout(() => {
            router.push('/sheet-sync');
          }, 1500);
        } else {
          throw new Error(sheetError || 'OAuth completion failed');
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(errorMsg);
        setMessage('❌ OAuth callback failed');
        console.error('OAuth callback error:', err);
      } finally {
        setIsProcessing(false);
      }
    };

    // Only proceed if user is authenticated with NextAuth
    if (authStatus === 'authenticated') {
      handleCallback();
    } else if (authStatus === 'loading') {
      setMessage('Authenticating with server...');
    } else if (authStatus === 'unauthenticated') {
      setError('You must be logged in to connect Google Sheets');
      setIsProcessing(false);
    }
  }, [searchParams, completeOAuth, sheetError, authStatus, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          {isProcessing ? (
            <>
              {/* Loading Animation */}
              <div className="mb-6 flex justify-center">
                <div className="inline-block">
                  <div className="w-16 h-16 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
                </div>
              </div>

              <h1 className="text-2xl font-bold text-slate-900 mb-4">
                Connecting Google Sheets
              </h1>
              <p className="text-slate-600 mb-2">{message}</p>
              <p className="text-sm text-slate-500">This usually takes just a few seconds...</p>
            </>
          ) : error ? (
            <>
              {/* Error State */}
              <div className="mb-6 flex justify-center">
                <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-red-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </div>
              </div>

              <h1 className="text-2xl font-bold text-red-900 mb-4">Connection Failed</h1>
              <p className="text-red-700 mb-4">{error}</p>
              
              <div className="space-y-3">
                <button
                  onClick={() => window.history.back()}
                  className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition"
                >
                  ← Go Back
                </button>
                <button
                  onClick={() => router.push('/sheet-sync')}
                  className="w-full px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-900 rounded-lg font-medium transition"
                >
                  Start Over
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Success State */}
              <div className="mb-6 flex justify-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
              </div>

              <h1 className="text-2xl font-bold text-green-900 mb-2">{message}</h1>
              <p className="text-slate-600 mb-6">Redirecting to sheet configuration...</p>

              {/* Loading indicator */}
              <div className="flex justify-center gap-1">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
              </div>
            </>
          )}
        </div>

        {/* Debug Info (development only) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-4 p-4 bg-slate-900 text-slate-100 rounded-lg text-xs font-mono">
            <p className="text-slate-400 mb-2">Debug Info:</p>
            <p>Auth Status: {authStatus}</p>
            <p>Processing: {isProcessing ? 'true' : 'false'}</p>
            <p>Authenticating: {isAuthenticating ? 'true' : 'false'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
          <div className="w-full max-w-md">
            <div className="bg-white rounded-lg shadow-lg p-8 text-center">
              <div className="mb-6 flex justify-center">
                <div className="inline-block">
                  <div className="w-16 h-16 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
                </div>
              </div>
              <h1 className="text-2xl font-bold text-slate-900 mb-4">
                Connecting Google Sheets
              </h1>
              <p className="text-slate-600">Loading...</p>
            </div>
          </div>
        </div>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  );
}
