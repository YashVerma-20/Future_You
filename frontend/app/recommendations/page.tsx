'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Loading } from '@/components/ui/loading'
import { Navbar } from '@/components/layout/navbar'
import { useAuth } from '@/hooks/useAuth'
import { recommendationsApi, scrapingApi } from '@/lib/api'
import type { JobMatch } from '@/types'
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  TrendingUp, 
  Briefcase,
  AlertCircle,
  Sparkles,
  RefreshCw,
  MapPin,
  X,
  ExternalLink
} from 'lucide-react'

export default function RecommendationsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [recommendations, setRecommendations] = useState<JobMatch[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isScraping, setIsScraping] = useState(false)
  const [scrapeMessage, setScrapeMessage] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<JobMatch | null>(null)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (isAuthenticated) {
      fetchRecommendations()
    }
  }, [isAuthenticated])

  const fetchRecommendations = async () => {
    try {
      setIsLoading(true)
      const response = await recommendationsApi.matchJobs(10)
      setRecommendations(response.data.data.matches)
    } catch (error) {
      console.error('Failed to fetch recommendations:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleScrapeJobs = async () => {
    let scrapingId: string | null = null
    
    try {
      setIsScraping(true)
      setScrapeMessage('🔍 Starting job search...')
      
      // Start scraping
      const response = await scrapingApi.scrapeJobsForMe({ max_results_per_source: 15 })
      
      if (!response.data.success) {
        setScrapeMessage('❌ Failed to start job search. Please try again.')
        setTimeout(() => setScrapeMessage(null), 5000)
        return
      }
      
      scrapingId = response.data.data.scraping_id
      const sources = response.data.data.sources || ['indeed']
      
      // Poll for status
      setScrapeMessage(`🔍 Searching ${sources.join(', ')} for jobs... This may take 30-60 seconds.`)
      
      let attempts = 0
      const maxAttempts = 60  // 60 seconds max
      
      while (attempts < maxAttempts && scrapingId) {
        await new Promise(resolve => setTimeout(resolve, 2000))  // Wait 2 seconds
        
        try {
          const statusResponse = await scrapingApi.getScrapingStatus(scrapingId)
          
          if (statusResponse.data.success) {
            const status = statusResponse.data.data.status
            
            if (status === 'completed') {
              const result = statusResponse.data.data.result
              const stored = result?.stored || 0
              const bySource = result?.by_source || {}
              const sourceSummary = Object.entries(bySource).map(([k, v]) => `${k}: ${v}`).join(', ')
              
              setScrapeMessage(`✅ Found ${stored} new jobs from ${sourceSummary}! Refreshing...`)
              await fetchRecommendations()
              setScrapeMessage(null)
              return
            } else if (status === 'failed') {
              setScrapeMessage('❌ Job search failed. Please try again.')
              setTimeout(() => setScrapeMessage(null), 5000)
              return
            }
            // If in_progress, continue polling
          }
        } catch (pollError) {
          // Continue polling on error
        }
        
        attempts++
        if (attempts % 10 === 0) {
          setScrapeMessage(`🔍 Still searching... (${attempts * 2} seconds)`)
        }
      }
      
      // If we reach here, we timed out
      setScrapeMessage('⏱️ Search is taking longer than expected. Please refresh the page in a moment to see new jobs.')
      setTimeout(() => setScrapeMessage(null), 10000)
      
    } catch (error: any) {
      console.error('Failed to scrape jobs:', error)
      if (error.response?.status === 400) {
        setScrapeMessage('⚠️ Please upload and process your resume first.')
      } else {
        setScrapeMessage('❌ Failed to fetch jobs. Please try again.')
      }
      setTimeout(() => setScrapeMessage(null), 8000)
    } finally {
      setIsScraping(false)
    }
  }

  const getMatchScoreColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-500'
    if (score >= 0.6) return 'bg-blue-500'
    if (score >= 0.4) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getMatchScoreLabel = (score: number) => {
    if (score >= 0.8) return 'Excellent Match'
    if (score >= 0.6) return 'Good Match'
    if (score >= 0.4) return 'Fair Match'
    return 'Low Match'
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
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-secondary-900 dark:text-white">
              Recommended Jobs
            </h1>
            <p className="text-secondary-600 dark:text-secondary-400 mt-2">
              Personalized job matches based on your skills and experience
            </p>
            <p className="text-sm text-green-600 dark:text-green-400 mt-1 flex items-center gap-1">
              <MapPin className="w-4 h-4" />
              Showing jobs in India only
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <Button 
              onClick={handleScrapeJobs} 
              disabled={isScraping}
              className="flex items-center gap-2"
            >
              {isScraping ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Finding Jobs...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Find Jobs for Me
                </>
              )}
            </Button>
            {scrapeMessage && (
              <p className={`text-sm ${scrapeMessage.includes('Failed') || scrapeMessage.includes('Please') ? 'text-red-500' : 'text-green-600'}`}>
                {scrapeMessage}
              </p>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loading size="lg" />
          </div>
        ) : (
          <div className="grid gap-6">
            {recommendations.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-secondary-600 dark:text-secondary-400 mb-4">
                    No recommendations yet. Upload your resume to get personalized job matches.
                  </p>
                  <Button onClick={() => router.push('/resume/upload')}>
                    Upload Resume
                  </Button>
                </CardContent>
              </Card>
            ) : (
              recommendations.map((rec, index) => (
                <Card key={rec.job.id} className="hover:shadow-lg transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-xl font-semibold text-secondary-900 dark:text-white">
                            {rec.job.title}
                          </h3>
                          <span className={`px-3 py-1 text-white rounded-full text-sm font-medium ${getMatchScoreColor(rec.final_score)}`}>
                            {Math.round(rec.final_score * 100)}% {getMatchScoreLabel(rec.final_score)}
                          </span>
                        </div>
                        <p className="text-secondary-600 dark:text-secondary-400">
                          {rec.job.company?.name || 'Unknown Company'}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-sm text-secondary-500 dark:text-secondary-400">
                          <span>{rec.job.location || 'Location not specified'}</span>
                          {rec.job.is_remote && (
                            <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-xs">
                              Remote
                            </span>
                          )}
                          <span className="capitalize">{rec.job.employment_type}</span>
                          {/* Job Source Badge */}
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            rec.job.source_platform === 'indeed' 
                              ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' 
                              : rec.job.source_platform === 'internshala'
                              ? 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200'
                              : rec.job.source_platform === 'naukri'
                              ? 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200'
                              : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200'
                          }`}>
                            {rec.job.source_platform === 'indeed' ? 'Indeed' : 
                             rec.job.source_platform === 'internshala' ? 'Internshala' : 
                             rec.job.source_platform === 'naukri' ? 'Naukri' : 
                             rec.job.source_platform}
                          </span>
                        </div>
                        
                        {/* Job Description */}
                        {rec.job.description && (
                          <div className="mt-3 p-3 bg-secondary-50 dark:bg-secondary-800/50 rounded-lg">
                            <p className="text-sm text-secondary-700 dark:text-secondary-300 line-clamp-3">
                              {rec.job.description}
                            </p>
                          </div>
                        )}
                        
                        {/* AI Explanation */}
                        <div className="mt-4 p-4 bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 rounded-lg border border-primary-200 dark:border-primary-800">
                          <div className="flex items-start gap-2">
                            <Sparkles className="w-5 h-5 text-primary-600 dark:text-primary-400 mt-0.5 flex-shrink-0" />
                            <p className="text-secondary-700 dark:text-secondary-300 text-sm">
                              {rec.explanation}
                            </p>
                          </div>
                        </div>

                        {/* Match Score Breakdown */}
                        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                          <div className="p-3 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                            <div className="flex items-center gap-1.5 text-xs text-secondary-500 dark:text-secondary-400 mb-1">
                              <TrendingUp className="w-3.5 h-3.5" />
                              Semantic
                            </div>
                            <div className="text-lg font-semibold text-secondary-900 dark:text-white">
                              {Math.round(rec.breakdown.semantic_score * 100)}%
                            </div>
                          </div>
                          <div className="p-3 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                            <div className="flex items-center gap-1.5 text-xs text-secondary-500 dark:text-secondary-400 mb-1">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Skills
                            </div>
                            <div className="text-lg font-semibold text-secondary-900 dark:text-white">
                              {Math.round(rec.breakdown.skill_overlap * 100)}%
                            </div>
                          </div>
                          <div className="p-3 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                            <div className="flex items-center gap-1.5 text-xs text-secondary-500 dark:text-secondary-400 mb-1">
                              <Clock className="w-3.5 h-3.5" />
                              Freshness
                            </div>
                            <div className="text-lg font-semibold text-secondary-900 dark:text-white">
                              {Math.round(rec.breakdown.freshness_score * 100)}%
                            </div>
                          </div>
                          <div className="p-3 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                            <div className="flex items-center gap-1.5 text-xs text-secondary-500 dark:text-secondary-400 mb-1">
                              <Briefcase className="w-3.5 h-3.5" />
                              Experience
                            </div>
                            <div className="text-lg font-semibold text-secondary-900 dark:text-white">
                              {Math.round(rec.breakdown.experience_match * 100)}%
                            </div>
                          </div>
                        </div>

                        {/* Matching Skills */}
                        {rec.matching_skills.length > 0 && (
                          <div className="mt-4">
                            <p className="text-sm font-medium text-green-700 dark:text-green-400 mb-2 flex items-center gap-1.5">
                              <CheckCircle2 className="w-4 h-4" />
                              Matching Skills ({rec.matching_skills.length})
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {rec.matching_skills.slice(0, 8).map((skill, idx) => (
                                <span
                                  key={idx}
                                  className="px-2.5 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded-full text-xs font-medium"
                                >
                                  {skill}
                                </span>
                              ))}
                              {rec.matching_skills.length > 8 && (
                                <span className="px-2.5 py-1 text-xs text-secondary-500 dark:text-secondary-400">
                                  +{rec.matching_skills.length - 8} more
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Missing Skills */}
                        {rec.missing_skills.length > 0 && (
                          <div className="mt-4 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                            <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-2 flex items-center gap-1.5">
                              <AlertCircle className="w-4 h-4" />
                              Skills to Develop ({rec.missing_skills.length})
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {rec.missing_skills.slice(0, 5).map((skill, idx) => (
                                <span
                                  key={idx}
                                  className="px-2.5 py-1 bg-amber-100 dark:bg-amber-800 text-amber-800 dark:text-amber-200 rounded-full text-xs font-medium"
                                >
                                  {skill}
                                </span>
                              ))}
                              {rec.missing_skills.length > 5 && (
                                <span className="text-xs text-amber-700 dark:text-amber-300">
                                  +{rec.missing_skills.length - 5} more
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Freshness Badge */}
                        {rec.freshness_days !== null && rec.freshness_days <= 7 && (
                          <div className="mt-3 flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
                            <Clock className="w-3.5 h-3.5" />
                            Posted {rec.freshness_days === 0 ? 'today' : `${rec.freshness_days} days ago`}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex flex-col gap-2">
                        <Button 
                          onClick={() => rec.job.source_url && window.open(rec.job.source_url, '_blank')}
                          disabled={!rec.job.source_url}
                          className="flex items-center gap-2"
                        >
                          <ExternalLink className="w-4 h-4" />
                          Apply Now
                        </Button>
                        <Button 
                          variant="outline" 
                          onClick={() => setSelectedJob(rec)}
                        >
                          View Details
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}
      </main>

      {/* Job Details Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-secondary-900 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white dark:bg-secondary-900 border-b border-secondary-200 dark:border-secondary-700 p-4 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-secondary-900 dark:text-white">
                  {selectedJob.job.title}
                </h2>
                <p className="text-secondary-600 dark:text-secondary-400">
                  {selectedJob.job.company?.name || 'Unknown Company'}
                </p>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="p-2 hover:bg-secondary-100 dark:hover:bg-secondary-800 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-secondary-500" />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Job Meta */}
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 bg-secondary-100 dark:bg-secondary-800 text-secondary-700 dark:text-secondary-300 rounded-full text-sm">
                  {selectedJob.job.location || 'Location not specified'}
                </span>
                {selectedJob.job.is_remote && (
                  <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-sm">
                    Remote
                  </span>
                )}
                <span className="px-3 py-1 bg-secondary-100 dark:bg-secondary-800 text-secondary-700 dark:text-secondary-300 rounded-full text-sm capitalize">
                  {selectedJob.job.employment_type}
                </span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  selectedJob.job.source_platform === 'indeed' 
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200' 
                    : selectedJob.job.source_platform === 'internshala'
                    ? 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200'
                    : selectedJob.job.source_platform === 'naukri'
                    ? 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200'
                }`}>
                  {selectedJob.job.source_platform === 'indeed' ? 'Indeed' : 
                   selectedJob.job.source_platform === 'internshala' ? 'Internshala' : 
                   selectedJob.job.source_platform === 'naukri' ? 'Naukri' : 
                   selectedJob.job.source_platform}
                </span>
              </div>

              {/* Description */}
              {selectedJob.job.description && (
                <div>
                  <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-2">
                    Job Description
                  </h3>
                  <div className="text-secondary-700 dark:text-secondary-300 whitespace-pre-line">
                    {selectedJob.job.description}
                  </div>
                </div>
              )}

              {/* Requirements */}
              {selectedJob.job.requirements && (
                <div>
                  <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-2">
                    Requirements
                  </h3>
                  <div className="text-secondary-700 dark:text-secondary-300 whitespace-pre-line">
                    {selectedJob.job.requirements}
                  </div>
                </div>
              )}

              {/* Responsibilities */}
              {selectedJob.job.responsibilities && (
                <div>
                  <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-2">
                    Responsibilities
                  </h3>
                  <div className="text-secondary-700 dark:text-secondary-300 whitespace-pre-line">
                    {selectedJob.job.responsibilities}
                  </div>
                </div>
              )}

              {/* Required Skills */}
              {selectedJob.job.required_skills && selectedJob.job.required_skills.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-secondary-900 dark:text-white mb-2">
                    Required Skills
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedJob.job.required_skills.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1 bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 rounded-full text-sm"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Match Score */}
              <div className="p-4 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-secondary-900 dark:text-white">Match Score</span>
                  <span className={`px-3 py-1 text-white rounded-full text-sm font-medium ${
                    selectedJob.final_score >= 0.8 ? 'bg-green-500' :
                    selectedJob.final_score >= 0.6 ? 'bg-blue-500' :
                    selectedJob.final_score >= 0.4 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}>
                    {Math.round(selectedJob.final_score * 100)}% Match
                  </span>
                </div>
                <p className="text-sm text-secondary-600 dark:text-secondary-400">
                  {selectedJob.explanation}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 border-t border-secondary-200 dark:border-secondary-700">
                <Button 
                  className="flex-1 flex items-center justify-center gap-2"
                  onClick={() => selectedJob.job.source_url && window.open(selectedJob.job.source_url, '_blank')}
                  disabled={!selectedJob.job.source_url}
                >
                  <ExternalLink className="w-4 h-4" />
                  Apply Now
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => setSelectedJob(null)}
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
