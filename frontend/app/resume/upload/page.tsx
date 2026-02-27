'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Loading } from '@/components/ui/loading'
import { Navbar } from '@/components/layout/navbar'
import { useAuth } from '@/hooks/useAuth'
import { resumeApi } from '@/lib/api'

export default function ResumeUploadPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<any>(null)
  const [error, setError] = useState('')

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileUpload(files[0])
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileUpload(files[0])
    }
  }, [])

  const handleFileUpload = async (file: File) => {
    // Validate file type
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if (!allowedTypes.includes(file.type)) {
      setError('Please upload a PDF or DOCX file')
      return
    }

    // Validate file size (16MB)
    if (file.size > 16 * 1024 * 1024) {
      setError('File size must be less than 16MB')
      return
    }

    setError('')
    setIsUploading(true)
    setUploadResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await resumeApi.uploadResume(formData)
      setUploadResult(response.data.data)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to upload resume')
    } finally {
      setIsUploading(false)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loading size="lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    router.push('/login')
    return null
  }

  return (
    <div className="min-h-screen bg-secondary-50 dark:bg-secondary-900">
      <Navbar />
      
      <main className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-secondary-900 dark:text-white mb-8">
          Upload Resume
        </h1>

        <div className="max-w-2xl mx-auto">
          {/* Upload Area */}
          <Card>
            <CardContent className="pt-6">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                  isDragging
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-secondary-300 dark:border-secondary-600 hover:border-secondary-400 dark:hover:border-secondary-500'
                }`}
              >
                {isUploading ? (
                  <Loading text="Uploading and processing resume..." />
                ) : (
                  <>
                    <svg
                      className="mx-auto h-12 w-12 text-secondary-400"
                      stroke="currentColor"
                      fill="none"
                      viewBox="0 0 48 48"
                      aria-hidden="true"
                    >
                      <path
                        d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                    <div className="mt-4">
                      <label
                        htmlFor="file-upload"
                        className="cursor-pointer"
                      >
                        <span className="text-primary-600 hover:text-primary-500 dark:text-primary-400 font-medium">
                          Click to upload
                        </span>{' '}
                        <span className="text-secondary-600 dark:text-secondary-400">
                          or drag and drop
                        </span>
                        <input
                          id="file-upload"
                          name="file-upload"
                          type="file"
                          className="sr-only"
                          accept=".pdf,.docx"
                          onChange={handleFileSelect}
                        />
                      </label>
                    </div>
                    <p className="mt-2 text-sm text-secondary-500 dark:text-secondary-400">
                      PDF or DOCX up to 16MB
                    </p>
                  </>
                )}
              </div>

              {error && (
                <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg">
                  {error}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Upload Result */}
          {uploadResult && (
            <Card className="mt-8">
              <CardHeader>
                <CardTitle>Processing Complete</CardTitle>
                <CardDescription>
                  We&apos;ve analyzed your resume and extracted the following skills
                </CardDescription>
              </CardHeader>
              <CardContent>
                {uploadResult.processing_result?.skills?.length > 0 ? (
                  <div>
                    <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-4">
                      Extracted {uploadResult.processing_result.skills.length} skills:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {uploadResult.processing_result.skills.slice(0, 15).map((skill: any, idx: number) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-primary-100 dark:bg-primary-900 text-primary-800 dark:text-primary-200 rounded-full text-sm"
                        >
                          {skill.name}
                        </span>
                      ))}
                      {uploadResult.processing_result.skills.length > 15 && (
                        <span className="px-3 py-1 text-secondary-500 dark:text-secondary-400 text-sm">
                          +{uploadResult.processing_result.skills.length - 15} more
                        </span>
                      )}
                    </div>
                    
                    <div className="mt-6 flex gap-4">
                      <Button onClick={() => router.push('/recommendations')}>
                        View Recommendations
                      </Button>
                      <Button variant="outline" onClick={() => router.push('/dashboard')}>
                        Go to Dashboard
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-secondary-600 dark:text-secondary-400">
                      No skills were extracted. Please try uploading a different resume.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  )
}
