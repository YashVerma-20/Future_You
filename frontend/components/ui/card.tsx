import React from 'react'
import { cn } from '@/lib/utils'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  variant?: 'default' | 'outlined' | 'elevated'
}

export function Card({ children, variant = 'default', className, ...props }: CardProps) {
  const variants = {
    default: 'bg-white dark:bg-secondary-800 shadow-sm',
    outlined: 'bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-700',
    elevated: 'bg-white dark:bg-secondary-800 shadow-lg',
  }

  return (
    <div
      className={cn(
        'rounded-xl overflow-hidden transition-all duration-200',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-6 py-4 border-b border-secondary-200 dark:border-secondary-700', className)} {...props}>
      {children}
    </div>
  )
}

export function CardTitle({ children, className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn('text-lg font-semibold text-secondary-900 dark:text-secondary-100', className)} {...props}>
      {children}
    </h3>
  )
}

export function CardDescription({ children, className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn('text-sm text-secondary-500 dark:text-secondary-400 mt-1', className)} {...props}>
      {children}
    </p>
  )
}

export function CardContent({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-6 py-4', className)} {...props}>
      {children}
    </div>
  )
}

export function CardFooter({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-6 py-4 border-t border-secondary-200 dark:border-secondary-700', className)} {...props}>
      {children}
    </div>
  )
}
