'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Loading } from '@/components/ui/loading'
import { Navbar } from '@/components/layout/navbar'
import { useAuth } from '@/hooks/useAuth'
import { jobsApi } from '@/lib/api'

interface Job {
  id: string
  title: string
  company: { name: string } | null
  location: string
  is_remote: boolean
  employment_type: string
  salary_range: { min: number; max: number; currency: string } | null
  required_skills: string[]
}

export default function JobsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [jobs, setJobs] = useState<Job[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState({
    location: '',
    employment_type: '',
    is_remote: false,
  })

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (isAuthenticated) {
      fetchJobs()
    }
  }, [isAuthenticated])

  const fetchJobs = async () => {
    try {
      setIsLoading(true)
      const response = await jobsApi.searchJobs({ q: searchQuery, limit: 20 })
      setJobs(response.data.data.jobs.map((j: { job: Job }) => j.job))
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    fetchJobs()
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
      
      <main className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-secondary-900 dark:text-white mb-8">
          Job Search
        </h1>

        {/* Search Bar */}
        <Card className="mb-8">
          <CardContent className="pt-6">
            <form onSubmit={handleSearch} className="flex gap-4">
              <Input
                placeholder="Search jobs, skills, or companies..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1"
              />
              <Button type="submit">Search</Button>
            </form>
          </CardContent>
        </Card>

        {/* Jobs List */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loading size="lg" />
          </div>
        ) : (
          <div className="grid gap-4">
            {jobs.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-secondary-600 dark:text-secondary-400">
                    No jobs found. Try adjusting your search.
                  </p>
                </CardContent>
              </Card>
            ) : (
              jobs.map((job) => (
                <Card key={job.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="text-xl font-semibold text-secondary-900 dark:text-white">
                          {job.title}
                        </h3>
                        <p className="text-secondary-600 dark:text-secondary-400 mt-1">
                          {job.company?.name || 'Unknown Company'}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-sm text-secondary-500 dark:text-secondary-400">
                          <span>{job.location || 'Location not specified'}</span>
                          {job.is_remote && (
                            <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-xs">
                              Remote
                            </span>
                          )}
                          <span className="capitalize">{job.employment_type}</span>
                        </div>
                        {job.salary_range && (
                          <p className="mt-2 text-sm text-secondary-600 dark:text-secondary-400">
                            {job.salary_range.currency} {job.salary_range.min?.toLocaleString()} - {job.salary_range.max?.toLocaleString()}
                          </p>
                        )}
                      </div>
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    </div>
                    {job.required_skills && job.required_skills.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {job.required_skills.slice(0, 5).map((skill, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-1 bg-secondary-100 dark:bg-secondary-700 text-secondary-700 dark:text-secondary-300 rounded text-xs"
                          >
                            {skill}
                          </span>
                        ))}
                        {job.required_skills.length > 5 && (
                          <span className="px-2 py-1 text-secondary-500 dark:text-secondary-400 text-xs">
                            +{job.required_skills.length - 5} more
                          </span>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  )
}
