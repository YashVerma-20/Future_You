'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loading } from '@/components/ui/loading'
import { Navbar } from '@/components/layout/navbar'
import { useAuth } from '@/hooks/useAuth'
import { resumeApi, recommendationsApi } from '@/lib/api'
import type { ProfileStrength, DomainResult, SeniorityResult, MatchAnalytics, RoadmapSummary } from '@/types'
import { 
  Target, 
  TrendingUp, 
  Briefcase, 
  Award, 
  Lightbulb,
  ArrowRight,
  Zap,
  BookOpen,
  BarChart3
} from 'lucide-react'

interface UserSkill {
  skill_name: string
  proficiency: number
  is_verified: boolean
}

export default function DashboardPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()

  const [skills, setSkills] = useState<UserSkill[]>([])
  const [recommendationsCount, setRecommendationsCount] = useState(0)
  const [isLoadingData, setIsLoadingData] = useState(true)
  
  // AI Mentor data
  const [profileStrength, setProfileStrength] = useState<ProfileStrength | null>(null)
  const [domain, setDomain] = useState<DomainResult | null>(null)
  const [seniority, setSeniority] = useState<SeniorityResult | null>(null)
  const [analytics, setAnalytics] = useState<MatchAnalytics | null>(null)
  const [roadmapSummary, setRoadmapSummary] = useState<RoadmapSummary | null>(null)

  /**
   * ✅ Redirect ONLY when auth check is fully complete
   * and user is definitively null.
   */
  useEffect(() => {
    if (!isLoading && !user) {
      router.replace('/login')
    }
  }, [isLoading, user, router])

  /**
   * ✅ Fetch dashboard data only when user exists
   */
  useEffect(() => {
    if (user) {
      fetchDashboardData()
    }
  }, [user])

  const fetchDashboardData = async () => {
    try {
      setIsLoadingData(true)

      // Fetch basic data
      const skillsResponse = await resumeApi.getSkills()
      setSkills(skillsResponse.data.data.skills || [])

      const recsResponse = await recommendationsApi.getJobRecommendations()
      setRecommendationsCount(
        recsResponse.data.data.recommendations?.length || 0
      )

      // Fetch AI Mentor data
      try {
        const [strengthRes, domainRes, seniorityRes, analyticsRes, roadmapRes] = await Promise.all([
          recommendationsApi.getProfileStrength(),
          recommendationsApi.getDomain(),
          recommendationsApi.getSeniority(),
          recommendationsApi.getMatchAnalytics(),
          recommendationsApi.getRoadmapSummary()
        ])

        setProfileStrength(strengthRes.data.data)
        setDomain(domainRes.data.data)
        setSeniority(seniorityRes.data.data)
        setAnalytics(analyticsRes.data.data)
        setRoadmapSummary(roadmapRes.data.data)
      } catch (aiError) {
        console.log('AI Mentor data not available yet:', aiError)
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setIsLoadingData(false)
    }
  }

  const getStrengthColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 60) return 'text-blue-600 dark:text-blue-400'
    if (score >= 40) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getStrengthBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-500'
    if (score >= 60) return 'bg-blue-500'
    if (score >= 40) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  /**
   * ✅ While checking auth state
   */
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loading size="lg" />
      </div>
    )
  }

  /**
   * ✅ If no user, redirect effect will handle navigation
   */
  if (!user) {
    return null
  }

  const legacyProfileStrength = skills.length > 0 ? Math.min(100, 30 + skills.length * 5) : 15
  const displayProfileStrength = profileStrength?.profile_strength ?? legacyProfileStrength

  return (
    <div className="min-h-screen bg-secondary-50 dark:bg-secondary-900">
      <Navbar />

      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900 dark:text-white">
            Welcome back, {user.display_name || user.email?.split('@')[0]}
          </h1>
          <p className="text-secondary-600 dark:text-secondary-400 mt-2">
            Here&apos;s your Future You overview
          </p>
        </div>

        {isLoadingData ? (
          <div className="flex justify-center py-12">
            <Loading size="lg" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* AI Career Mentor Overview */}
            {profileStrength && (
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Profile Strength Card */}
                <Card className="relative overflow-hidden">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-secondary-500 dark:text-secondary-400 flex items-center gap-2">
                      <Target className="w-4 h-4" />
                      Profile Strength
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-baseline gap-2">
                      <span className={`text-3xl font-bold ${getStrengthColor(displayProfileStrength)}`}>
                        {displayProfileStrength}%
                      </span>
                      <span className="text-sm text-secondary-500">
                        {profileStrength.improvement_potential > 0 && `+${profileStrength.improvement_potential}% potential`}
                      </span>
                    </div>
                    <div className="mt-3 h-2 bg-secondary-200 dark:bg-secondary-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-500 ${getStrengthBgColor(displayProfileStrength)}`}
                        style={{ width: `${displayProfileStrength}%` }}
                      />
                    </div>
                    {profileStrength.suggestions.length > 0 && (
                      <p className="mt-3 text-xs text-secondary-600 dark:text-secondary-400">
                        {profileStrength.suggestions[0]}
                      </p>
                    )}
                  </CardContent>
                </Card>

                {/* Domain Card */}
                {domain && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-secondary-500 dark:text-secondary-400 flex items-center gap-2">
                        <Briefcase className="w-4 h-4" />
                        Career Domain
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-lg font-semibold text-secondary-900 dark:text-white">
                        {domain.primary_domain}
                      </p>
                      <p className="text-sm text-secondary-500">
                        {Math.round(domain.primary_confidence * 100)}% confidence
                      </p>
                      {domain.secondary_domain && (
                        <p className="mt-2 text-xs text-secondary-400">
                          Also: {domain.secondary_domain}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Seniority Card */}
                {seniority && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-secondary-500 dark:text-secondary-400 flex items-center gap-2">
                        <Award className="w-4 h-4" />
                        Experience Level
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-lg font-semibold text-secondary-900 dark:text-white">
                        {seniority.seniority_level}
                      </p>
                      <p className="text-sm text-secondary-500">
                        ~{seniority.estimated_years} years
                      </p>
                      {seniority.next_level && (
                        <Link href="/roadmap" className="mt-2 inline-flex items-center text-xs text-primary-600 hover:text-primary-700">
                          Path to {seniority.next_level}
                          <ArrowRight className="w-3 h-3 ml-1" />
                        </Link>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Match Analytics Card */}
                {analytics && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-secondary-500 dark:text-secondary-400 flex items-center gap-2">
                        <BarChart3 className="w-4 h-4" />
                        Match Rate
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-secondary-900 dark:text-white">
                          {analytics.average_match_score}%
                        </span>
                        {analytics.improvement.change_percent > 0 && (
                          <span className="text-xs text-green-600 flex items-center">
                            <TrendingUp className="w-3 h-3 mr-0.5" />
                            +{analytics.improvement.change_percent}%
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-secondary-500">
                        {analytics.high_match_jobs} high matches
                      </p>
                      <p className="text-xs text-secondary-400 mt-1">
                        from {analytics.total_jobs_analyzed} jobs analyzed
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {/* Career Roadmap Preview */}
            {roadmapSummary?.available && roadmapSummary.next_milestone && (
              <Card className="bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 border-primary-200 dark:border-primary-800">
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 text-primary-700 dark:text-primary-300 mb-2">
                        <Zap className="w-5 h-5" />
                        <span className="font-semibold">Your Career Roadmap</span>
                      </div>
                      <p className="text-secondary-700 dark:text-secondary-300">
                        {roadmapSummary.summary}
                      </p>
                      <div className="mt-3 flex items-center gap-4 text-sm">
                        <span className="text-secondary-600">
                          <span className="font-medium">Current:</span> {roadmapSummary.current_position}
                        </span>
                        <ArrowRight className="w-4 h-4 text-secondary-400" />
                        <span className="text-secondary-600">
                          <span className="font-medium">Target:</span> {roadmapSummary.target_position}
                        </span>
                      </div>
                    </div>
                    <Link href="/roadmap">
                      <Button className="whitespace-nowrap">
                        View Full Roadmap
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Main Dashboard Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Legacy Profile Strength - show if AI data not available */}
              {!profileStrength && (
                <Card>
                  <CardHeader>
                    <CardTitle>Profile Strength</CardTitle>
                    <CardDescription>
                      Complete your profile for better matches
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="relative pt-1">
                      <div className="flex mb-2 items-center justify-between">
                        <span className="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-primary-600 bg-primary-200 dark:bg-primary-900 dark:text-primary-300">
                          {legacyProfileStrength < 50
                            ? 'Beginner'
                            : legacyProfileStrength < 80
                            ? 'Intermediate'
                            : 'Expert'}
                        </span>
                        <span className="text-xs font-semibold inline-block text-primary-600 dark:text-primary-400">
                          {legacyProfileStrength}%
                        </span>
                      </div>

                      <div className="overflow-hidden h-2 mb-4 rounded bg-primary-200 dark:bg-primary-900">
                        <div
                          style={{ width: `${legacyProfileStrength}%` }}
                          className="h-2 bg-primary-500 transition-all duration-500"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

            {/* Skills Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Your Skills</CardTitle>
                <CardDescription>
                  Skills extracted from your resume
                </CardDescription>
              </CardHeader>
              <CardContent>
                {skills.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {skills.slice(0, 8).map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 rounded text-sm"
                      >
                        {skill.skill_name}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-secondary-600 dark:text-secondary-400 mb-4">
                      No skills added yet
                    </p>
                    <Link href="/resume/upload">
                      <Button size="sm">Upload Resume</Button>
                    </Link>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle>Recommendations</CardTitle>
                <CardDescription>
                  Personalized job matches
                </CardDescription>
              </CardHeader>
              <CardContent>
                {recommendationsCount > 0 ? (
                  <div>
                    <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">
                      {recommendationsCount}
                    </p>
                    <p className="text-secondary-600 dark:text-secondary-400">
                      jobs match your profile
                    </p>
                    <Link href="/recommendations">
                      <Button className="mt-4" variant="outline" size="sm">
                        View Recommendations
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <p className="text-secondary-600 dark:text-secondary-400 mb-4">
                      Upload your resume to get personalized recommendations
                    </p>
                    <Link href="/resume/upload">
                      <Button size="sm">Upload Resume</Button>
                    </Link>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Improve your career prospects
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <Link href="/skills">
                  <Button variant="outline" className="w-full justify-start" size="sm">
                    <Lightbulb className="w-4 h-4 mr-2" />
                    Analyze Skill Gaps
                  </Button>
                </Link>
                <Link href="/resume/upload">
                  <Button variant="outline" className="w-full justify-start" size="sm">
                    <BookOpen className="w-4 h-4 mr-2" />
                    Update Resume
                  </Button>
                </Link>
                <Link href="/jobs">
                  <Button variant="outline" className="w-full justify-start" size="sm">
                    <Briefcase className="w-4 h-4 mr-2" />
                    Browse All Jobs
                  </Button>
                </Link>
              </CardContent>
            </Card>
          </div>
          </div>
        )}
      </main>
    </div>
  )
}