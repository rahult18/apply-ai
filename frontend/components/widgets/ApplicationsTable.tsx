"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, XCircle, ExternalLink } from "lucide-react"

interface JobApplication {
  id: string
  job_title: string
  company: string
  status: string
  application_date: string
  job_site_type: string
  open_to_visa_sponsorship: boolean
  url: string
}

interface ApplicationsTableProps {
  applications: JobApplication[]
}

export function ApplicationsTable({ applications }: ApplicationsTableProps) {
  const getStatusVariant = (
    status: string
  ): "saved" | "applied" | "interviewing" | "rejected" | "offer" | "withdrawn" => {
    return status as
      | "saved"
      | "applied"
      | "interviewing"
      | "rejected"
      | "offer"
      | "withdrawn"
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return "N/A"
    try {
      return new Date(dateString).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    } catch {
      return dateString
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>All Applications</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left p-4 font-semibold">Job Title</th>
                <th className="text-left p-4 font-semibold">Company</th>
                <th className="text-left p-4 font-semibold">Status</th>
                <th className="text-left p-4 font-semibold">Application Date</th>
                <th className="text-left p-4 font-semibold">Source</th>
                <th className="text-left p-4 font-semibold">Visa Sponsorship</th>
                <th className="text-left p-4 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {applications.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-muted-foreground">
                    No applications found
                  </td>
                </tr>
              ) : (
                applications.map((app) => (
                  <tr key={app.id} className="border-b hover:bg-muted/50">
                    <td className="p-4 font-medium">{app.job_title}</td>
                    <td className="p-4">{app.company}</td>
                    <td className="p-4">
                      <Badge variant={getStatusVariant(app.status)}>
                        {app.status}
                      </Badge>
                    </td>
                    <td className="p-4 text-muted-foreground">
                      {formatDate(app.application_date)}
                    </td>
                    <td className="p-4">
                      <span className="capitalize">{app.job_site_type}</span>
                    </td>
                    <td className="p-4">
                      {app.open_to_visa_sponsorship ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-gray-400" />
                      )}
                    </td>
                    <td className="p-4">
                      <a
                        href={app.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                      >
                        <ExternalLink className="h-4 w-4" />
                        View
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

