"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";

export default function ConnectExtensionPage() {

  const { user, loading } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  const handleAuthenticate = async () => {
    setStatus("loading");
    setError(null);
    try {
      // Get token from cookies
      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("token="))
        ?.split("=")[1];

      if (!token) {
        throw new Error("Not authenticated");
      }

      // Call backend to get one-time code
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/extension/connect/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });
      if (!res.ok) {
        throw new Error("Failed to get one-time code");
      }
      const data = await res.json();
      const code = data.one_time_code;

      // Post message to extension (window.postMessage)
      window.postMessage({ type: "APPLYAI_EXTENSION_CONNECT", code }, window.location.origin);
      console.log("Posted message to extension with code:", code);

      setStatus("success");
    } catch (err: any) {
      setError(err.message || "Unknown error");
      setStatus("error");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex flex-col items-center justify-center min-h-[80vh]">
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="flex flex-col items-center justify-center min-h-[80vh]">
        {status === "idle" && (
          <Button onClick={handleAuthenticate}>Authenticate Extension</Button>
        )}
        {status === "loading" && <span>Connecting...</span>}
        {status === "success" && (
          <div className="flex flex-col items-center">
            <span className="text-green-600 font-semibold mb-2">Connected! You can close this tab.</span>
          </div>
        )}
        {status === "error" && (
          <div className="flex flex-col items-center">
            <span className="text-red-600 font-semibold mb-2">Failed, retry.</span>
            {error && <span className="text-xs text-gray-500">{error}</span>}
            <Button className="mt-2" onClick={handleAuthenticate}>Retry</Button>
          </div>
        )}
      </div>
    </div>
  );
}
