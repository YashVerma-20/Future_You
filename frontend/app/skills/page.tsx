'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Loading } from '@/components/ui/loading'
import { Navbar } from '@/components/layout/navbar'
import { useAuth } from '@/hooks/useAuth'
import { recommendationsApi } from '@/lib/api'
import type { SkillGapAnalysis, SkillGap } from '@/types'
import { 
  TrendingUp, 
  AlertCircle, 
  CheckCircle2, 
  Target,
  BookOpen,
  ExternalLink,
  Lightbulb
} from 'lucide-react'

export default function SkillsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [analysis, setAnalysis] = useState<SkillGapAnalysis | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (isAuthenticated) {
      fetchSkillAnalysis()
    }
  }, [isAuthenticated])

  const fetchSkillAnalysis = async () => {
    try {
      setIsLoading(true)
      const response = await recommendationsApi.getMarketSkillGaps()
      setAnalysis(response.data.data)
    } catch (error) {
      console.error('Failed to fetch skill analysis:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-200 dark:border-red-800'
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800'
      default:
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800'
    }
  }

  const getDemandColor = (percentage: number) => {
    if (percentage >= 50) return 'text-red-600 dark:text-red-400'
    if (percentage >= 30) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-blue-600 dark:text-blue-400'
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
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900 dark:text-white">
            Skill Gap Analysis
          </h1>
          <p className="text-secondary-600 dark:text-secondary-400 mt-2">
            Discover skills that can unlock more career opportunities
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loading size="lg" />
          </div>
        ) : analysis ? (
          <div className="space-y-6">
            {/* Overview Cards */}
            <div className="grid md:grid-cols-3 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-secondary-500 flex items-center gap-2">
                    <Target className="w-4 h-4" />
                    Skill Coverage
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-secondary-900 dark:text-white">
                      {analysis.skill_coverage.percentage}%
                    </span>
                  </div>
                  <p className="text-sm text-secondary-500 mt-1">
                    {analysis.skill_coverage.covered_count} of {analysis.skill_coverage.total_high_demand} high-demand skills
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-secondary-500 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    Skill Gaps
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-secondary-900 dark:text-white">
                      {analysis.gaps.length}
                    </span>
                  </div>
                  <p className="text-sm text-secondary-500 mt-1">
                    High-demand skills you can acquire
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-secondary-500 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Your Skills
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-secondary-900 dark:text-white">
                      {analysis.user_skills.length}
                    </span>
                  </div>
                  <p className="text-sm text-secondary-500 mt-1">
                    Skills identified from your profile
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Top Opportunities */}
            {analysis.top_opportunities.length > 0 && (
              <Card className="bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 border-primary-200 dark:border-primary-800">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Lightbulb className="w-5 h-5 text-primary-600" />
                    Top Opportunities
                  </CardTitle>
                  <CardDescription>
                    Learning these skills could unlock the most job opportunities
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-3 gap-4">
                    {analysis.top_opportunities.map((opp, idx) => (
                      <div 
                        key={idx}
                        className="p-4 bg-white dark:bg-secondary-800 rounded-lg border border-primary-200 dark:border-primary-800"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-secondary-900 dark:text-white capitalize">
                            {opp.skill}
                          </span>
                          <span className={`text-sm font-medium ${getDemandColor(opp.demand_percentage)}`}>
                            {opp.demand_percentage}%
                          </span>
                        </div>
                        <p className="text-sm text-secondary-500">
                          Unlocks ~{opp.potential_jobs} job opportunities
                        </p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Skill Gaps List */}
            <Card>
              <CardHeader>
                <CardTitle>Detailed Skill Gaps</CardTitle>
                <CardDescription>
                  Prioritized list of skills to consider learning
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysis.gaps.map((gap: SkillGap, idx: number) => (
                    <div 
                      key={idx}
                      className={`p-4 rounded-lg border ${getPriorityColor(gap.priority)}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <span className="font-semibold capitalize">
                              {gap.skill}
                            </span>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium uppercase ${
                              gap.priority === 'high' 
                                ? 'bg-red-200 text-red-900 dark:bg-red-800 dark:text-red-200'
                                : gap.priority === 'medium'
                                ? 'bg-yellow-200 text-yellow-900 dark:bg-yellow-800 dark:text-yellow-200'
                                : 'bg-blue-200 text-blue-900 dark:bg-blue-800 dark:text-blue-200'
                            }`}>
                              {gap.priority} Priority
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-sm">
                            <span className="flex items-center gap-1">
                              <TrendingUp className="w-4 h-4" />
                              {gap.demand_percentage}% of jobs require this
                            </span>
                            <span className="flex items-center gap-1">
                              <CheckCircle2 className="w-4 h-4" />
                              {gap.job_count} opportunities
                            </span>
                          </div>
                        </div>
                        <a 
                          href={`https://www.google.com/search?q=learn+${encodeURIComponent(gap.skill)}+tutorial`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-4"
                        >
                          <Button variant="outline" size="sm">
                            <BookOpen className="w-4 h-4 mr-1" />
                            Learn
                            <ExternalLink className="w-3 h-3 ml-1" />
                          </Button>
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Your Current Skills */}
            <Card>
              <CardHeader>
                <CardTitle>Your Current Skills</CardTitle>
                <CardDescription>
                  Skills identified from your resume and profile
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {analysis.user_skills.map((skill, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1.5 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded-full text-sm font-medium"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 inline mr-1" />
                      {skill}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-secondary-600 dark:text-secondary-400 mb-4">
                Upload your resume to get a personalized skill gap analysis
              </p>
              <Button onClick={() => router.push('/resume/upload')}>
                Upload Resume
              </Button>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
