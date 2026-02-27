'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Loading } from '@/components/ui/loading'
import { scrapingApi } from '@/lib/api'

interface ScrapingStatus {
  available_sources: string[]
  selenium_configured: boolean
  note: string
}

interface ScrapingResult {
  total_scraped: number
  stored: number
  duplicates: number
  by_source: Record<string, number>
}

export default function JobScrapingPage() {
  const [status, setStatus] = useState<ScrapingStatus | null>(null)
  const [keywords, setKeywords] = useState('python, react, data science')
  const [location, setLocation] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<ScrapingResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    fetchStatus()
  }, [])

  const fetchStatus = async () => {
    try {
      const response = await scrapingApi.getScrapingStatus()
      setStatus(response.data.data)
    } catch (error) {
      console.error('Failed to fetch scraping status:', error)
      setError('Failed to fetch scraping status')
    }
  }

  const handleScrapeDemo = async () => {
    setIsLoading(true)
    setResult(null)
    setError(null)
    setSuccess(null)

    try {
      const keywordList = keywords.split(',').map(k => k.trim()).filter(Boolean)
      
      const response = await scrapingApi.scrapeDemoJobs({
        keywords: keywordList,
        count: 10,
      })

      setResult(response.data.data)
      setSuccess(`Scraped ${response.data.data.stored} jobs successfully!`)
    } catch (error: any) {
      console.error('Scraping failed:', error)
      setError(error.response?.data?.error || 'Failed to scrape jobs')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-secondary-900 dark:text-white mb-2">
            Job Scraping
          </h1>
          <p className="text-secondary-600 dark:text-secondary-400">
            Scrape job listings from external sources
          </p>
        </div>

        {/* Status Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>API Status</CardTitle>
            <CardDescription>
              Configuration status of job scraping sources
            </CardDescription>
          </CardHeader>
          <CardContent>
            {status ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  {status.available_sources.map((source) => (
                    <span
                      key={source}
                      className={`px-3 py-1 rounded-full text-sm font-medium ${
                        source === 'mock' || status.selenium_configured
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-secondary-100 text-secondary-800 dark:bg-secondary-800 dark:text-secondary-200'
                      }`}
                    >
                      {source}: {source === 'mock' || status.selenium_configured ? 'Available' : 'Needs Selenium'}
                    </span>
                  ))}
                </div>
                {!status.selenium_configured && (
                  <p className="text-sm text-amber-600 dark:text-amber-400">
                    {status.note}
                  </p>
                )}
              </div>
            ) : (
              <Loading size="sm" />
            )}
          </CardContent>
        </Card>

        {/* Scraping Form */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Scrape Jobs</CardTitle>
            <CardDescription>
              Enter keywords and location to scrape job listings
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg">
                  {error}
                </div>
              )}
              {success && (
                <div className="p-4 bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 rounded-lg">
                  {success}
                </div>
              )}

              <div>
                <label htmlFor="keywords" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  Keywords (comma-separated)
                </label>
                <Input
                  id="keywords"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="e.g., python, react, data science"
                />
              </div>

              <div>
                <label htmlFor="location" className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  Location (optional)
                </label>
                <Input
                  id="location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g., San Francisco, CA"
                />
              </div>

              <Button
                onClick={handleScrapeDemo}
                disabled={isLoading || !keywords.trim()}
                className="w-full"
              >
                {isLoading ? (
                  <>
                    <Loading size="sm" />
                    <span className="ml-2">Scraping...</span>
                  </>
                ) : (
                  'Scrape Demo Jobs'
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Results */}
        {result && (
          <Card>
            <CardHeader>
              <CardTitle>Scraping Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center p-4 bg-secondary-50 dark:bg-secondary-800 rounded-lg">
                  <p className="text-2xl font-bold text-primary-600">{result.total_scraped}</p>
                  <p className="text-sm text-secondary-600 dark:text-secondary-400">Total Scraped</p>
                </div>
                <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <p className="text-2xl font-bold text-green-600">{result.stored}</p>
                  <p className="text-sm text-secondary-600 dark:text-secondary-400">Stored</p>
                </div>
                <div className="text-center p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                  <p className="text-2xl font-bold text-amber-600">{result.duplicates}</p>
                  <p className="text-sm text-secondary-600 dark:text-secondary-400">Duplicates</p>
                </div>
              </div>

              {Object.keys(result.by_source).length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">By Source:</h4>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(result.by_source).map(([source, count]) => (
                      <span
                        key={source}
                        className="px-3 py-1 border border-secondary-200 dark:border-secondary-700 rounded-full text-sm"
                      >
                        {source}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
