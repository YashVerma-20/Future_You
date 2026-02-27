import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-primary-50 to-secondary-100 dark:from-secondary-900 dark:to-secondary-800">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-16 animate-fade-in">
          <h1 className="text-5xl font-bold text-secondary-900 dark:text-white mb-6">
            Future You
          </h1>
          <p className="text-xl text-secondary-600 dark:text-secondary-300 max-w-2xl mx-auto">
            AI-powered platform for intelligent job matching, skill analysis, and career development
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link href="/signup">
              <Button size="lg">Get Started</Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg">Sign In</Button>
            </Link>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <Card className="animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <CardHeader>
              <CardTitle>Resume Intelligence</CardTitle>
              <CardDescription>
                AI-powered resume parsing and skill extraction
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-secondary-600 dark:text-secondary-400">
                Upload your resume and let our AI extract your skills, experience, and qualifications automatically.
              </p>
            </CardContent>
          </Card>

          <Card className="animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <CardHeader>
              <CardTitle>Job Matching</CardTitle>
              <CardDescription>
                Intelligent job recommendations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-secondary-600 dark:text-secondary-400">
                Get personalized job recommendations based on your skills, experience, and career goals.
              </p>
            </CardContent>
          </Card>

          <Card className="animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <CardHeader>
              <CardTitle>Skill Development</CardTitle>
              <CardDescription>
                Personalized learning paths
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-secondary-600 dark:text-secondary-400">
                Identify skill gaps and get customized learning recommendations to advance your career.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>
  )
}
