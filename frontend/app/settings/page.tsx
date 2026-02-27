'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Loading } from '@/components/ui/loading'
import { Navbar } from '@/components/layout/navbar'
import { useAuth } from '@/hooks/useAuth'
import { authApi } from '@/lib/api'
import { MapPin, Briefcase, User, Save, CheckCircle } from 'lucide-react'

interface UserProfile {
  id: string
  email: string
  display_name?: string
  phone?: string
  photo_url?: string
  location?: string
  preferred_work_type?: 'remote' | 'onsite' | 'hybrid'
}

export default function SettingsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  
  // Form state
  const [location, setLocation] = useState('')
  const [preferredWorkType, setPreferredWorkType] = useState<'remote' | 'onsite' | 'hybrid'>('hybrid')
  const [displayName, setDisplayName] = useState('')

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (isAuthenticated) {
      fetchProfile()
    }
  }, [isAuthenticated])

  const fetchProfile = async () => {
    try {
      setIsLoading(true)
      const response = await authApi.getCurrentUser()
      const userData = response.data.data.user
      setProfile(userData)
      
      // Set form values
      setLocation(userData.location || '')
      setPreferredWorkType(userData.preferred_work_type || 'hybrid')
      setDisplayName(userData.display_name || '')
    } catch (error) {
      console.error('Failed to fetch profile:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setIsSaving(true)
      setSaveMessage(null)
      
      await authApi.updateProfile({
        display_name: displayName || undefined,
        location: location || undefined,
        preferred_work_type: preferredWorkType
      })
      
      setSaveMessage('Profile updated successfully!')
      setTimeout(() => setSaveMessage(null), 3000)
    } catch (error) {
      console.error('Failed to update profile:', error)
      setSaveMessage('Failed to update profile. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  if (authLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loading size="lg" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-secondary-50 dark:bg-secondary-900">
      <Navbar />
      
      <main className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900 dark:text-white">
            Settings
          </h1>
          <p className="text-secondary-600 dark:text-secondary-400 mt-2">
            Manage your profile and job preferences
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loading size="lg" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Profile Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="w-5 h-5" />
                  Profile Information
                </CardTitle>
                <CardDescription>
                  Update your personal details
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                    Display Name
                  </label>
                  <Input
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="Your name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                    Email
                  </label>
                  <Input
                    value={profile?.email || ''}
                    disabled
                    className="bg-secondary-100 dark:bg-secondary-800"
                  />
                  <p className="text-xs text-secondary-500 mt-1">
                    Email cannot be changed
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Job Preferences */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="w-5 h-5" />
                  Job Preferences
                </CardTitle>
                <CardDescription>
                  Set your location and work preferences for better job matches
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                    Your City / Location
                  </label>
                  <Input
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g., Bangalore, Mumbai, Delhi"
                  />
                  <p className="text-xs text-secondary-500 mt-1">
                    Jobs will be matched to this location (India only)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                    Preferred Work Type
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['remote', 'hybrid', 'onsite'] as const).map((type) => (
                      <button
                        key={type}
                        onClick={() => setPreferredWorkType(type)}
                        className={`p-3 rounded-lg border text-sm font-medium capitalize transition-colors ${
                          preferredWorkType === type
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                            : 'border-secondary-200 dark:border-secondary-700 text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-800'
                        }`}
                      >
                        <Briefcase className="w-4 h-4 mx-auto mb-1" />
                        {type}
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Save Button */}
            <div className="flex items-center justify-between">
              <div>
                {saveMessage && (
                  <p className={`text-sm flex items-center gap-1 ${
                    saveMessage.includes('Failed') ? 'text-red-500' : 'text-green-600'
                  }`}>
                    {saveMessage.includes('Failed') ? null : <CheckCircle className="w-4 h-4" />}
                    {saveMessage}
                  </p>
                )}
              </div>
              <Button 
                onClick={handleSave} 
                disabled={isSaving}
                className="flex items-center gap-2"
              >
                {isSaving ? (
                  <>
                    <Loading size="sm" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
