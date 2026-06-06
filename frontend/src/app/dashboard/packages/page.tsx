//src/app/packages/page.tsx
"use client"

import { useEffect, useState } from "react"
import {
  Check,
  Star,
  Users,
  Building2,
  Leaf,
  Loader2,
} from "lucide-react"

import { packageService, extractArray } from "@/services/wellnet"
import type { WellnessPackage } from "@/types"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

const DEMO: WellnessPackage[] = [
  {
    id: "1",
    name: "Individual Premium",
    package_type: "individual",
    tagline: "Your personal wellness journey",
    price_etb: 150,
    billing_period: "monthly",
    max_members: 1,
    is_featured: false,
    kuriftu_discount_pct: 10,
    features: [
      "Daily gut health score",
      "AI wellness tips (Hana)",
      "Weekly trend charts",
      "SMS daily reminders",
      "10% off Kuriftu experiences",
    ],
  },

  {
    id: "2",
    name: "Family Plan",
    package_type: "family",
    tagline: "Whole family wellness under one account",
    price_etb: 450,
    billing_period: "monthly",
    max_members: 6,
    is_featured: false,
    kuriftu_discount_pct: 15,
    features: [
      "Everything in Individual",
      "Up to 6 family profiles",
      "Pregnancy & child modes",
      "AI weekly family meal plan",
      "1 free nutritionist consult/month",
      "15% off Kuriftu family packages",
    ],
  },

  {
    id: "3",
    name: "Kuriftu Resort Bundle",
    package_type: "kuriftu",
    tagline: "The ultimate Ethiopian wellness experience",
    price_etb: 1800,
    billing_period: "one_time",
    max_members: 1,
    is_featured: true,
    kuriftu_discount_pct: 0,
    features: [
      "Gut Health Passport on check-in",
      "Personalised resort menu scoring",
      "1 gut-targeted spa treatment",
      "Yoga or Mystic Nights session",
      "30-day post-stay SMS follow-up",
      "3-month Premium subscription included",
    ],
  },

  {
    id: "4",
    name: "Group / Friends",
    package_type: "group",
    tagline: "Wellness is better together",
    price_etb: 200,
    billing_period: "one_time",
    max_members: 4,
    is_featured: false,
    kuriftu_discount_pct: 25,
    features: [
      "Group gut scan session (60 min)",
      "Shared wellness leaderboard",
      "7-day group fiber challenge",
      "WhatsApp group AI coach bot",
      "25% off group Kuriftu booking",
      "Minimum 4 people",
    ],
  },

  {
    id: "5",
    name: "Corporate Wellness",
    package_type: "corporate",
    tagline: "Invest in your team's vitality",
    price_etb: 500,
    billing_period: "annual",
    max_members: 100,
    is_featured: false,
    kuriftu_discount_pct: 20,
    features: [
      "All-employee gut health dashboard",
      "Anonymous HR wellness report",
      "Quarterly nutritionist webinar",
      "Off-peak Kuriftu slots for staff",
      "Branded company challenge",
    ],
  },
]

const ICONS: Record<string, any> = {
  individual: Leaf,
  family: Users,
  kuriftu: Star,
  group: Users,
  corporate: Building2,
}

const COLORS: Record<
  string,
  { card: string; icon: string; btn: string }
> = {
  individual: {
    card: "border-gray-200",
    icon: "bg-wellnet-50 text-wellnet-600",
    btn: "btn-secondary",
  },

  family: {
    card: "border-purple-200",
    icon: "bg-purple-50 text-purple-600",
    btn: "bg-purple-500 hover:bg-purple-600 text-white font-medium px-4 py-2.5 rounded-xl transition-all",
  },

  kuriftu: {
    card: "border-wellnet-400",
    icon: "bg-wellnet-500 text-white",
    btn: "btn-primary",
  },

  group: {
    card: "border-amber-200",
    icon: "bg-amber-50 text-amber-600",
    btn: "bg-amber-500 hover:bg-amber-600 text-white font-medium px-4 py-2.5 rounded-xl transition-all",
  },

  corporate: {
    card: "border-gray-300",
    icon: "bg-gray-100 text-gray-600",
    btn: "btn-secondary",
  },
}

const BILLING: Record<string, string> = {
  monthly: "/ month",
  annual: "/ employee / year",
  one_time: "one-time",
}

