"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@/contexts/AuthContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ArrowLeft,
  ExternalLink,
  Building2,
  Calendar,
  Globe,
  CheckCircle2,
  XCircle,
  FileText,
  Sparkles,
  Send,
  Clock
} from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface JobApplication {
  id: string
  job_title: string
  company: string
  status: string
  application_date: string
  job_site_type: string
  open_to_visa_sponsorship: boolean
  url: string
  job_description: string
  required_skills: string[]
  preferred_skills: string[]
}

interface AutofillEvent {
  id: string
  run_id: string
  event_type: string
  payload: Record<string, unknown> | null
  created_at: string
}

const statusColors: Record<string, string> = {
  saved: "bg-slate-100 text-slate-700",
  applied: "bg-blue-100 text-blue-700",
  interviewing: "bg-amber-100 text-amber-700",
  rejected: "bg-red-100 text-red-700",
  offer: "bg-green-100 text-green-700",
  withdrawn: "bg-gray-100 text-gray-700",
}

function timeAgo(dateString: string): string {
  try {
    const diff = Date.now() - new Date(dateString).getTime()
    const mins = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    if (mins < 1) return "just now"
    if (mins < 60) return `${mins}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return new Date(dateString).toLocaleDateString("en-US", { month: "short", day: "numeric" })
  } catch {
    return ""
  }
}

function formatFullDate(dateString: string): string {
  try {
    return new Date(dateString).toLocaleString("en-US", {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit"
    })
  } catch {
    return dateString
  }
}

const eventTypeConfig: Record<string, { icon: typeof FileText; label: string; iconColor: string; ringColor: string; dotColor: string }> = {
  autofill_plan_received: {
    icon: FileText,
    label: "Autofill Plan Generated",
    iconColor: "text-blue-600",
    ringColor: "bg-blue-50 ring-blue-200",
    dotColor: "bg-blue-500"
  },
  autofill_applied: {
    icon: Sparkles,
    label: "Form Autofilled",
    iconColor: "text-violet-600",
    ringColor: "bg-violet-50 ring-violet-200",
    dotColor: "bg-violet-500"
  },
  application_submitted: {
    icon: Send,
    label: "Application Submitted",
    iconColor: "text-emerald-600",
    ringColor: "bg-emerald-50 ring-emerald-200",
    dotColor: "bg-emerald-500"
  }
}

function EventTimeline({ events }: { events: AutofillEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center gap-3">
        <div className="rounded-full bg-muted p-3">
          <Clock className="h-6 w-6 text-muted-foreground" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">No activity yet</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Use the extension to autofill and track this application
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Vertical connector line */}
      <div className="absolute left-[18px] top-3 bottom-3 w-px bg-border" />

      <div className="space-y-1">
        {events.map((event, index) => {
          const config = eventTypeConfig[event.event_type] || {
            icon: Clock,
            label: event.event_type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
            iconColor: "text-gray-500",
            ringColor: "bg-gray-50 ring-gray-200",
            dotColor: "bg-gray-400"
          }
          const Icon = config.icon
          const isLast = index === events.length - 1

          return (
            <div key={event.id} className={`relative flex gap-4 ${isLast ? "pb-0" : "pb-5"}`}>
              {/* Icon badge */}
              <div className={`relative z-10 flex-shrink-0 flex h-9 w-9 items-center justify-center rounded-full ring-2 ${config.ringColor}`}>
                <Icon className={`h-4 w-4 ${config.iconColor}`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pt-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold leading-tight text-foreground">
                    {config.label}
                  </p>
                  <span
                    className="text-xs text-muted-foreground whitespace-nowrap flex-shrink-0 cursor-default"
                    title={formatFullDate(event.created_at)}
                  >
                    {timeAgo(event.created_at)}
                  </span>
                </div>

                {/* Date */}
                <p className="text-xs text-muted-foreground mt-0.5">
                  {formatFullDate(event.created_at)}
                </p>

                {/* Payload pills */}
                {event.payload && Object.keys(event.payload).length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {event.event_type === "autofill_applied" && (
                      <>
                        {event.payload.filled !== undefined && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-200">
                            <CheckCircle2 className="h-3 w-3" />
                            {event.payload.filled as number} filled
                          </span>
                        )}
                        {(event.payload.skipped as number) > 0 && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 ring-1 ring-gray-200">
                            {event.payload.skipped as number} skipped
                          </span>
                        )}
                      </>
                    )}
                    {event.event_type === "autofill_plan_received" && event.payload.field_count !== undefined && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-blue-200">
                        <FileText className="h-3 w-3" />
                        {event.payload.field_count as number} fields planned
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}



function PageSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-64" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-5 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default function ApplicationDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const [application, setApplication] = useState<JobApplication | null>(null)
  const [events, setEvents] = useState<AutofillEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [eventsLoading, setEventsLoading] = useState(true)

  const applicationId = params.id as string

  useEffect(() => {
    if (user && applicationId) {
      fetchApplication()
      fetchEvents()
    }
  }, [user, applicationId])

  const getToken = () => {
    return document.cookie
      .split("; ")
      .find((row) => row.startsWith("token="))
      ?.split("=")[1]
  }

  const fetchApplication = async () => {
    try {
      const token = getToken()
      if (!token) {
        setLoading(false)
        return
      }

      const response = await fetch(`${API_URL}/db/get-all-applications`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        const app = data.find((a: JobApplication) => a.id === applicationId)
        setApplication(app || null)
      }
    } catch (error) {
      console.error("Failed to fetch application:", error)
    } finally {
      setLoading(false)
    }
  }

  const fetchEvents = async () => {
    try {
      const token = getToken()
      if (!token) {
        setEventsLoading(false)
        return
      }

      // Note: This endpoint uses the extension JWT token format
      // For the web app, we may need a different endpoint or token handling
      // For now, we'll try with the web token and handle errors gracefully
      const response = await fetch(`${API_URL}/extension/autofill/events/${applicationId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setEvents(data.events || [])
      }
    } catch (error) {
      console.error("Failed to fetch events:", error)
    } finally {
      setEventsLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return "N/A"
    try {
      return new Date(dateString).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    } catch {
      return dateString
    }
  }

  if (loading) {
    return <PageSkeleton />
  }

  if (!application) {
    return (
      <div className="p-6">
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <h2 className="text-lg font-semibold mb-2">Application not found</h2>
          <p className="text-muted-foreground mb-4">
            The application you&apos;re looking for doesn&apos;t exist or you don&apos;t have access to it.
          </p>
          <Button onClick={() => router.push("/home")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/home")}
          className="mt-1"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold tracking-tight">{application.job_title}</h1>
            <Badge
              variant="secondary"
              className={statusColors[application.status] || statusColors.saved}
            >
              {application.status}
            </Badge>
          </div>
          <div className="flex items-center gap-4 text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Building2 className="h-4 w-4" />
              {application.company}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              {formatDate(application.application_date)}
            </span>
          </div>
        </div>
        <Button variant="outline" asChild>
          <a
            href={application.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            View Posting
          </a>
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Job Details Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Job Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Source</span>
              <span className="text-sm capitalize">{application.job_site_type}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Visa Sponsorship</span>
              <span className="flex items-center gap-1.5">
                {application.open_to_visa_sponsorship ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-green-600">Available</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">Not available</span>
                  </>
                )}
              </span>
            </div>

            {application.required_skills && application.required_skills.length > 0 && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">Required Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {application.required_skills.slice(0, 8).map((skill, i) => (
                    <Badge key={i} variant="outline" className="text-xs">
                      {skill}
                    </Badge>
                  ))}
                  {application.required_skills.length > 8 && (
                    <Badge variant="outline" className="text-xs">
                      +{application.required_skills.length - 8} more
                    </Badge>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Activity Timeline Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Activity Timeline</CardTitle>
            <CardDescription>
              Track your application progress
            </CardDescription>
          </CardHeader>
          <CardContent>
            {eventsLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : (
              <EventTimeline events={events} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
