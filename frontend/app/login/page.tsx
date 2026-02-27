'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/hooks/useAuth'
import { loginWithEmail } from '@/lib/firebase'
import { validateEmail } from '@/lib/utils'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuth()

  // Redirect if already authenticated (after auth check completes)
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace('/dashboard')
    }
  }, [isAuthenticated, isLoading, router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!validateEmail(email)) {
      setError('Please enter a valid email address')
      return
    }

    if (!password) {
      setError('Please enter your password')
      return
    }

    setIsSubmitting(true)

    try {
      // 🔥 Only Firebase login here
      await loginWithEmail(email, password)

      // DO NOT call backend here
      // DO NOT router.push here
      // AuthProvider will handle everything
    } catch (err: any) {
      console.error('Login error:', err)
      // Firebase specific error messages
      if (err.code === 'auth/user-not-found') {
        setError('No account found with this email. Please sign up first.')
      } else if (err.code === 'auth/wrong-password') {
        setError('Incorrect password. Please try again.')
      } else if (err.code === 'auth/invalid-credential') {
        setError('Invalid email or password. Please check your credentials.')
      } else if (err.code === 'auth/too-many-requests') {
        setError('Too many failed attempts. Please try again later.')
      } else {
        setError(err.message || 'Failed to sign in. Please check your credentials.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50 dark:bg-secondary-900 px-4">
      <Card className="w-full max-w-md animate-fade-in">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Welcome Back</CardTitle>
          <CardDescription>
            Sign in to your Future You account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            <Input
              label="Password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            {error && (
              <p className="text-sm text-red-600 dark:text-red-400 animate-fade-in">
                {error}
              </p>
            )}

            <Button
              type="submit"
              className="w-full"
              isLoading={isSubmitting}
            >
              Sign In
            </Button>
          </form>

          <div className="mt-6 text-center text-sm">
            <span className="text-secondary-600 dark:text-secondary-400">
              Don&apos;t have an account?{' '}
            </span>
            <Link
              href="/signup"
              className="text-primary-600 hover:text-primary-500 dark:text-primary-400 font-medium"
            >
              Sign up
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
