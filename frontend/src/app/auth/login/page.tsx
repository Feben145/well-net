"use client"
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Leaf, Eye, EyeOff, Loader2, BadgeCheck } from "lucide-react"
import { authService } from "@/services/wellnet"
import { useAuthStore } from "@/store"
import { cn } from "@/lib/utils"

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
})
type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const router = useRouter()
  const { setUser, setProfile } = useAuthStore()
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      await authService.login(data.email, data.password)
      const [meRes, profileRes] = await Promise.all([
        authService.getMe(),
        authService.getProfile(),
      ])
      setUser(meRes.data)
      setProfile(profileRes.data)
      toast.success("Welcome back to Well-Net!")
      router.push("/dashboard")
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Invalid email or password"
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-wellnet-50 via-white to-amber-50">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 bg-wellnet-500">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
            <Leaf className="w-6 h-6 text-white" />
          </div>
          <span className="text-white font-bold text-xl">Well-Net</span>
        </div>

        <div>
          <h1 className="text-4xl font-bold text-white leading-tight mb-4">
            Ethiopian Wellness,<br />Backed by Science.
          </h1>
          <p className="text-wellnet-100 text-lg leading-relaxed mb-6">
            AI-powered gut health scoring built on the EPHI Ethiopian Food
            Composition Table — injera, misir wot, and 435 more foods,
            verified by Ethiopia's own public health institute.
          </p>

          {/* EPHI source badge */}
          <div className="flex items-center gap-2 mb-8 bg-white/10 rounded-2xl px-4 py-3 w-fit">
            <BadgeCheck className="w-5 h-5 text-wellnet-100 shrink-0" />
            <span className="text-wellnet-50 text-sm font-medium">
              Sourced from the EPHI Food Composition Table
            </span>
          </div>

          {/* Stat cards */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { val: "437", label: "EPHI-verified Ethiopian foods" },
              { val: "82",  label: "Avg gut score after 2 weeks" },
              { val: "6",   label: "Family profiles per account" },
              { val: "24/7",label: "AI wellness coach" },
            ].map(({ val, label }) => (
              <div key={label} className="bg-white/10 rounded-2xl p-4">
                <div className="text-2xl font-bold text-white">{val}</div>
                <div className="text-wellnet-100 text-xs mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="text-wellnet-200 text-sm">
          © 2026 Well-Net · Powered by ALX Ethiopia
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-9 h-9 rounded-xl bg-wellnet-500 flex items-center justify-center">
              <Leaf className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-gray-900">Well-Net</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Welcome back</h2>
            <p className="text-gray-500 text-sm mt-1">Sign in to your wellness journey</p>
          </div>

          {/* Mobile-only EPHI badge */}
          <div className="lg:hidden flex items-center gap-2 mb-6 bg-wellnet-50 rounded-2xl px-4 py-3">
            <BadgeCheck className="w-4 h-4 text-wellnet-600 shrink-0" />
            <span className="text-wellnet-700 text-xs font-medium">
              437 foods verified by the EPHI Food Composition Table
            </span>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Email address
              </label>
              <input
                {...register("email")}
                type="email"
                placeholder="you@example.com"
                className={cn("input", errors.email && "border-red-400 focus:ring-red-400")}
              />
              {errors.email && (
                <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  {...register("password")}
                  type={showPw ? "text" : "password"}
                  placeholder="••••••••"
                  className={cn("input pr-10", errors.password && "border-red-400 focus:ring-red-400")}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-3 flex items-center justify-center gap-2"
            >
              {loading
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Signing in…</>
                : "Sign in"
              }
            </button>
          </form>

          <div className="mt-6 text-center">
            <span className="text-sm text-gray-500">Don't have an account? </span>
            <Link href="/auth/register" className="text-sm font-medium text-wellnet-600 hover:underline">
              Create one free
            </Link>
          </div>

          {/* Kuriftu guest login hint */}
          <div className="mt-6 p-4 bg-wellnet-50 rounded-2xl">
            <div className="text-xs font-medium text-wellnet-700 mb-0.5">
              🏨 Kuriftu Resort guest?
            </div>
            <div className="text-xs text-wellnet-600">
              Scan the QR code at check-in for your free Gut Health Passport scan.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}