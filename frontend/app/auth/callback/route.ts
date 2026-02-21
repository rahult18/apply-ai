import { NextResponse } from "next/server"
import { createClient } from "@/lib/supabase/server"

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get("code")
  const next = searchParams.get("next") ?? "/home"
  const error = searchParams.get("error")
  const errorDescription = searchParams.get("error_description")

  // Handle OAuth errors
  if (error) {
    console.error("OAuth error:", error, errorDescription)
    return NextResponse.redirect(
      `${origin}/login?error=${encodeURIComponent(errorDescription || error)}`
    )
  }

  if (code) {
    const supabase = await createClient()

    const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)

    if (exchangeError) {
      console.error("Session exchange error:", exchangeError)
      return NextResponse.redirect(
        `${origin}/login?error=${encodeURIComponent(exchangeError.message)}`
      )
    }

    if (data.session) {
      // Store the access token in a cookie for your existing backend auth flow
      const response = NextResponse.redirect(`${origin}${next}`)

      // Set the Supabase access token as your app's token cookie
      response.cookies.set("token", data.session.access_token, {
        path: "/",
        maxAge: 86400, // 24 hours
        httpOnly: false,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax",
      })

      return response
    }
  }

  // No code present, redirect to login
  return NextResponse.redirect(`${origin}/login?error=no_code`)
}
