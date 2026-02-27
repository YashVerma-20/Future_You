'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Loading } from '@/components/ui/loading'
import { Navbar } from '@/components/layout/navbar'
import { useAuth } from '@/hooks/useAuth'
import { recommendationsApi } from '@/lib/api'
import type { CareerRoadmap } from '@/types'
import { 
  MapPin, 
  Target, 
  Clock, 
  CheckCircle2, 
  Circle,
  BookOpen,
  ExternalLink,
  Award,
  ArrowRight,
  Sparkles
} from 'lucide-react'

export default function RoadmapPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [roadmap, setRoadmap] = useState<CareerRoadmap | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (isAuthenticated) {
      fetchRoadmap()
    }
  }, [isAuthenticated])

  const fetchRoadmap = async () => {
    try {
      setIsLoading(true)
      const response = await recommendationsApi.getCareerRoadmap()
      setRoadmap(response.data.data)
    } catch (error) {
      console.error('Failed to fetch roadmap:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getResourceIcon = (type: string) => {
    switch (type) {
      case 'official':
        return <Award className="w-4 h-4" />
      case 'course':
        return <BookOpen className="w-4 h-4" />
      case 'certification':
        return <Award className="w-4 h-4" />
      default:
        return <ExternalLink className="w-4 h-4" />
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
      
      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900 dark:text-white">
            Your Career Roadmap
          </h1>
          <p className="text-secondary-600 dark:text-secondary-400 mt-2">
            Personalized growth plan based on your profile and market demand
          </p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loading size="lg" />
          </div>
        ) : roadmap ? (
          <div className="space-y-6">
            {/* Overview Card */}
            <Card className="bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 border-primary-200 dark:border-primary-800">
              <CardContent className="p-6">
                <div className="flex flex-col md:flex-row md:items-center gap-6">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 text-primary-700 dark:text-primary-300 mb-3">
                      <Sparkles className="w-5 h-5" />
                      <span className="font-semibold">Career Journey Overview</span>
                    </div>
                    <p className="text-secondary-700 dark:text-secondary-300 text-lg">
                      {roadmap.summary}
                    </p>
                    <div className="mt-4 flex flex-wrap items-center gap-6">
                      <div className="flex items-center gap-2">
                        <MapPin className="w-5 h-5 text-secondary-400" />
                        <span className="text-secondary-600 dark:text-secondary-400">
                          <span className="font-medium text-secondary-900 dark:text-white">Current:</span> {roadmap.current_position}
                        </span>
                      </div>
                      <ArrowRight className="w-5 h-5 text-secondary-300 hidden md:block" />
                      <div className="flex items-center gap-2">
                        <Target className="w-5 h-5 text-primary-500" />
                        <span className="text-secondary-600 dark:text-secondary-400">
                          <span className="font-medium text-secondary-900 dark:text-white">Target:</span> {roadmap.target_position}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-secondary-800 rounded-lg">
                    <Clock className="w-5 h-5 text-primary-500" />
                    <div>
                      <p className="text-2xl font-bold text-secondary-900 dark:text-white">
                        {roadmap.estimated_timeline_months}
                      </p>
                      <p className="text-xs text-secondary-500">months estimated</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Milestones Timeline */}
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-secondary-900 dark:text-white">
                Your Milestones
              </h2>
              
              {roadmap.milestones.map((milestone, idx) => (
                <Card key={idx} className="relative overflow-hidden">
                  {/* Timeline connector */}
                  {idx < roadmap.milestones.length - 1 && (
                    <div className="absolute left-6 top-16 bottom-0 w-0.5 bg-secondary-200 dark:bg-secondary-700" />
                  )}
                  
                  <CardContent className="p-6">
                    <div className="flex gap-4">
                      {/* Step indicator */}
                      <div className="flex-shrink-0">
                        <div className="w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                          <span className="text-lg font-bold text-primary-600 dark:text-primary-400">
                            {milestone.order}
                          </span>
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1">
                        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                          <div className="flex-1">
                            <h3 className="text-lg font-semibold text-secondary-900 dark:text-white">
                              {milestone.title}
                            </h3>
                            <p className="text-secondary-600 dark:text-secondary-400 mt-1">
                              {milestone.description}
                            </p>
                            
                            {/* Reason */}
                            <div className="mt-3 p-3 bg-secondary-50 dark:bg-secondary-800/50 rounded-lg">
                              <p className="text-sm text-secondary-600 dark:text-secondary-400">
                                <span className="font-medium">Why this matters:</span> {milestone.reason}
                              </p>
                            </div>

                            {/* Skills to acquire */}
                            {milestone.skills_to_acquire.length > 0 && (
                              <div className="mt-3">
                                <p className="text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                                  Skills you will acquire:
                                </p>
                                <div className="flex flex-wrap gap-2">
                                  {milestone.skills_to_acquire.map((skill, sidx) => (
                                    <span
                                      key={sidx}
                                      className="px-2.5 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-800 dark:text-primary-300 rounded-full text-xs font-medium"
                                    >
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Completion criteria */}
                            <div className="mt-3 flex items-start gap-2">
                              <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                              <p className="text-sm text-secondary-600 dark:text-secondary-400">
                                <span className="font-medium">Complete when:</span> {milestone.completion_criteria}
                              </p>
                            </div>
                          </div>

                          {/* Meta info */}
                          <div className="flex flex-col items-end gap-3">
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-secondary-100 dark:bg-secondary-800 rounded-full">
                              <Clock className="w-4 h-4 text-secondary-500" />
                              <span className="text-sm font-medium text-secondary-700 dark:text-secondary-300">
                                {milestone.estimated_weeks} weeks
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Resources */}
                        {milestone.resources.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-secondary-200 dark:border-secondary-700">
                            <p className="text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-2">
                              Recommended Resources:
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {milestone.resources.map((resource, ridx) => (
                                <a
                                  key={ridx}
                                  href={resource.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-700 rounded-lg text-sm text-secondary-700 dark:text-secondary-300 hover:bg-secondary-50 dark:hover:bg-secondary-700 transition-colors"
                                >
                                  {getResourceIcon(resource.type)}
                                  {resource.name}
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Action Cards */}
            <div className="grid md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="w-5 h-5" />
                    Start Learning
                  </CardTitle>
                  <CardDescription>
                    Begin with the first milestone
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {roadmap.milestones[0] && (
                    <div>
                      <p className="font-medium text-secondary-900 dark:text-white mb-2">
                        {roadmap.milestones[0].title}
                      </p>
                      <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-4">
                        Estimated time: {roadmap.milestones[0].estimated_weeks} weeks
                      </p>
                      <Button className="w-full">
                        Get Started
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="w-5 h-5" />
                    Track Progress
                  </CardTitle>
                  <CardDescription>
                    Monitor your career growth
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-4">
                    Complete milestones and track your journey to becoming a {roadmap.target_position}
                  </p>
                  <Button variant="outline" className="w-full" onClick={() => router.push('/dashboard')}>
                    View Dashboard
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-secondary-600 dark:text-secondary-400 mb-4">
                Upload your resume to generate your personalized career roadmap
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
