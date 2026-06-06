"use client"
import { useEffect, useState } from "react"
import Link from "next/link"
import { Leaf, Utensils, Sparkles, Bell, TrendingUp, Users } from "lucide-react"
import GutScoreRing from "@/components/wellness/GutScoreRing"
import { foodService, aiService, notificationService, extractArray } from "@/services/wellnet"
import { useAuthStore, useMealLogStore } from "@/store"
import type { DailyNutrition, FeedCard, OffPeakDeal } from "@/types"
import { cn } from "@/lib/utils"

const FEED_STYLE: Record<string, { card: string; title: string; text: string }> = {
  teal:   { card: "bg-wellnet-50 border-wellnet-200", title: "text-wellnet-800", text: "text-wellnet-700" },
  amber:  { card: "bg-amber-50  border-amber-200",   title: "text-amber-800",   text: "text-amber-700"  },
  purple: { card: "bg-purple-50 border-purple-200",  title: "text-purple-800",  text: "text-purple-700" },
  green:  { card: "bg-green-50  border-green-200",   title: "text-green-800",   text: "text-green-700"  },
}

const QUICK_ACTIONS = [
  { href: "/dashboard/log",              label: "Log meal",      sub: "Track today's food",  icon: Utensils,   bg: "bg-wellnet-50", ic: "text-wellnet-600" },
  { href: "/dashboard/ai",               label: "AI Coach",      sub: "Personalised tips",   icon: Sparkles,   bg: "bg-purple-50",  ic: "text-purple-600" },
  { href: "/dashboard/weekly", label: "Weekly report", sub: "7-day trends",        icon: TrendingUp, bg: "bg-blue-50",    ic: "text-blue-600" },
  { href: "/dashboard/family", label: "Family plan",   sub: "All members",         icon: Users,      bg: "bg-amber-50",   ic: "text-amber-600" },
]

