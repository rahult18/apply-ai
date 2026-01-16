"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Puzzle, CheckCircle2, AlertCircle, Loader2, ArrowRight } from "lucide-react"

export default function ConnectExtensionPage() {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [error, setError] = useState<string | null>(null)

  const handleAuthenticate = async () => {
    setStatus("loading")
    setError(null)
    try {
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("token="))
        ?.split("=")[1]

      if (!token) {
        throw new Error("Not authenticated")
      }

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/extension/connect/start`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      )
      if (!res.ok) {
        throw new Error("Failed to get one-time code")
      }
      const data = await res.json()
      const code = data.one_time_code

      window.postMessage(
        { type: "APPLYAI_EXTENSION_CONNECT", code },
        window.location.origin
      )
      console.log("Posted message to extension with code:", code)

      setStatus("success")
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error"
      setError(errorMessage)
      setStatus("error")
    }
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] p-6">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Puzzle className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl">Connect Browser Extension</CardTitle>
          <CardDescription>
            Link your browser extension to your ApplyAI account for automatic job
            tracking
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {status === "idle" && (
            <div className="space-y-4">
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>Make sure you have:</p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Installed the ApplyAI browser extension</li>
                  <li>The extension popup is open</li>
                </ul>
              </div>
              <Button onClick={handleAuthenticate} className="w-full" size="lg">
                Connect Extension
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          )}

          {status === "loading" && (
            <div className="flex flex-col items-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
              <p className="text-muted-foreground">Connecting to extension...</p>
            </div>
          )}

          {status === "success" && (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                <CheckCircle2 className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-green-600 mb-2">
                Successfully Connected!
              </h3>
              <p className="text-muted-foreground">
                Your extension is now linked to your account. You can close this
                tab and start tracking jobs.
              </p>
            </div>
          )}

          {status === "error" && (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
                <AlertCircle className="h-8 w-8 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-red-600 mb-2">
                Connection Failed
              </h3>
              <p className="text-muted-foreground mb-4">
                {error || "Something went wrong. Please try again."}
              </p>
              <Button onClick={handleAuthenticate} variant="outline">
                Try Again
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
