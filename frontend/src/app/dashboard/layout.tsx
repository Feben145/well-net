"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect } from "react"
import {
  LayoutDashboard,
  Utensils,
  Sparkles,
  Users,
  Bell,
  Package,
  LogOut,
  Menu,
  X,
  TrendingUp,
  Leaf,
  Globe,
  UserCircle,
} from "lucide-react"

import { useAuthStore, useUIStore } from "@/store"
import { authService } from "@/services/wellnet"
import { cn } from "@/lib/utils"

const NAV = [
  {
    section: "Wellness",
    href: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
  },
   {
    section: "Wellness",
    href: "/dashboard/foods",
    label: "Foods",
    icon: Utensils,
  },
  {
    section: "Wellness",
    href: "/dashboard/log",
    label: "Log meal",
    icon: Utensils,
  },
  {
    section: "Wellness",
    href: "/dashboard/ai",
    label: "AI Coach",
    icon: Sparkles,
  },
  {
    section: "Insights",
    href: "/dashboard/weekly",
    label: "Weekly report",
    icon: TrendingUp,
  },
  {
    section: "Insights",
    href: "/dashboard/family",
    label: "Family plan",
    icon: Users,
  },
  {
    section: "Services",
    href: "/dashboard/experts",
    label: "Experts",
    icon: UserCircle,
  },
  {
    section: "Services",
    href: "/dashboard/packages",
    label: "Packages",
    icon: Package,
  },
  {
    section: "Services",
    href: "/dashboard/deals",
    label: "Kuriftu deals",
    icon: Bell,
  },
   { section: "Insights",
      href: "/dashboard/community",
       label: "Community 🌿", 
         icon: Globe  
          },
]

const SECTIONS = ["Wellness", "Insights", "Services"]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { isAuthenticated, logout, profile } = useAuthStore()
  const { sidebarOpen, setSidebarOpen } = useUIStore()

  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login")
    }
  }, [isAuthenticated, router])

  const handleLogout = () => {
    authService.logout()
    logout()
    router.push("/auth/login")
  }

  const isActive = (href: string) =>
    pathname === href ||
    (href !== "/dashboard" && pathname.startsWith(href + "/"))

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-100 flex flex-col",
          "transition-transform duration-300 lg:translate-x-0 lg:static",
          sidebarOpen ? "translate-x-0 shadow-xl" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100">
          <div className="w-9 h-9 rounded-xl bg-wellnet-500 flex items-center justify-center shrink-0">
            <Leaf className="w-5 h-5 text-white" />
          </div>

          <div className="min-w-0 flex-1">
            <div className="font-bold text-gray-900 text-sm leading-tight">
              Well-Net
            </div>

            <div className="text-xs text-wellnet-600 truncate">
              {profile?.display_name || "Wellness Ecosystem"}
            </div>
          </div>

          <button
            className="lg:hidden shrink-0 p-1"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Score pill */}
        {(profile?.current_gut_score ?? 0) > 0 && (
          <div className="mx-4 mt-3 flex items-center gap-3 bg-wellnet-50 rounded-xl px-3 py-2.5">
            <div className="w-9 h-9 rounded-full border-2 border-wellnet-400 flex items-center justify-center shrink-0">
              <span className="text-xs font-bold text-wellnet-600">
                {profile?.current_gut_score}
              </span>
            </div>

            <div>
              <div className="text-xs font-semibold text-wellnet-700">
                Today's gut score
              </div>

              <div className="text-[10px] text-wellnet-500">
                🔥 {profile?.wellness_streak_days ?? 0} day streak
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 px-3 py-3 overflow-y-auto space-y-4">
          {SECTIONS.map((section) => (
            <div key={section}>
              <div className="px-3 mb-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                {section}
              </div>

              {NAV.filter((n) => n.section === section).map(
                ({ href, label, icon: Icon }) => (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setSidebarOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all mb-0.5",
                      isActive(href)
                        ? "bg-wellnet-50 text-wellnet-700"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    )}
                  >
                    <Icon
                      className={cn(
                        "w-4 h-4 shrink-0",
                        isActive(href)
                          ? "text-wellnet-600"
                          : "text-gray-400"
                      )}
                    />

                    {label}
                  </Link>
                )
              )}
            </div>
          ))}
        </nav>

        {/* Kuriftu banner */}
        <div className="mx-3 mb-3 p-3 bg-gradient-to-br from-wellnet-50 to-amber-50 rounded-2xl border border-wellnet-100">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-sm">🏨</span>

            <div className="text-xs font-semibold text-wellnet-700">
              Kuriftu × Well-Net
            </div>
          </div>

          <div className="text-[10px] text-gray-500 leading-relaxed mb-2">
            Yoga · Sound healing · Gut reset retreats
          </div>

          <Link
            href="/dashboard/packages"
            onClick={() => setSidebarOpen(false)}
            className="block text-center text-xs font-medium bg-wellnet-500 text-white py-1.5 rounded-xl hover:bg-wellnet-600 transition-colors"
          >
            Explore experiences
          </Link>
        </div>

        {/* Logout */}
        <div className="px-3 pb-4 border-t border-gray-100 pt-3">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium text-gray-500 hover:bg-red-50 hover:text-red-600 transition-all"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <header className="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-100">
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="w-5 h-5 text-gray-600" />
          </button>

          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-wellnet-500 flex items-center justify-center">
              <Leaf className="w-4 h-4 text-white" />
            </div>

            <span className="font-bold text-sm text-gray-900">
              Well-Net
            </span>
          </div>

          {(profile?.current_gut_score ?? 0) > 0 && (
            <div className="ml-auto flex items-center gap-1 bg-wellnet-50 rounded-full px-2.5 py-1">
              <span className="text-xs font-bold text-wellnet-600">
                {profile?.current_gut_score}
              </span>

              <span className="text-[10px] text-wellnet-500">
                /100
              </span>
            </div>
          )}
        </header>

        <main className="flex-1 overflow-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
