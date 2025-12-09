"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/AuthContext"
import { Navbar } from "@/components/Navbar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export default function AddToTrackerPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [jobLink, setJobLink] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="min-h-screen flex items-center justify-center">
          <p>Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    router.push("/login")
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSuccess(false)
    setIsLoading(true)

    try {
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("token="))
        ?.split("=")[1]

      if (!token) {
        setError("Not authenticated. Please login again.")
        setIsLoading(false)
        return
      }

      const response = await fetch(
        `${API_URL}/scrape?job_link=${encodeURIComponent(jobLink)}`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to scrape job posting")
      }

      setSuccess(true)
      setJobLink("")
      setTimeout(() => {
        router.push("/home")
      }, 2000)
    } catch (err: any) {
      setError(err.message || "An error occurred while adding the job")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <CardHeader>
            <CardTitle>Add Job to Tracker</CardTitle>
            <CardDescription>
              Enter a job posting URL to automatically extract and track the job details.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="jobLink">Job Posting URL</Label>
                <Input
                  id="jobLink"
                  type="url"
                  placeholder="https://www.linkedin.com/jobs/view/..."
                  value={jobLink}
                  onChange={(e) => setJobLink(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              {error && (
                <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md">
                  {error}
                </div>
              )}

              {success && (
                <div className="p-3 text-sm text-green-600 bg-green-50 rounded-md">
                  Job successfully added to tracker! Redirecting...
                </div>
              )}

              <Button type="submit" disabled={isLoading || !jobLink}>
                {isLoading ? "Adding..." : "Add to Tracker"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}

