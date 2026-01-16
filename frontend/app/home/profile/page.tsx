"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@/contexts/AuthContext"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  User,
  Link as LinkIcon,
  MapPin,
  Briefcase,
  FileText,
  Users,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Eye,
  Download,
  ExternalLink,
} from "lucide-react"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface UserProfile {
  full_name?: string
  first_name?: string
  last_name?: string
  email?: string
  phone_number?: string
  linkedin_url?: string
  github_url?: string
  portfolio_url?: string
  other_url?: string
  address?: string
  city?: string
  state?: string
  zip_code?: string
  country?: string
  authorized_to_work_in_us?: boolean
  visa_sponsorship?: boolean
  visa_sponsorship_type?: string
  desired_salary?: number
  desired_location?: string[]
  gender?: string
  race?: string
  veteran_status?: string
  disability_status?: string
  resume?: string
  resume_url?: string
  resume_text?: string
  resume_profile?: {
    summary?: string
    skills?: string[]
    experience?: {
      company: string
      position: string
      start_date?: string
      end_date?: string
      description?: string
    }[]
    education?: {
      institution: string
      degree: string
      field_of_study: string
      start_date?: string
      end_date?: string
      description?: string
    }[]
    certifications?: {
      name: string
      issuing_organization?: string
      issue_date?: string
      expiration_date?: string
      credential_id?: string
      credential_url?: string
    }[]
    projects?: {
      name: string
      description?: string
      link?: string
    }[]
  }
  resume_parsed_at?: string
  resume_parse_status?: "PENDING" | "COMPLETED" | "FAILED"
}

function ProfileSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64" />
      </div>
      <Skeleton className="h-10 w-full max-w-md" />
      <div className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ProfilePage() {
  const { user } = useAuth()
  const [profile, setProfile] = useState<UserProfile>({})
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState(false)
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [desiredLocationInput, setDesiredLocationInput] = useState("")
  const [isParsingResume, setIsParsingResume] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    if (user) {
      fetchProfile()
    }
  }, [user])

  const fetchProfile = async () => {
    try {
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("token="))
        ?.split("=")[1]

      if (!token) {
        setLoadingProfile(false)
        return
      }

      const response = await fetch(`${API_URL}/db/get-profile`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setProfile(data)
        if (data.desired_location && Array.isArray(data.desired_location)) {
          setDesiredLocationInput(data.desired_location.join(", "))
        }

        if (data.resume_parse_status === "PENDING") {
          setIsParsingResume(true)
          if (retryCount < 2) {
            setTimeout(() => {
              setRetryCount((prev) => prev + 1)
              fetchProfile()
            }, 30000)
          }
        } else {
          setIsParsingResume(false)
          setRetryCount(0)
        }
      }
    } catch (error) {
      console.error("Failed to fetch profile:", error)
    } finally {
      setLoadingProfile(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setSuccess(false)
    setSaving(true)

    try {
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("token="))
        ?.split("=")[1]

      if (!token) {
        setError("Not authenticated. Please login again.")
        setSaving(false)
        return
      }

      const formData = new FormData()

      if (profile.full_name) formData.append("full_name", profile.full_name)
      if (profile.first_name) formData.append("first_name", profile.first_name)
      if (profile.last_name) formData.append("last_name", profile.last_name)
      if (profile.email) formData.append("email", profile.email)
      if (profile.phone_number) formData.append("phone_number", profile.phone_number)
      if (profile.linkedin_url) formData.append("linkedin_url", profile.linkedin_url)
      if (profile.github_url) formData.append("github_url", profile.github_url)
      if (profile.portfolio_url) formData.append("portfolio_url", profile.portfolio_url)
      if (profile.other_url) formData.append("other_url", profile.other_url)
      if (profile.address) formData.append("address", profile.address)
      if (profile.city) formData.append("city", profile.city)
      if (profile.state) formData.append("state", profile.state)
      if (profile.zip_code) formData.append("zip_code", profile.zip_code)
      if (profile.country) formData.append("country", profile.country)
      if (profile.authorized_to_work_in_us !== undefined) {
        formData.append("authorized_to_work_in_us", String(profile.authorized_to_work_in_us))
      }
      if (profile.visa_sponsorship !== undefined) {
        formData.append("visa_sponsorship", String(profile.visa_sponsorship))
      }
      if (profile.visa_sponsorship_type) {
        formData.append("visa_sponsorship_type", profile.visa_sponsorship_type)
      }
      if (profile.desired_salary) {
        formData.append("desired_salary", String(profile.desired_salary))
      }
      if (desiredLocationInput) {
        const locations = desiredLocationInput
          .split(",")
          .map((loc) => loc.trim())
          .filter((loc) => loc)
        formData.append("desired_location", JSON.stringify(locations))
      }
      if (profile.gender) formData.append("gender", profile.gender)
      if (profile.race) formData.append("race", profile.race)
      if (profile.veteran_status) formData.append("veteran_status", profile.veteran_status)
      if (profile.disability_status) formData.append("disability_status", profile.disability_status)
      if (resumeFile) formData.append("resume", resumeFile)

      const response = await fetch(`${API_URL}/db/update-profile`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to update profile")
      }

      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
      if (resumeFile) {
        setIsParsingResume(true)
        setRetryCount(0)
        setTimeout(() => {
          fetchProfile()
        }, 5000)
      } else {
        fetchProfile()
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "An error occurred while updating profile"
      setError(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  if (loadingProfile) {
    return <ProfileSkeleton />
  }

  return (
    <div className="p-6 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Profile Settings</h1>
        <p className="text-muted-foreground">
          Manage your account information and preferences
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-green-50 text-green-700">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Profile updated successfully!
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <Tabs defaultValue="personal" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 lg:grid-cols-6 h-auto gap-2 bg-transparent p-0">
            <TabsTrigger
              value="personal"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              <User className="mr-2 h-4 w-4" />
              Personal
            </TabsTrigger>
            <TabsTrigger
              value="links"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              <LinkIcon className="mr-2 h-4 w-4" />
              Links
            </TabsTrigger>
            <TabsTrigger
              value="location"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              <MapPin className="mr-2 h-4 w-4" />
              Location
            </TabsTrigger>
            <TabsTrigger
              value="work"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              <Briefcase className="mr-2 h-4 w-4" />
              Work
            </TabsTrigger>
            <TabsTrigger
              value="resume"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              <FileText className="mr-2 h-4 w-4" />
              Resume
            </TabsTrigger>
            <TabsTrigger
              value="demographic"
              className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
            >
              <Users className="mr-2 h-4 w-4" />
              Demographics
            </TabsTrigger>
          </TabsList>

          <TabsContent value="personal" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Personal Information</CardTitle>
                <CardDescription>
                  Your basic profile information used for job applications
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="full_name">Full Name</Label>
                    <Input
                      id="full_name"
                      value={profile.full_name || ""}
                      onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={profile.email || ""}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="first_name">First Name</Label>
                    <Input
                      id="first_name"
                      value={profile.first_name || ""}
                      onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Last Name</Label>
                    <Input
                      id="last_name"
                      value={profile.last_name || ""}
                      onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone_number">Phone Number</Label>
                    <Input
                      id="phone_number"
                      type="tel"
                      value={profile.phone_number || ""}
                      onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="links" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Profile Links</CardTitle>
                <CardDescription>
                  Links to your professional profiles and portfolio
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="linkedin_url">LinkedIn URL</Label>
                    <Input
                      id="linkedin_url"
                      type="url"
                      placeholder="https://linkedin.com/in/..."
                      value={profile.linkedin_url || ""}
                      onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="github_url">GitHub URL</Label>
                    <Input
                      id="github_url"
                      type="url"
                      placeholder="https://github.com/..."
                      value={profile.github_url || ""}
                      onChange={(e) => setProfile({ ...profile, github_url: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="portfolio_url">Portfolio URL</Label>
                    <Input
                      id="portfolio_url"
                      type="url"
                      placeholder="https://..."
                      value={profile.portfolio_url || ""}
                      onChange={(e) => setProfile({ ...profile, portfolio_url: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="other_url">Other URL</Label>
                    <Input
                      id="other_url"
                      type="url"
                      placeholder="https://..."
                      value={profile.other_url || ""}
                      onChange={(e) => setProfile({ ...profile, other_url: e.target.value })}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="location" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Address</CardTitle>
                <CardDescription>Your current address information</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="md:col-span-2 space-y-2">
                    <Label htmlFor="address">Street Address</Label>
                    <Input
                      id="address"
                      value={profile.address || ""}
                      onChange={(e) => setProfile({ ...profile, address: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="city">City</Label>
                    <Input
                      id="city"
                      value={profile.city || ""}
                      onChange={(e) => setProfile({ ...profile, city: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="state">State</Label>
                    <Input
                      id="state"
                      value={profile.state || ""}
                      onChange={(e) => setProfile({ ...profile, state: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="zip_code">Zip Code</Label>
                    <Input
                      id="zip_code"
                      value={profile.zip_code || ""}
                      onChange={(e) => setProfile({ ...profile, zip_code: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="country">Country</Label>
                    <Input
                      id="country"
                      value={profile.country || ""}
                      onChange={(e) => setProfile({ ...profile, country: e.target.value })}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="work" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Work Authorization</CardTitle>
                <CardDescription>
                  Your work authorization status in the United States
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="authorized_to_work_in_us"
                    checked={profile.authorized_to_work_in_us || false}
                    onCheckedChange={(checked) =>
                      setProfile({ ...profile, authorized_to_work_in_us: checked as boolean })
                    }
                  />
                  <Label htmlFor="authorized_to_work_in_us">Authorized to work in US</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="visa_sponsorship"
                    checked={profile.visa_sponsorship || false}
                    onCheckedChange={(checked) =>
                      setProfile({ ...profile, visa_sponsorship: checked as boolean })
                    }
                  />
                  <Label htmlFor="visa_sponsorship">Need visa sponsorship</Label>
                </div>
                {profile.visa_sponsorship && (
                  <div className="space-y-2 max-w-xs">
                    <Label htmlFor="visa_sponsorship_type">Visa Type</Label>
                    <Select
                      value={profile.visa_sponsorship_type || ""}
                      onValueChange={(value) =>
                        setProfile({ ...profile, visa_sponsorship_type: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select visa type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="H1B">H1B</SelectItem>
                        <SelectItem value="OPT">OPT</SelectItem>
                        <SelectItem value="F1">F1</SelectItem>
                        <SelectItem value="J1">J1</SelectItem>
                        <SelectItem value="L1">L1</SelectItem>
                        <SelectItem value="O1">O1</SelectItem>
                        <SelectItem value="Other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Job Preferences</CardTitle>
                <CardDescription>
                  Your desired compensation and location preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="desired_salary">Desired Salary (USD)</Label>
                    <Input
                      id="desired_salary"
                      type="number"
                      placeholder="e.g., 100000"
                      value={profile.desired_salary || ""}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          desired_salary: parseFloat(e.target.value) || undefined,
                        })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="desired_location">Desired Locations</Label>
                    <Input
                      id="desired_location"
                      value={desiredLocationInput}
                      onChange={(e) => setDesiredLocationInput(e.target.value)}
                      placeholder="e.g., San Francisco, New York, Remote"
                    />
                    <p className="text-xs text-muted-foreground">Comma-separated list</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="resume" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Resume</CardTitle>
                <CardDescription>
                  Upload your resume for automatic parsing and application auto-fill
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {profile.resume_url && (
                  <div className="flex items-center justify-between p-4 rounded-lg border bg-muted/50">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <FileText className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">Current Resume</p>
                        <p className="text-sm text-muted-foreground">
                          {profile.resume?.split("/").pop() || "Resume file"}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => window.open(profile.resume_url, "_blank")}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        View
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const link = document.createElement("a")
                          link.href = profile.resume_url!
                          link.download = profile.resume?.split("/").pop() || "resume.pdf"
                          link.click()
                        }}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download
                      </Button>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="resume">
                    {profile.resume_url ? "Upload New Resume" : "Upload Resume"}
                  </Label>
                  <div className="flex items-center gap-4">
                    <Input
                      id="resume"
                      type="file"
                      accept=".pdf,.doc,.docx"
                      onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                      className="flex-1"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Accepted formats: PDF, DOC, DOCX
                  </p>
                </div>

                {(profile.resume || isParsingResume) && (
                  <div className="space-y-2">
                    <Label>Parsing Status</Label>
                    {profile.resume_parse_status === "PENDING" && isParsingResume && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 text-blue-700">
                        <Clock className="h-4 w-4 animate-pulse" />
                        Resume parsing in progress...
                      </div>
                    )}
                    {profile.resume_parse_status === "COMPLETED" && !isParsingResume && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 text-green-700">
                        <CheckCircle2 className="h-4 w-4" />
                        Resume parsed successfully
                        {profile.resume_parsed_at &&
                          ` on ${new Date(profile.resume_parsed_at).toLocaleDateString()}`}
                      </div>
                    )}
                    {profile.resume_parse_status === "FAILED" && !isParsingResume && (
                      <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 text-red-700">
                        <AlertCircle className="h-4 w-4" />
                        Failed to parse resume. Please try uploading again.
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {profile.resume_profile && !isParsingResume && (
              <Card>
                <CardHeader>
                  <CardTitle>Parsed Resume Data</CardTitle>
                  <CardDescription>
                    Information extracted from your resume
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {profile.resume_profile.summary && (
                    <div className="space-y-2">
                      <Label>Summary</Label>
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                        {profile.resume_profile.summary}
                      </p>
                    </div>
                  )}

                  {profile.resume_profile.skills && profile.resume_profile.skills.length > 0 && (
                    <div className="space-y-2">
                      <Label>Skills</Label>
                      <div className="flex flex-wrap gap-2">
                        {profile.resume_profile.skills.map((skill, index) => (
                          <Badge key={index} variant="secondary">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {profile.resume_profile.experience &&
                    profile.resume_profile.experience.length > 0 && (
                      <div className="space-y-3">
                        <Label>Experience</Label>
                        <div className="space-y-3">
                          {profile.resume_profile.experience.map((exp, index) => (
                            <div key={index} className="p-4 rounded-lg border">
                              <p className="font-medium">
                                {exp.position} at {exp.company}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {exp.start_date} - {exp.end_date || "Present"}
                              </p>
                              {exp.description && (
                                <p className="text-sm text-muted-foreground mt-2 whitespace-pre-wrap">
                                  {exp.description}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  {profile.resume_profile.education &&
                    profile.resume_profile.education.length > 0 && (
                      <div className="space-y-3">
                        <Label>Education</Label>
                        <div className="space-y-3">
                          {profile.resume_profile.education.map((edu, index) => (
                            <div key={index} className="p-4 rounded-lg border">
                              <p className="font-medium">
                                {edu.degree} in {edu.field_of_study}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {edu.institution}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {edu.start_date} - {edu.end_date || "Present"}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                  {profile.resume_profile.projects &&
                    profile.resume_profile.projects.length > 0 && (
                      <div className="space-y-3">
                        <Label>Projects</Label>
                        <div className="space-y-3">
                          {profile.resume_profile.projects.map((proj, index) => (
                            <div key={index} className="p-4 rounded-lg border">
                              <p className="font-medium">{proj.name}</p>
                              {proj.description && (
                                <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
                                  {proj.description}
                                </p>
                              )}
                              {proj.link && (
                                <a
                                  href={proj.link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-primary hover:underline mt-2 inline-flex items-center gap-1"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                  View Project
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="demographic" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Demographic Information</CardTitle>
                <CardDescription>
                  Optional information for diversity reporting. This information is kept
                  confidential.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="gender">Gender</Label>
                    <Select
                      value={profile.gender || ""}
                      onValueChange={(value) => setProfile({ ...profile, gender: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select gender" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Male">Male</SelectItem>
                        <SelectItem value="Female">Female</SelectItem>
                        <SelectItem value="Non-binary">Non-binary</SelectItem>
                        <SelectItem value="Prefer not to say">Prefer not to say</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="race">Race/Ethnicity</Label>
                    <Select
                      value={profile.race || ""}
                      onValueChange={(value) => setProfile({ ...profile, race: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select race" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="American Indian or Alaska Native">
                          American Indian or Alaska Native
                        </SelectItem>
                        <SelectItem value="Asian">Asian</SelectItem>
                        <SelectItem value="Black or African American">
                          Black or African American
                        </SelectItem>
                        <SelectItem value="Hispanic or Latino">Hispanic or Latino</SelectItem>
                        <SelectItem value="Native Hawaiian or Other Pacific Islander">
                          Native Hawaiian or Other Pacific Islander
                        </SelectItem>
                        <SelectItem value="White">White</SelectItem>
                        <SelectItem value="Prefer not to say">Prefer not to say</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="veteran_status">Veteran Status</Label>
                    <Select
                      value={profile.veteran_status || ""}
                      onValueChange={(value) =>
                        setProfile({ ...profile, veteran_status: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Yes">Yes</SelectItem>
                        <SelectItem value="No">No</SelectItem>
                        <SelectItem value="Prefer not to say">Prefer not to say</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="disability_status">Disability Status</Label>
                    <Select
                      value={profile.disability_status || ""}
                      onValueChange={(value) =>
                        setProfile({ ...profile, disability_status: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Yes">Yes</SelectItem>
                        <SelectItem value="No">No</SelectItem>
                        <SelectItem value="Prefer not to say">Prefer not to say</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <Separator className="my-6" />

        <div className="flex justify-end gap-4">
          <Button type="submit" disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save Changes"
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
