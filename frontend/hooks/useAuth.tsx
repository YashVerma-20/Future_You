'use client'

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from 'react'

import { useRouter } from 'next/navigation'
import { onAuthStateChanged } from 'firebase/auth'

import { auth, logoutUser } from '@/lib/firebase'
import { authApi } from '@/lib/api'

import type { User, AuthContextType } from '@/types'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const router = useRouter()

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setUser(null)
        setIsLoading(false)
        return
      }

      try {
        const idToken = await firebaseUser.getIdToken()

        // Always verify with backend to restore user properly
        const response = await authApi.firebaseAuth(idToken)

        const { access_token, refresh_token, user: userData } =
          response.data.data

        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)

        setUser(userData)
      } catch (error) {
        console.error('Backend auth error:', error)
        await logoutUser()
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    })

    return () => unsubscribe()
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutUser()
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setUser(null)
      router.replace('/login')
    } catch (error) {
      console.error('Logout error:', error)
      throw error
    }
  }, [router])

  const login = useCallback(async (idToken: string) => {
    try {
      const response = await authApi.firebaseAuth(idToken)
      const { access_token, refresh_token, user: userData } =
        response.data.data

      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      setUser(userData)
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  }, [])

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    logout,
    refreshToken: async () => {},
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}