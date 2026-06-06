// app/page.tsx
"use client"
import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/store"

export default function RootPage() {
  const { isAuthenticated } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard")
    } else {
      router.push("/auth/login")
    }
  }, [isAuthenticated, router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-wellnet-50">
      <div className="flex flex-col items-center gap-3">
        <div className="w-12 h-12 rounded-full bg-wellnet-500 flex items-center justify-center">
          <span className="text-white text-xl font-bold">W</span>
        </div>
        <p className="text-wellnet-700 text-sm font-medium">Loading Well-Net…</p>
      </div>
    </div>
  )
}
