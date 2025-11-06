'use client'

import { useSession } from 'next-auth/react'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import {
  Settings as SettingsIcon,
  User,
  Bell,
  Shield,
  Globe
} from 'lucide-react'

export default function SettingsPage() {
  const { data: session } = useSession()

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="bg-gradient-to-r from-slate-600 to-slate-800 rounded-xl p-6 text-white shadow-lg">
            <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
              <SettingsIcon className="w-8 h-8" />
              Ayarlar
            </h1>
            <p className="text-slate-100">
              Uygulama ayarlarını ve tercihlerinizi yönetin
            </p>
          </div>

          {/* Settings Sections */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* User Profile */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex items-center gap-3 mb-4">
                <User className="w-6 h-6 text-blue-600" />
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Kullanıcı Profili
                </h2>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    İsim
                  </label>
                  <p className="text-slate-900 dark:text-white">{session?.user?.name || 'Belirtilmemiş'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    E-posta
                  </label>
                  <p className="text-slate-900 dark:text-white">{session?.user?.email || 'Belirtilmemiş'}</p>
                </div>
              </div>
            </div>

            {/* Notifications */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex items-center gap-3 mb-4">
                <Bell className="w-6 h-6 text-purple-600" />
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Bildirimler
                </h2>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-700 dark:text-slate-300">Export bildirimleri</span>
                  <input type="checkbox" className="w-4 h-4 text-purple-600 rounded" defaultChecked />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-700 dark:text-slate-300">Senkronizasyon bildirimleri</span>
                  <input type="checkbox" className="w-4 h-4 text-purple-600 rounded" defaultChecked />
                </div>
              </div>
            </div>

            {/* Security */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex items-center gap-3 mb-4">
                <Shield className="w-6 h-6 text-green-600" />
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Güvenlik
                </h2>
              </div>
              <div className="space-y-3">
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Google OAuth ile güvenli giriş yapıyorsunuz.
                </p>
                <button className="text-sm text-blue-600 hover:text-blue-700">
                  Oturum bilgilerini yenile
                </button>
              </div>
            </div>

            {/* Language */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
              <div className="flex items-center gap-3 mb-4">
                <Globe className="w-6 h-6 text-orange-600" />
                <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                  Dil ve Bölge
                </h2>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-2">
                    Dil
                  </label>
                  <select className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white">
                    <option value="tr">Türkçe</option>
                    <option value="en">English</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
