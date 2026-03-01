"use client"

import { createContext, useContext, useState, useEffect, useRef, ReactNode } from "react"
import { useRouter } from "next/navigation"
import { createClient } from "@/lib/supabase/client"

interface User {
  email: string
  id: string
  first_name?: string | null
  full_name?: string | null
  avatar_url?: string | null
}

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

interface AuthContextType {
  user: User | null
  loading: boolean
  applications: JobApplication[]
  loadingApplications: boolean
  applicationsError: boolean
  refetchApplications: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  loginWithGoogle: () => Promise<void>
  signupWithGoogle: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const supabase = createClient()

const FETCH_TIMEOUT_MS = 10000

async function fetchWithTimeout(url: string, options: RequestInit): Promise<Response> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    clearTimeout(id)
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [applications, setApplications] = useState<JobApplication[]>([])
  const [loadingApplications, setLoadingApplications] = useState(true)
  const [applicationsError, setApplicationsError] = useState(false)
  const router = useRouter()
  const authCheckStarted = useRef(false)

  useEffect(() => {
    // Guard against React StrictMode double-invoking this effect,
    // which would fire two concurrent requests to the backend.
    if (authCheckStarted.current) return
    authCheckStarted.current = true
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("token="))
        ?.split("=")[1]

      if (!token) {
        setLoading(false)
        setLoadingApplications(false)
        return
      }

      const headers = { Authorization: `Bearer ${token}` }

      // Fetch auth + applications in parallel — allSettled so one failure doesn't block the other
      const [authResult, appsResult] = await Promise.allSettled([
        fetchWithTimeout(`${API_URL}/auth/me`, { headers }),
        fetchWithTimeout(`${API_URL}/db/get-all-applications`, { headers }),
      ])

      if (authResult.status === "fulfilled" && authResult.value.ok) {
        const data = await authResult.value.json()
        setUser(data)
      } else {
        document.cookie = "token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"
      }

      if (appsResult.status === "fulfilled" && appsResult.value.ok) {
        const data = await appsResult.value.json()
        setApplications(data)
      } else {
        setApplicationsError(true)
      }
    } catch (error) {
      console.error("Auth check failed:", error)
    } finally {
      setLoading(false)
      setLoadingApplications(false)
    }
  }

  const refetchApplications = async () => {
    setLoadingApplications(true)
    setApplicationsError(false)
    try {
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("token="))
        ?.split("=")[1]

      if (!token) return

      const response = await fetchWithTimeout(`${API_URL}/db/get-all-applications`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        const data = await response.json()
        setApplications(data)
      } else {
        setApplicationsError(true)
      }
    } catch (error) {
      console.error("Failed to fetch applications:", error)
      setApplicationsError(true)
    } finally {
      setLoadingApplications(false)
    }
  }

  const login = async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        'email': email, 
        'password': password 
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Login failed")
    }

    const data = await response.json()
    document.cookie = `token=${data.token}; path=/; max-age=86400`
    setUser(data.user)
    router.push("/home")
  }

  const signup = async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        'email': email, 
        'password': password 
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || "Signup failed")
    }

    const data = await response.json()
    document.cookie = `token=${data.token}; path=/; max-age=86400`
    setUser(data.user)
    router.push("/home")
  }

  const loginWithGoogle = async () => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })

    if (error) {
      throw new Error(error.message)
    }

    if (data.url) {
      window.location.href = data.url
    }
  }

  const signupWithGoogle = async () => {
    // Google OAuth handles both login and signup
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })

    if (error) {
      throw new Error(error.message)
    }

    if (data.url) {
      window.location.href = data.url
    }
  }

  const logout = async () => {
    document.cookie = "token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"
    setUser(null)
    router.push("/login")
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        applications,
        loadingApplications,
        applicationsError,
        refetchApplications,
        login,
        signup,
        loginWithGoogle,
        signupWithGoogle,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

