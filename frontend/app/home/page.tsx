"use client"

import { useEffect, useState, useMemo } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { KPICard } from "@/components/widgets/KPICard"
import { StatusChart } from "@/components/widgets/StatusChart"
import { ApplicationsOverTimeChart } from "@/components/widgets/ApplicationsOverTimeChart"
import { ApplicationsTable } from "@/components/widgets/ApplicationsTable"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Briefcase, FileCheck, Calendar, Gift, Globe, TrendingUp } from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface JobApplication {
  id: string
  user_id: string
  job_title: string
  company: string
  job_posted: string
  job_description: string
  url: string
  required_skills: string[]
  preferred_skills: string[]
  education_requirements: string[]
  experience_requirements: string[]
  keywords: string[]
  job_site_type: string
  open_to_visa_sponsorship: boolean
  status: string
  notes: string | null
  application_date: string
  created_at: string
  updated_at: string
}

function DashboardSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <Skeleton className="h-4 w-24 mb-2" />
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[300px] w-full" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-40" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-[300px] w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function HomePage() {
  const { user } = useAuth()
  const [applications, setApplications] = useState<JobApplication[]>([])
  const [loadingApplications, setLoadingApplications] = useState(true)

  useEffect(() => {
    if (user) {
      fetchApplications()
    }
  }, [user])

  const fetchApplications = async () => {
    try {
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("token="))
        ?.split("=")[1]

      if (!token) {
        setLoadingApplications(false)
        return
      }

      const response = await fetch(`${API_URL}/db/get-all-applications`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setApplications(data)
      }
    } catch (error) {
      console.error("Failed to fetch applications:", error)
    } finally {
      setLoadingApplications(false)
    }
  }

  const stats = useMemo(() => {
    const total = applications.length
    const applied = applications.filter((app) => app.status === "applied").length
    const interviewing = applications.filter(
      (app) => app.status === "interviewing"
    ).length
    const offers = applications.filter((app) => app.status === "offer").length
    const visaSponsorship = applications.filter(
      (app) => app.open_to_visa_sponsorship === true
    ).length

    const statusCounts: Record<string, number> = {}
    applications.forEach((app) => {
      statusCounts[app.status] = (statusCounts[app.status] || 0) + 1
    })

    const statusData = Object.entries(statusCounts).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
    }))

    const timeDataMap: Record<string, { count: number; date: Date }> = {}
    applications.forEach((app) => {
      if (app.application_date) {
        try {
          const date = new Date(app.application_date)
          const monthKey = date.toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
          })
          if (!timeDataMap[monthKey]) {
            timeDataMap[monthKey] = { count: 0, date }
          }
          timeDataMap[monthKey].count += 1
        } catch {
          // Skip invalid dates
        }
      }
    })

    const timeData = Object.entries(timeDataMap)
      .map(([month, data]) => ({ month, applications: data.count, date: data.date }))
      .sort((a, b) => a.date.getTime() - b.date.getTime())
      .map(({ month, applications }) => ({ month, applications }))

    return {
      total,
      applied,
      interviewing,
      offers,
      visaSponsorship,
      statusData,
      timeData,
    }
  }, [applications])

  if (loadingApplications) {
    return <DashboardSkeleton />
  }

  return (
    <div className="p-6 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">
          Welcome back{user?.first_name ? `, ${user.first_name}` : user?.full_name ? `, ${user.full_name}` : ""}
        </h1>
        <p className="text-muted-foreground">
          Track and analyze all your job applications in one place
        </p>
      </div>

      {applications.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="rounded-full bg-muted p-4 mb-4">
              <Briefcase className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">No applications yet</h3>
            <p className="text-muted-foreground max-w-sm">
              Start tracking your job search by adding your first application using
              the browser extension.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <KPICard
              title="Total Applications"
              value={stats.total}
              icon={Briefcase}
            />
            <KPICard
              title="Applied"
              value={stats.applied}
              icon={FileCheck}
            />
            <KPICard
              title="Interviewing"
              value={stats.interviewing}
              icon={Calendar}
            />
            <KPICard
              title="Offers"
              value={stats.offers}
              icon={Gift}
            />
            <KPICard
              title="Visa Sponsorship"
              value={stats.visaSponsorship}
              icon={Globe}
            />
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div>
                  <CardTitle className="text-base font-medium">
                    Application Status
                  </CardTitle>
                  <CardDescription>
                    Distribution of your applications by status
                  </CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <StatusChart data={stats.statusData} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div>
                  <CardTitle className="text-base font-medium">
                    Applications Over Time
                  </CardTitle>
                  <CardDescription>
                    Your application activity by month
                  </CardDescription>
                </div>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <ApplicationsOverTimeChart data={stats.timeData} />
              </CardContent>
            </Card>
          </div>

          <ApplicationsTable applications={applications} />
        </>
      )}
    </div>
  )
}