export default function DashboardPage() {
  const { profile } = useAuthStore()
  const { setTodayNutrition } = useMealLogStore()
  const [today, setToday]   = useState<DailyNutrition | null>(null)
  const [feed, setFeed]     = useState<FeedCard[]>([])
  const [deals, setDeals]   = useState<OffPeakDeal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const [nutRes, feedRes, dealRes] = await Promise.allSettled([
          foodService.getDaily(),
          aiService.getFeed(),
          notificationService.getDeals(),
        ])

        // ── Daily nutrition ──────────────────────────────────────
        if (nutRes.status === "fulfilled") {
          const d = nutRes.value.data
          // DRF might return {gut_score:0, message:"..."} when no meals logged
          if (d && typeof d.gut_score === "number") {
            setToday(d)
            setTodayNutrition(d)
          }
        }

        // ── Feed cards ───────────────────────────────────────────
        if (feedRes.status === "fulfilled") {
          const raw = feedRes.value.data
          // raw is JourneyFeedResponse: { feed: FeedCard[], ... }
          const cards = Array.isArray(raw?.feed) ? raw.feed : []
          setFeed(cards.slice(0, 3))
        }

        // ── Deals ────────────────────────────────────────────────
        if (dealRes.status === "fulfilled") {
          const arr = extractArray<OffPeakDeal>(dealRes.value.data)
          setDeals(arr.slice(0, 2))
        }
      } catch {
        // silently handled — each section degrades gracefully
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const gutScore = today?.gut_score ?? profile?.current_gut_score ?? 0
  const name     = profile?.display_name || "there"

  const METRICS = [
    { label: "Fiber",         value: today?.fiber_g          ?? 0, max: 25, unit: "g"  },
    { label: "Protein",       value: today?.protein_g        ?? 0, max: 50, unit: "g"  },
    { label: "Iron",          value: today?.iron_mg          ?? 0, max: 18, unit: "mg" },
    { label: "Fermentation",  value: today?.fermentation_total ?? 0, max: 9,  unit: ""  },
  ]

  return (
    <div className="max-w-2xl mx-auto space-y-5">

      {/* Greeting */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">Selam, {name} 👋</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {new Date().toLocaleDateString("en-ET", {
            weekday: "long", month: "long", day: "numeric",
          })}
        </p>
      </div>

      {/* Score card */}
      <div className="card flex items-start gap-5">
        <GutScoreRing score={gutScore} size="md" animate />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-gray-400 mb-2.5 uppercase tracking-wide">
            Today's gut health
          </p>
          {loading ? (
            <div className="space-y-2">
              {[1,2,3,4].map(i => (
                <div key={i} className="h-4 bg-gray-100 rounded-full animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {METRICS.map(({ label, value, max, unit }) => (
                <div key={label}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">{label}</span>
                    <span className="text-gray-700 font-medium tabular-nums">
                      {Number(value).toFixed(unit === "" ? 0 : 1)}{unit}
                      <span className="text-gray-300"> / {max}{unit}</span>
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-wellnet-500 rounded-full transition-all duration-700"
                      style={{ width: `${Math.min((Number(value) / max) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
          {!loading && !today && (
            <p className="text-xs text-gray-400">No meals logged yet — tap "Log meal" to start.</p>
          )}
        </div>
      </div>

      {/* Quick actions grid */}
      <div className="grid grid-cols-2 gap-3">
        {QUICK_ACTIONS.map(({ href, label, sub, icon: Icon, bg, ic }) => (
          <Link key={href} href={href} className="card-hover flex items-center gap-3 p-4">
            <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center shrink-0", bg)}>
              <Icon className={cn("w-4 h-4", ic)} />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-medium text-gray-800 truncate">{label}</div>
              <div className="text-xs text-gray-400 truncate">{sub}</div>
            </div>
          </Link>
        ))}
      </div>

      {/* Kuriftu off-peak deals */}
      {deals.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold text-gray-700">🏨 Kuriftu deals for you</h2>
            <Link href="/dashboard/deals" className="text-xs text-wellnet-600 hover:underline">
              See all →
            </Link>
          </div>
          <div className="space-y-2">
            {deals.map(deal => (
              <div key={deal.id} className="card flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-wellnet-50 shrink-0 flex items-center justify-center">
                  <Bell className="w-4 h-4 text-wellnet-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-800 truncate">{deal.title}</div>
                  <div className="text-xs text-gray-500 truncate">{deal.location}</div>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className="text-sm font-bold text-wellnet-600">
                      {Number(deal.discounted_price_etb).toLocaleString()} ETB
                    </span>
                    <span className="text-xs text-gray-400 line-through">
                      {Number(deal.original_price_etb).toLocaleString()}
                    </span>
                    <span className="badge-teal text-[10px]">-{deal.discount_pct}%</span>
                  </div>
                </div>
                <a
                  href={deal.booking_url || "https://kurifturesorts.com"}
                  target="_blank" rel="noopener"
                  className="btn-secondary text-xs px-3 py-1.5 shrink-0"
                >
                  Book
                </a>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Wellness journey feed */}
      {feed.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Your wellness journey</h2>
          <div className="space-y-2">
            {feed.map((card, i) => {
              const s = FEED_STYLE[card.color] ?? FEED_STYLE.teal
              return (
                <div key={i} className={cn("card border", s.card)}>
                  <div className={cn("text-sm font-semibold mb-1", s.title)}>{card.title}</div>
                  <div className={cn("text-xs leading-relaxed", s.text)}>{card.body}</div>
                  {card.cta_label && (
                    <Link
                      href={card.cta_action === "book_kuriftu" ? "/dashboard/packages" : "/dashboard/log"}
                      className={cn("inline-block mt-2 text-xs font-medium underline underline-offset-2", s.title)}
                    >
                      {card.cta_label} →
                    </Link>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Empty state */}
      {!loading && !today && feed.length === 0 && (
        <div className="card text-center py-10">
          <Leaf className="w-10 h-10 text-wellnet-200 mx-auto mb-3" />
          <p className="text-sm font-medium text-gray-700 mb-1">
            How are you nourishing yourself today?
          </p>
          <p className="text-xs text-gray-400 mb-4">
            Log your first meal to unlock your gut score and AI insights.
          </p>
          <Link href="/dashboard/log" className="btn-primary inline-block">
            Log a meal 🌿
          </Link>
        </div>
      )}
    </div>
  )
}