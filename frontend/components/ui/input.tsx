import React, { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, leftIcon, rightIcon, className, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-secondary-400">
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            className={cn(
              'block w-full rounded-lg border-0 py-2.5 text-secondary-900 dark:text-secondary-100 shadow-sm ring-1 ring-inset placeholder:text-secondary-400 focus:ring-2 focus:ring-inset sm:text-sm sm:leading-6 transition-all duration-200',
              error
                ? 'ring-red-300 focus:ring-red-500 dark:ring-red-700 dark:focus:ring-red-500'
                : 'ring-secondary-300 focus:ring-primary-600 dark:ring-secondary-700 dark:focus:ring-primary-500',
              leftIcon && 'pl-10',
              rightIcon && 'pr-10',
              'bg-white dark:bg-secondary-800',
              className
            )}
            {...props}
          />
          {rightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-secondary-400">
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400 animate-fade-in">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p className="mt-1 text-sm text-secondary-500 dark:text-secondary-400">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
