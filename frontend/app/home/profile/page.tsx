"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/AuthContext"
import { Navbar } from "@/components/Navbar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

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
    summary?: string;
    skills?: string[];
    experience?: {
      company: string;
      position: string;
      start_date?: string;
      end_date?: string;
      description?: string;
    }[];
    education?: {
      institution: string;
      degree: string;
      field_of_study: string;
      start_date?: string;
      end_date?: string;
      description?: string;
    }[];
    certifications?: {
      name: string;
      issuing_organization?: string;
      issue_date?: string;
      expiration_date?: string;
      credential_id?: string;
      credential_url?: string;
    }[];
    projects?: {
      name: string;
      description?: string;
      link?: string;
    }[];
  };
  resume_parsed_at?: string;
  resume_parse_status?: 'PENDING' | 'COMPLETED' | 'FAILED';
}

export default function ProfilePage() {
  const { user, loading } = useAuth()
  const router = useRouter()
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
    if (!loading && !user) {
      router.push("/login")
    }
  }, [user, loading, router])

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

        // Update parsing status
        if (data.resume_parse_status === 'PENDING') {
            setIsParsingResume(true);
            // If still pending, try to re-fetch after a delay
            if (retryCount < 2) { // Limit retries to prevent infinite loops
                setTimeout(() => {
                    setRetryCount(prev => prev + 1);
                    fetchProfile();
                }, 30000); // 30 seconds
            } else {
                console.warn("Resume parsing still pending after multiple retries.");
            }
        } else {
            setIsParsingResume(false);
            setRetryCount(0); // Reset retry count on completion or failure
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

      // Add all form fields
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
        const locations = desiredLocationInput.split(",").map(loc => loc.trim()).filter(loc => loc)
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
      // If a resume was uploaded, start monitoring its parsing status
      if (resumeFile) {
          setIsParsingResume(true);
          setRetryCount(0); // Reset retry count for a new upload
          // Initiate first fetch after a short delay
          setTimeout(() => {
              fetchProfile();
          }, 5000); // 5 seconds initial delay before first check
      } else {
          fetchProfile();
      }
    } catch (err: any) {
      setError(err.message || "An error occurred while updating profile")
    } finally {
      setSaving(false)
    }
  }

  if (loading || loadingProfile) {
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
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <CardHeader>
            <CardTitle>Profile Settings</CardTitle>
            <CardDescription>Update your profile information</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md">
                  {error}
                </div>
              )}
              {success && (
                <div className="p-3 bg-green-50 border border-green-200 text-green-700 rounded-md">
                  Profile updated successfully!
                </div>
              )}

              {/* Personal Information */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Personal Information</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="full_name">Full Name</Label>
                    <Input
                      id="full_name"
                      value={profile.full_name || ""}
                      onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={profile.email || ""}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="first_name">First Name</Label>
                    <Input
                      id="first_name"
                      value={profile.first_name || ""}
                      onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="last_name">Last Name</Label>
                    <Input
                      id="last_name"
                      value={profile.last_name || ""}
                      onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="phone_number">Phone Number</Label>
                    <Input
                      id="phone_number"
                      type="tel"
                      value={profile.phone_number || ""}
                      onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              {/* Links */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Links</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="linkedin_url">LinkedIn URL</Label>
                    <Input
                      id="linkedin_url"
                      type="url"
                      value={profile.linkedin_url || ""}
                      onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="github_url">GitHub URL</Label>
                    <Input
                      id="github_url"
                      type="url"
                      value={profile.github_url || ""}
                      onChange={(e) => setProfile({ ...profile, github_url: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="portfolio_url">Portfolio URL</Label>
                    <Input
                      id="portfolio_url"
                      type="url"
                      value={profile.portfolio_url || ""}
                      onChange={(e) => setProfile({ ...profile, portfolio_url: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="other_url">Other URL</Label>
                    <Input
                      id="other_url"
                      type="url"
                      value={profile.other_url || ""}
                      onChange={(e) => setProfile({ ...profile, other_url: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              {/* Address */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Address</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="md:col-span-2">
                    <Label htmlFor="address">Street Address</Label>
                    <Input
                      id="address"
                      value={profile.address || ""}
                      onChange={(e) => setProfile({ ...profile, address: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="city">City</Label>
                    <Input
                      id="city"
                      value={profile.city || ""}
                      onChange={(e) => setProfile({ ...profile, city: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="state">State</Label>
                    <Input
                      id="state"
                      value={profile.state || ""}
                      onChange={(e) => setProfile({ ...profile, state: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="zip_code">Zip Code</Label>
                    <Input
                      id="zip_code"
                      value={profile.zip_code || ""}
                      onChange={(e) => setProfile({ ...profile, zip_code: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="country">Country</Label>
                    <Input
                      id="country"
                      value={profile.country || ""}
                      onChange={(e) => setProfile({ ...profile, country: e.target.value })}
                    />
                  </div>
                </div>
              </div>

              {/* Work Authorization */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Work Authorization</h3>
                <div className="space-y-4">
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
                    <div>
                      <Label htmlFor="visa_sponsorship_type">Visa Sponsorship Type</Label>
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
                </div>
              </div>

              {/* Job Preferences */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Job Preferences</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <Label htmlFor="desired_salary">Desired Salary</Label>
                    <Input
                      id="desired_salary"
                      type="number"
                      value={profile.desired_salary || ""}
                      onChange={(e) =>
                        setProfile({ ...profile, desired_salary: parseFloat(e.target.value) || undefined })
                      }
                    />
                  </div>
                  <div>
                    <Label htmlFor="desired_location">Desired Locations (comma-separated)</Label>
                    <Input
                      id="desired_location"
                      value={desiredLocationInput}
                      onChange={(e) => setDesiredLocationInput(e.target.value)}
                      placeholder="e.g., San Francisco, New York, Remote"
                    />
                  </div>
                </div>
              </div>

              {/* Resume */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Resume</h3>
                {profile.resume_url && (
                  <div className="p-4 bg-gray-50 rounded-md border">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">Current Resume</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {profile.resume?.split('/').pop() || 'Resume file'}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => window.open(profile.resume_url, '_blank')}
                        >
                          View
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const link = document.createElement('a')
                            link.href = profile.resume_url!
                            link.download = profile.resume?.split('/').pop() || 'resume.pdf'
                            link.click()
                          }}
                        >
                          Download
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
                <div>
                  <Label htmlFor="resume">
                    {profile.resume_url ? 'Upload New Resume' : 'Upload Resume'}
                  </Label>
                  <Input
                    id="resume"
                    type="file"
                    accept=".pdf,.doc,.docx"
                    onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Accepted formats: PDF, DOC, DOCX
                  </p>
                </div>
              </div>

              {/* Resume Parsing Status */}
              {(profile.resume || isParsingResume) && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Resume Parsing Status</h3>
                  {
                    profile.resume_parse_status === 'PENDING' && isParsingResume && (
                      <div className="p-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-md">
                        Resume parsing in progress... This may take a moment.
                      </div>
                    )
                  }
                  {
                    profile.resume_parse_status === 'COMPLETED' && !isParsingResume && profile.resume_parsed_at && (
                      <div className="p-3 bg-green-50 border border-green-200 text-green-700 rounded-md">
                        Resume parsed successfully on {new Date(profile.resume_parsed_at).toLocaleDateString()}.
                      </div>
                    )
                  }
                  {
                    profile.resume_parse_status === 'FAILED' && !isParsingResume && (
                      <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md">
                        Failed to parse resume. Please try uploading again.
                      </div>
                    )
                  }
                </div>
              )}

              {/* Parsed Resume Data */}
              {profile.resume_profile && !isParsingResume && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Parsed Resume Data</h3>
                  <div className="grid gap-4">
                    {profile.resume_profile.summary && (
                      <div>
                        <Label>Summary</Label>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                          {profile.resume_profile.summary}
                        </p>
                      </div>
                    )}
                    {profile.resume_profile.skills && profile.resume_profile.skills.length > 0 && (
                      <div>
                        <Label>Skills</Label>
                        <p className="text-sm text-muted-foreground">
                          {profile.resume_profile.skills.join(", ")}
                        </p>
                      </div>
                    )}
                    {profile.resume_profile.experience && profile.resume_profile.experience.length > 0 && (
                      <div>
                        <Label>Experience</Label>
                        <div className="space-y-2">
                          {profile.resume_profile.experience.map((exp, index) => (
                            <Card key={index} className="p-3">
                              <p className="font-medium">{exp.position} at {exp.company}</p>
                              <p className="text-xs text-muted-foreground">
                                {exp.start_date} - {exp.end_date || "Present"}
                              </p>
                              {exp.description && (
                                <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
                                  {exp.description}
                                </p>
                              )}
                            </Card>
                          ))}
                        </div>
                      </div>
                    )}
                    {profile.resume_profile.education && profile.resume_profile.education.length > 0 && (
                      <div>
                        <Label>Education</Label>
                        <div className="space-y-2">
                          {profile.resume_profile.education.map((edu, index) => (
                            <Card key={index} className="p-3">
                              <p className="font-medium">{edu.degree} in {edu.field_of_study}</p>
                              <p className="text-xs text-muted-foreground">{edu.institution}</p>
                              <p className="text-xs text-muted-foreground">
                                {edu.start_date} - {edu.end_date || "Present"}
                              </p>
                              {edu.description && (
                                <p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap">
                                  {edu.description}
                                </p>
                              )}
                            </Card>
                          ))}
                        </div>
                      </div>
                    )}
                    {profile.resume_profile.projects && profile.resume_profile.projects.length > 0 && (
                      <div>
                        <Label>Projects</Label>
                        <div className="space-y-2">
                          {profile.resume_profile.projects.map((proj, index) => (
                            <Card key={index} className="p-3">
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
                                  className="text-sm text-blue-600 hover:underline mt-1 block"
                                >
                                  {proj.link}
                                </a>
                              )}
                            </Card>
                          ))}
                        </div>
                      </div>
                    )}
                    {profile.resume_profile.certifications && profile.resume_profile.certifications.length > 0 && (
                      <div>
                        <Label>Certifications</Label>
                        <div className="space-y-2">
                          {profile.resume_profile.certifications.map((cert, index) => (
                            <Card key={index} className="p-3">
                              <p className="font-medium">{cert.name}</p>
                              {cert.issuing_organization && (
                                <p className="text-xs text-muted-foreground">{cert.issuing_organization}</p>
                              )}
                              <p className="text-xs text-muted-foreground">
                                {cert.issue_date}
                                {cert.expiration_date ? ` - ${cert.expiration_date}` : ""}
                              </p>
                              {cert.credential_url && (
                                <a
                                  href={cert.credential_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-blue-600 hover:underline mt-1 block"
                                >
                                  View Credential
                                </a>
                              )}
                            </Card>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Demographic Information (Optional) */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Demographic Information (Optional)</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
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
                  <div>
                    <Label htmlFor="race">Race</Label>
                    <Select
                      value={profile.race || ""}
                      onValueChange={(value) => setProfile({ ...profile, race: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select race" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="American Indian or Alaska Native">American Indian or Alaska Native</SelectItem>
                        <SelectItem value="Asian">Asian</SelectItem>
                        <SelectItem value="Black or African American">Black or African American</SelectItem>
                        <SelectItem value="Hispanic or Latino">Hispanic or Latino</SelectItem>
                        <SelectItem value="Native Hawaiian or Other Pacific Islander">Native Hawaiian or Other Pacific Islander</SelectItem>
                        <SelectItem value="White">White</SelectItem>
                        <SelectItem value="Prefer not to say">Prefer not to say</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="veteran_status">Veteran Status</Label>
                    <Select
                      value={profile.veteran_status || ""}
                      onValueChange={(value) => setProfile({ ...profile, veteran_status: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select veteran status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Yes">Yes</SelectItem>
                        <SelectItem value="No">No</SelectItem>
                        <SelectItem value="Prefer not to say">Prefer not to say</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="disability_status">Disability Status</Label>
                    <Select
                      value={profile.disability_status || ""}
                      onValueChange={(value) => setProfile({ ...profile, disability_status: value })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select disability status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Yes">Yes</SelectItem>
                        <SelectItem value="No">No</SelectItem>
                        <SelectItem value="Prefer not to say">Prefer not to say</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-4">
                <Button type="button" variant="outline" onClick={() => router.back()}>
                  Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}

