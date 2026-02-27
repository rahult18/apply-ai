"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { MapPin, Home, Building2, ExternalLink } from "lucide-react"
import { DiscoveredJob, JobBoardProvider } from "@/types/jobs"

interface JobCardProps {
  job: DiscoveredJob
}

const providerStyles: Record<JobBoardProvider, string> = {
  ashby: "bg-purple-100 text-purple-700 border-purple-200",
  lever: "bg-green-100 text-green-700 border-green-200",
  greenhouse: "bg-orange-100 text-orange-700 border-orange-200",
}

const providerLabels: Record<JobBoardProvider, string> = {
  ashby: "Ashby",
  lever: "Lever",
  greenhouse: "Greenhouse",
}

function formatRelativeDate(dateString: string | null): string {
  if (!dateString) return ""

  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return "Today"
  if (diffDays === 1) return "Yesterday"
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 14) return "1 week ago"
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  if (diffDays < 60) return "1 month ago"
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export function JobCard({ job }: JobCardProps) {
  const handleApply = () => {
    window.open(job.apply_url, "_blank", "noopener,noreferrer")
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-5">
        {/* Header: Provider badge and date */}
        <div className="flex items-center justify-between mb-3">
          <Badge variant="outline" className={providerStyles[job.provider]}>
            {providerLabels[job.provider]}
          </Badge>
          {job.posted_at && (
            <span className="text-xs text-muted-foreground">
              {formatRelativeDate(job.posted_at)}
            </span>
          )}
        </div>

        {/* Title */}
        <h3 className="font-semibold text-base mb-1 line-clamp-2">{job.title}</h3>

        {/* Company */}
        <p className="text-sm text-muted-foreground mb-3">
          {job.company_name || "Unknown Company"}
        </p>

        {/* Location and Remote */}
        <div className="flex flex-wrap items-center gap-2 mb-3 text-sm text-muted-foreground">
          {job.location && (
            <div className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" />
              <span className="line-clamp-1">{job.location}</span>
            </div>
          )}
          {job.is_remote && (
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
              <Home className="h-3 w-3 mr-1" />
              Remote
            </Badge>
          )}
        </div>

        {/* Department */}
        {job.department && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-3">
            <Building2 className="h-3.5 w-3.5" />
            <span>{job.department}</span>
          </div>
        )}

        {/* Description preview */}
        {job.description && (
          <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
            {job.description.replace(/<[^>]*>/g, "").slice(0, 150)}
          </p>
        )}

        {/* Apply button */}
        <div className="flex justify-end">
          <Button size="sm" onClick={handleApply}>
            Apply
            <ExternalLink className="h-3.5 w-3.5 ml-1.5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
