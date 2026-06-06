"use client"
import { useEffect, useState } from "react"
import { Bell, Clock, MapPin, Users, Zap, Calendar } from "lucide-react"
import { notificationService } from "@/services/wellnet"
import type { OffPeakDeal } from "@/types"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

const DEAL_TYPE_CONFIG: Record<string, { icon: any; label: string; color: string }> = {
  spa:      { icon: Zap,      label: "Spa treatment",  color: "bg-purple-50 border-purple-200 text-purple-700" },
  retreat:  { icon: Bell,     label: "Retreat",        color: "bg-wellnet-50 border-wellnet-200 text-wellnet-700" },
  yoga:     { icon: Users,    label: "Yoga session",   color: "bg-amber-50 border-amber-200 text-amber-700" },
  dining:   { icon: Clock,    label: "Wellness dining",color: "bg-green-50 border-green-200 text-green-700" },
  group:    { icon: Users,    label: "Group package",  color: "bg-blue-50 border-blue-200 text-blue-700" },
  consult:  { icon: Calendar, label: "Consult",        color: "bg-rose-50 border-rose-200 text-rose-700" },
}

function timeLeft(until: string): string {
  const diff = new Date(until).getTime() - Date.now()
  if (diff <= 0) return "Expired"
  const h = Math.floor(diff / 3600000)
  const m = Math.floor((diff % 3600000) / 60000)
  if (h > 24) return `${Math.floor(h/24)}d left`
  if (h > 0) return `${h}h ${m}m left`
  return `${m}m left`
}

// Demo deals for when API returns empty
const DEMO_DEALS: OffPeakDeal[] = [
  {
    id:"1", title:"Probiotic Herbal Spa Treatment", deal_type:"spa",
    description:"90-min gut-healing herbal treatment. Paired with your HabeShield score.",
    location:"Kuriftu Bishoftu", original_price_etb:2000, discounted_price_etb:1200,
    discount_pct:40, slots_remaining:3, booking_url:"https://kurifturesorts.com",
    valid_from:new Date().toISOString(), valid_until:new Date(Date.now()+6*3600000).toISOString(),
  },
  {
    id:"2", title:"Gut Reset Wellness Lunch", deal_type:"dining",
    description:"Injera + misir wot + ayib set — curated to boost your weekly fiber score.",
    location:"Kuriftu African Village", original_price_etb:450, discounted_price_etb:280,
    discount_pct:38, slots_remaining:8, booking_url:"https://kurifturesorts.com",
    valid_from:new Date().toISOString(), valid_until:new Date(Date.now()+2*3600000).toISOString(),
  },
  {
    id:"3", title:"Mystic Nights Sound Healing Session", deal_type:"retreat",
    description:"Overnight meditation journey in Kuriftu's nature-rich setting. Sound baths and guided mindfulness.",
    location:"Kuriftu Lake Tana", original_price_etb:1800, discounted_price_etb:1100,
    discount_pct:39, slots_remaining:5, booking_url:"https://kurifturesorts.com",
    valid_from:new Date().toISOString(), valid_until:new Date(Date.now()+24*3600000).toISOString(),
  },
  {
    id:"4", title:"Group Wellness Morning — 4 Friends", deal_type:"group",
    description:"Group gut scan + yoga with Weini + teff brunch. Minimum 4 people.",
    location:"Kuriftu Entoto Adventure Park", original_price_etb:1100, discounted_price_etb:800,
    discount_pct:27, slots_remaining:2, booking_url:"https://kurifturesorts.com",
    valid_from:new Date().toISOString(), valid_until:new Date(Date.now()+48*3600000).toISOString(),
  },
]

export default function DealsPage() {
  const [deals, setDeals] = useState<OffPeakDeal[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState("all")

  useEffect(() => {
    notificationService.getDeals()
      .then(r => setDeals(r.data.length > 0 ? r.data : DEMO_DEALS))
      .catch(() => setDeals(DEMO_DEALS))
      .finally(() => setLoading(false))
  }, [])

  const deal_types = ["all", ...Array.from(new Set(deals.map(d => d.deal_type)))]
  const filtered = filter === "all" ? deals : deals.filter(d => d.deal_type === filter)

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Bell className="w-5 h-5 text-wellnet-500" /> Kuriftu Off-Peak Deals
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Exclusive wellness experiences matched to your gut health score
        </p>
      </div>

      {/* How it works */}
      <div className="card bg-wellnet-50 border-wellnet-100">
        <div className="text-xs font-medium text-wellnet-700 mb-1">How off-peak deals work</div>
        <div className="text-xs text-wellnet-600 leading-relaxed">
          Kuriftu shares available slots with Well-Net. We match them to your gut score 
          and send personalised SMS notifications — so you get deals relevant to your 
          wellness level, not just generic promotions.
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {deal_types.map(t => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={cn(
              "flex-shrink-0 px-3 py-1.5 rounded-xl border text-xs font-medium capitalize transition-all",
              filter === t
                ? "bg-gray-900 text-white border-gray-900"
                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Deals */}
      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="h-40 bg-gray-100 rounded-2xl animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-8 text-sm text-gray-400">
          No deals available right now — check back soon.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(deal => {
            const cfg = DEAL_TYPE_CONFIG[deal.deal_type] || DEAL_TYPE_CONFIG.spa
            const Icon = cfg.icon
            const tl = timeLeft(deal.valid_until)
            const urgent = deal.slots_remaining <= 3
            const expiring = tl.includes("h") && parseInt(tl) < 4

            return (
              <div key={deal.id} className={cn("card border", cfg.color)}>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-white/70 flex items-center justify-center">
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <span className="text-[10px] font-semibold uppercase tracking-wide opacity-70">
                      {cfg.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    {urgent && (
                      <span className="text-[10px] bg-red-500 text-white px-2 py-0.5 rounded-full font-medium">
                        {deal.slots_remaining} left
                      </span>
                    )}
                    <span className={cn(
                      "text-[10px] font-medium px-2 py-0.5 rounded-full",
                      expiring ? "bg-red-100 text-red-600" : "bg-white/70"
                    )}>
                      {tl}
                    </span>
                  </div>
                </div>

                <h3 className="text-sm font-bold text-gray-900 mb-1">{deal.title}</h3>
                <p className="text-xs text-gray-600 leading-relaxed mb-3">{deal.description}</p>

                <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-3">
                  <MapPin className="w-3 h-3" />
                  {deal.location}
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-lg font-bold text-gray-900">
                      {Number(deal.discounted_price_etb).toLocaleString()} ETB
                    </span>
                    <span className="text-xs text-gray-400 line-through">
                      {Number(deal.original_price_etb).toLocaleString()}
                    </span>
                    <span className="text-xs font-bold text-wellnet-600">
                      -{deal.discount_pct}%
                    </span>
                  </div>
                  <a
                    href={deal.booking_url || "https://kurifturesorts.com"}
                    target="_blank"
                    rel="noopener"
                    onClick={() => toast.success("Opening Kuriftu booking…")}
                    className="btn-primary text-xs px-4 py-2"
                  >
                    Book now
                  </a>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="text-xs text-center text-gray-400">
        Deals are matched to your gut score and updated every 2 hours.
        <br />Enable SMS in settings to get notified automatically.
      </div>
    </div>
  )
}