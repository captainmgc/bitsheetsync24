'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useSession, signOut } from 'next-auth/react'
import { 
  LayoutDashboard, 
  Database, 
  Upload, 
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Server,
  Eye,
  Zap
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface NavItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: number
}

const navigationItems: NavItem[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Veri Görüntüleme',
    href: '/data',
    icon: Database,
  },
  {
    name: 'Veri Aktarımı',
    href: '/export',
    icon: Upload,
  },
  {
    name: 'View Yönetimi',
    href: '/views',
    icon: Eye,
  },
  {
    name: 'Sheet Sync',
    href: '/sheet-sync',
    icon: Zap,
  },
]

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()
  const { data: session } = useSession()

  return (
    <div
      className={cn(
        'fixed left-0 top-0 h-screen bg-gradient-to-b from-slate-900 to-slate-800 text-white transition-all duration-300 ease-in-out z-50 border-r border-slate-700',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <Server className="w-8 h-8 text-blue-500" />
            <div>
              <h1 className="text-sm font-bold">BitSheet24</h1>
              <p className="text-xs text-slate-400">Sync System</p>
            </div>
          </div>
        )}
        {collapsed && (
          <Server className="w-8 h-8 text-blue-500 mx-auto" />
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors ml-auto"
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-2 space-y-1 mt-4">
        {navigationItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                'hover:bg-slate-700/50',
                isActive && 'bg-gradient-to-r from-blue-600 to-green-600 shadow-lg',
                collapsed && 'justify-center'
              )}
              title={collapsed ? item.name : undefined}
            >
              <Icon className={cn('w-5 h-5', isActive && 'text-white')} />
              {!collapsed && (
                <div className="flex-1 flex items-center justify-between">
                  <span className={cn(
                    'text-sm font-medium',
                    isActive ? 'text-white' : 'text-slate-300'
                  )}>
                    {item.name}
                  </span>
                  {item.badge !== undefined && (
                    <span className="bg-blue-500 text-white text-xs px-2 py-0.5 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="absolute bottom-0 left-0 right-0 p-2 border-t border-slate-700">
        {/* User Info */}
        {session?.user && !collapsed && (
          <div className="px-3 py-2 mb-2">
            <div className="flex items-center gap-2">
              {session.user.image ? (
                <img 
                  src={session.user.image} 
                  alt={session.user.name || 'User'} 
                  className="w-8 h-8 rounded-full"
                />
              ) : (
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">
                    {session.user.name?.charAt(0) || 'U'}
                  </span>
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-white truncate">
                  {session.user.name}
                </div>
                <div className="text-xs text-slate-400 truncate">
                  {session.user.email}
                </div>
              </div>
            </div>
          </div>
        )}
        
        <Link
          href="/settings"
          className={cn(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors hover:bg-slate-700/50',
            collapsed && 'justify-center'
          )}
          title={collapsed ? 'Ayarlar' : undefined}
        >
          <Settings className="w-5 h-5 text-slate-400" />
          {!collapsed && (
            <span className="text-sm text-slate-300">Ayarlar</span>
          )}
        </Link>
        
        <button
          onClick={() => signOut({ callbackUrl: '/auth/signin' })}
          className={cn(
            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors hover:bg-red-500/10 hover:text-red-400 text-slate-400 mt-1',
            collapsed && 'justify-center'
          )}
          title={collapsed ? 'Çıkış' : undefined}
        >
          <LogOut className="w-5 h-5" />
          {!collapsed && (
            <span className="text-sm">Çıkış Yap</span>
          )}
        </button>
      </div>
    </div>
  )
}