export default function PackagesPage() {
  const [packages, setPackages] = useState<WellnessPackage[]>([])
  const [loading, setLoading] = useState(true)
  const [subbing, setSubbing] = useState<string | null>(null)

  useEffect(() => {
    packageService
      .list()
      .then((r) => {
        const arr = extractArray<WellnessPackage>(r.data)
        setPackages(arr.length > 0 ? arr : DEMO)
      })
      .catch(() => setPackages(DEMO))
      .finally(() => setLoading(false))
  }, [])

  const handleSub = async (pkg: WellnessPackage) => {
    setSubbing(pkg.id)

    await new Promise((r) => setTimeout(r, 900))

    toast.success(
      `${pkg.name} — we'll notify you when payments launch!`
    )

    setSubbing(null)
  }

  const sorted = [...packages].sort((a, b) => {
    if (a.package_type === "kuriftu") return -1
    if (b.package_type === "kuriftu") return 1
    return a.price_etb - b.price_etb
  })

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">
          Wellness Packages
        </h1>

        <p className="text-sm text-gray-500 mt-0.5">
          Choose the plan that fits your journey
        </p>
      </div>

      <div className="card bg-gradient-to-r from-wellnet-500 to-wellnet-600 border-none text-white">
        <div className="flex items-start gap-3">
          <span className="text-3xl shrink-0">🏨</span>

          <div>
            <div className="font-bold text-sm mb-1">
              Well-Net × Kuriftu Resorts
            </div>

            <div className="text-wellnet-100 text-xs leading-relaxed">
              Official wellness partner. Every package includes
              Kuriftu experience discounts — yoga, Mystic Nights
              sound healing, spa treatments, and gut reset retreats
              across Ethiopia.
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-56 bg-gray-100 rounded-2xl animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((pkg) => {
            const c = COLORS[pkg.package_type] || COLORS.individual
            const Icon = ICONS[pkg.package_type] || Leaf
            const busy = subbing === pkg.id

            return (
              <div
                key={pkg.id}
                className={cn(
                  "card border",
                  c.card,
                  pkg.is_featured && "border-2 shadow-md"
                )}
              >
                {pkg.is_featured && (
                  <div className="flex justify-end mb-2">
                    <span className="badge-teal text-[10px] font-bold uppercase tracking-wide">
                      ⭐ Most popular
                    </span>
                  </div>
                )}

                <div className="flex items-start gap-3 mb-4">
                  <div
                    className={cn(
                      "w-10 h-10 rounded-xl flex items-center justify-center shrink-0",
                      c.icon
                    )}
                  >
                    <Icon className="w-5 h-5" />
                  </div>

                  <div className="flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="text-base font-bold text-gray-900">
                        {pkg.name}
                      </div>

                      {pkg.max_members > 1 && (
                        <span className="badge-purple text-[10px] shrink-0">
                          {pkg.package_type === "corporate"
                            ? "100+"
                            : `Up to ${pkg.max_members}`}
                        </span>
                      )}
                    </div>

                    <div className="text-xs text-gray-500">
                      {pkg.tagline}
                    </div>
                  </div>
                </div>

                <div className="flex items-baseline gap-1.5 mb-4">
                  <span className="text-2xl font-bold text-gray-900">
                    {Number(pkg.price_etb).toLocaleString()} ETB
                  </span>

                  <span className="text-sm text-gray-400">
                    {BILLING[pkg.billing_period]}
                  </span>
                </div>

                <ul className="space-y-1.5 mb-4">
                  {pkg.features.map((f, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2"
                    >
                      <Check className="w-3.5 h-3.5 text-wellnet-500 shrink-0 mt-0.5" />

                      <span className="text-xs text-gray-600 leading-relaxed">
                        {f}
                      </span>
                    </li>
                  ))}
                </ul>

                {pkg.kuriftu_discount_pct > 0 && (
                  <div className="bg-wellnet-50 rounded-xl px-3 py-2 mb-4 text-xs text-wellnet-700">
                    🏨 Includes {pkg.kuriftu_discount_pct}% off all
                    Kuriftu wellness experiences
                  </div>
                )}

                <button
                  onClick={() => handleSub(pkg)}
                  disabled={busy}
                  className={cn(
                    "w-full py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all",
                    c.btn
                  )}
                >
                  {busy ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Processing…
                    </>
                  ) : pkg.billing_period === "one_time" ? (
                    "Book this package"
                  ) : (
                    "Get started"
                  )}
                </button>
              </div>
            )
          })}
        </div>
      )}

      <p className="text-xs text-center text-gray-400 pb-2">
        All prices in Ethiopian Birr (ETB). Payments processed securely.
      </p>
    </div>
  )
}
