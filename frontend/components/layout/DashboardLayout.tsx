'use client'

import { ReactNode } from 'react'
import { useSession } from 'next-auth/react'
import Sidebar from '@/components/layout/Sidebar'

interface DashboardLayoutProps {
  children: ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const { data: session } = useSession()

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <Sidebar />
      
      {/* Main Content Area */}
      <div className="pl-64 transition-all duration-300">
        {/* Top Bar */}
        <header className="sticky top-0 z-40 bg-white/80 dark:bg-slate-900/80 backdrop-blur-lg border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between px-6 py-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Dashboard
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Bitrix24 verilerinizi yönetin ve izleyin
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              {/* User Menu */}
              {session?.user && (
                <div className="flex items-center gap-3 px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg">
                  {session.user.image ? (
                    <img 
                      src={session.user.image} 
                      alt={session.user.name || 'User'} 
                      className="w-8 h-8 rounded-full"
                    />
                  ) : (
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-green-500 rounded-full flex items-center justify-center">
                      <span className="text-white text-xs font-bold">
                        {session.user.name?.charAt(0) || session.user.email?.charAt(0) || 'U'}
                      </span>
                    </div>
                  )}
                  <div className="text-sm">
                    <div className="font-medium text-slate-900 dark:text-white">
                      {session.user.name || 'Kullanıcı'}
                    </div>
                    <div className="text-xs text-slate-600 dark:text-slate-400">
                      {session.user.email}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
