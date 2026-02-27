import React from 'react'
import { cn } from '@/lib/utils'

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  text?: string
}

export function Loading({ size = 'md', className, text }: LoadingProps) {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  }

  return (
    <div className={cn('flex flex-col items-center justify-center', className)}>
      <div
        className={cn(
          'animate-spin rounded-full border-b-2 border-primary-600',
          sizes[size]
        )}
      />
      {text && (
        <p className="mt-2 text-sm text-secondary-600 dark:text-secondary-400">
          {text}
        </p>
      )}
    </div>
  )
}

export function LoadingOverlay({ text }: { text?: string }) {
  return (
    <div className="fixed inset-0 bg-white/80 dark:bg-secondary-900/80 backdrop-blur-sm flex items-center justify-center z-50">
      <Loading size="lg" text={text} />
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse bg-secondary-200 dark:bg-secondary-700 rounded',
        className
      )}
    />
  )
}
