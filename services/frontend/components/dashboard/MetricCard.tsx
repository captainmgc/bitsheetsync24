'use client'

import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'

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
    <Card className="hover:shadow-md transition-all duration-200 hover:-translate-y-1">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
              {title}
            </p>
            {loading ? (
              <div className="h-8 w-24 bg-slate-200 dark:bg-slate-700 animate-pulse rounded" />
            ) : (
              <h3 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
                {typeof value === 'number' ? value.toLocaleString('tr-TR') : value}
              </h3>
            )}
            
            {change && !loading && (
              <div className="flex items-center gap-1 mt-2">
                <span
                  className={cn(
                    'text-xs font-bold px-1.5 py-0.5 rounded',
                    change.trend === 'up'
                      ? 'text-green-700 bg-green-100 dark:text-green-300 dark:bg-green-900/30'
                      : 'text-red-700 bg-red-100 dark:text-red-300 dark:bg-red-900/30'
                  )}
                >
                  {change.trend === 'up' ? '↑' : '↓'} {Math.abs(change.value)}%
                </span>
                <span className="text-xs text-slate-400 dark:text-slate-500 ml-1">
                  geçen aya göre
                </span>
              </div>
            )}
          </div>

          <div className={cn('p-3 rounded-xl shadow-sm', gradient)}>
            <Icon className="w-6 h-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
