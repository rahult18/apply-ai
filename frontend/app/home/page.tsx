"use client"

import { useEffect, useState, useMemo } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/AuthContext"
import { Navbar } from "@/components/Navbar"
import { KPICard } from "@/components/widgets/KPICard"
import { StatusChart } from "@/components/widgets/StatusChart"
import { ApplicationsOverTimeChart } from "@/components/widgets/ApplicationsOverTimeChart"
import { ApplicationsTable } from "@/components/widgets/ApplicationsTable"
import { Briefcase, FileCheck, Calendar, Gift, Globe } from "lucide-react"

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

export default function HomePage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [applications, setApplications] = useState<JobApplication[]>([])
  const [loadingApplications, setLoadingApplications] = useState(true)

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login")
    }
  }, [user, loading, router])

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

  // Calculate statistics - must be before conditional returns (Rules of Hooks)
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

    // Status distribution for chart
    const statusCounts: Record<string, number> = {}
    applications.forEach((app) => {
      statusCounts[app.status] = (statusCounts[app.status] || 0) + 1
    })

    const statusData = Object.entries(statusCounts).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
    }))

    // Applications over time (group by month)
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

  if (loading || loadingApplications) {
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
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold">Job Applications Dashboard</h2>
          <p className="text-muted-foreground">
            Track and analyze all your job applications in one place
          </p>
        </div>

        {applications.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">
              No applications yet. Start tracking by adding your first job
              application.
            </p>
          </div>
        ) : (
          <>
            {/* KPI Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5 mb-6">
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
              <KPICard title="Offers" value={stats.offers} icon={Gift} />
              <KPICard
                title="Visa Sponsorship"
                value={stats.visaSponsorship}
                icon={Globe}
              />
            </div>

            {/* Charts */}
            <div className="grid gap-6 md:grid-cols-2 mb-6">
              <StatusChart data={stats.statusData} />
              <ApplicationsOverTimeChart data={stats.timeData} />
            </div>

            {/* Table */}
            <ApplicationsTable applications={applications} />
          </>
        )}
      </main>
    </div>
  )
}

