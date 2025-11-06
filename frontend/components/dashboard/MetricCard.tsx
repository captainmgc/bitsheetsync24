'use client'

import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string | number
  change?: {
    value: number
    trend: 'up' | 'down'
  }
  icon: LucideIcon
  gradient: string
  loading?: boolean
}

export default function MetricCard({
  title,
  value,
  change,
  icon: Icon,
  gradient,
  loading = false
}: MetricCardProps) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
            {title}
          </p>
          {loading ? (
            <div className="h-8 w-24 bg-slate-200 dark:bg-slate-700 animate-pulse rounded" />
          ) : (
            <h3 className="text-3xl font-bold text-slate-900 dark:text-white">
              {typeof value === 'number' ? value.toLocaleString('tr-TR') : value}
            </h3>
          )}
          
          {change && !loading && (
            <div className="flex items-center gap-1 mt-2">
              <span
                className={cn(
                  'text-xs font-medium',
                  change.trend === 'up'
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-red-600 dark:text-red-400'
                )}
              >
                {change.trend === 'up' ? '↑' : '↓'} {Math.abs(change.value)}%
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                son 24 saat
              </span>
            </div>
          )}
        </div>

        <div className={cn('p-3 rounded-lg', gradient)}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  )
}
