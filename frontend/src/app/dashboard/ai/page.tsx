"use client"
import { useEffect, useState, useRef } from "react"
import {
  Sparkles, Leaf, Zap, Star, RefreshCw,
  Loader2, Calendar, MessageCircle, Printer, Download,
} from "lucide-react"
import { aiService } from "@/services/wellnet"
import { useAuthStore } from "@/store"
import GutScoreRing from "@/components/wellness/GutScoreRing"
import type { WellnessTipsResponse, JourneyFeedResponse, FeedCard } from "@/types"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

const ICONS: Record<string, any> = { leaf: Leaf, zap: Zap, star: Star, heart: Sparkles }
const CARD: Record<string, { bg: string; title: string; body: string; btn: string }> = {
  teal:   { bg:"bg-wellnet-50 border-wellnet-200", title:"text-wellnet-800", body:"text-wellnet-700", btn:"bg-wellnet-500 text-white" },
  amber:  { bg:"bg-amber-50 border-amber-200",    title:"text-amber-800",   body:"text-amber-700",   btn:"bg-amber-500 text-white" },
  purple: { bg:"bg-purple-50 border-purple-200",  title:"text-purple-800",  body:"text-purple-700",  btn:"bg-purple-500 text-white" },
  green:  { bg:"bg-green-50 border-green-200",    title:"text-green-800",   body:"text-green-700",   btn:"bg-green-500 text-white" },
}
const FEED_EMOJI: Record<string, string> = {
  insight:"💡", tip:"🌿", retreat:"🏨", challenge:"🏆", milestone:"⭐"
}

export default function AIPage() {
  const { profile } = useAuthStore()
  const printRef = useRef<HTMLDivElement>(null)

  const [tips,  setTips]  = useState<WellnessTipsResponse | null>(null)
  const [feed,  setFeed]  = useState<JourneyFeedResponse | null>(null)
  const [plan,  setPlan]  = useState<any>(null)
  const [tab,   setTab]   = useState<"tips"|"feed"|"plan">("tips")
  const [loadT, setLoadT] = useState(true)
  const [loadF, setLoadF] = useState(true)
  const [loadP, setLoadP] = useState(false)

  useEffect(() => {
    aiService.getTips()
      .then(r => setTips(r.data))
      .catch(() => {})
      .finally(() => setLoadT(false))

    aiService.getFeed()
      .then(r => setFeed(r.data))
      .catch(() => {})
      .finally(() => setLoadF(false))
  }, [])

  const refreshTips = async () => {
    setLoadT(true)
    try { setTips((await aiService.getTips()).data); toast.success("Tips refreshed!") }
    catch { toast.error("Could not refresh tips") }
    finally { setLoadT(false) }
  }

  const generatePlan = async () => {
    setLoadP(true)
    try {
      const r = await aiService.getMealPlan(7)
      setPlan(r.data)
      setTab("plan")
    } catch {
      toast.error("Could not generate plan. Try again.")
    } finally {
      setLoadP(false)
    }
  }

  const handlePrint = () => {
    window.print()
  }

  const gutScore  = feed?.gut_score  ?? profile?.current_gut_score ?? 0
  const weeklyAvg = feed?.weekly_avg ?? 0
  const streak    = feed?.streak     ?? profile?.wellness_streak_days ?? 0
  const feedCards = Array.isArray(feed?.feed) ? feed!.feed : []

  return (
    <>
      {/* ── Print styles — only active during window.print() ───── */}
      <style>{`
        @media print {
          /* Hide everything except the meal plan */
          body * { visibility: hidden; }
          #meal-plan-print, #meal-plan-print * { visibility: visible; }
          #meal-plan-print {
            position: fixed;
            top: 0; left: 0;
            width: 100%;
            padding: 24px;
            background: white;
          }
          .no-print { display: none !important; }
          .print-only { display: block !important; }
        }
        .print-only { display: none; }
      `}</style>

      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-wellnet-500" /> AI Wellness Coach
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Hana, your personal Ethiopian wellness guide
            </p>
          </div>
          {/* Print button — only shown on plan tab */}
          {tab === "plan" && plan && !plan.error && (
            <button
              onClick={handlePrint}
              className="no-print flex items-center gap-2 btn-secondary px-3 py-2 text-sm"
            >
              <Printer className="w-4 h-4" /> Print plan
            </button>
          )}
        </div>

        {/* Score summary */}
        <div className="card flex items-center gap-5">
          <GutScoreRing score={gutScore} size="md" animate />
          <div className="flex-1 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-gray-50 rounded-xl p-3">
                <div className="text-xs text-gray-400 mb-0.5">Weekly avg</div>
                <div className="text-xl font-bold text-gray-800">{weeklyAvg || "—"}</div>
              </div>
              <div className="bg-amber-50 rounded-xl p-3">
                <div className="text-xs text-amber-600 mb-0.5">🔥 Streak</div>
                <div className="text-xl font-bold text-amber-700">{streak}d</div>
              </div>
            </div>
            {tips?.wellness_message && (
              <p className="text-xs text-gray-500 italic leading-relaxed">
                "{tips.wellness_message}"
              </p>
            )}
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1 no-print">
          {[
            { id:"tips",  label:"🌿 Tips" },
            { id:"feed",  label:"✨ Journey" },
            { id:"plan",  label:"📅 Meal plan" },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id as any)}
              className={cn(
                "flex-1 py-2 rounded-lg text-sm font-medium transition-all",
                tab === t.id ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              )}
            >{t.label}</button>
          ))}
        </div>

        {/* ── Tips ─────────────────────────────────────────────── */}
        {tab === "tips" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-700">Your personalised tips</span>
              <button onClick={refreshTips} disabled={loadT}
                className="flex items-center gap-1.5 text-xs text-wellnet-600">
                <RefreshCw className={cn("w-3.5 h-3.5", loadT && "animate-spin")} /> Refresh
              </button>
            </div>

            {loadT ? (
              [...Array(3)].map((_,i) => <div key={i} className="h-24 bg-gray-100 rounded-2xl animate-pulse" />)
            ) : tips?.tips?.length ? (
              tips.tips.map((tip, i) => {
                const Icon  = ICONS[tip.icon] || Leaf
                const style = CARD[tip.color] || CARD.teal
                return (
                  <div key={i} className={cn("card border", style.bg)}>
                    <div className="flex items-start gap-3">
                      <div className={cn("w-8 h-8 rounded-xl flex items-center justify-center shrink-0", style.btn)}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className={cn("text-sm font-semibold mb-1", style.title)}>{tip.title}</div>
                        <div className={cn("text-xs leading-relaxed", style.body)}>{tip.body}</div>
                      </div>
                    </div>
                  </div>
                )
              })
            ) : (
              <div className="card text-center py-6 text-sm text-gray-400">
                Log a meal first to get personalised tips.
              </div>
            )}

            {tips?.kuriftu_tip && (
              <div className="card border border-wellnet-200 bg-wellnet-50">
                <div className="flex items-start gap-3">
                  <span className="text-2xl shrink-0">🏨</span>
                  <div>
                    <div className="text-sm font-semibold text-wellnet-800 mb-1">
                      Kuriftu Wellness
                    </div>
                    <div className="text-xs text-wellnet-700 leading-relaxed">
                      {tips.kuriftu_tip}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Telegram CTA */}
            <div className="card bg-gray-50 border-gray-100">
              <div className="flex items-center gap-3">
                <MessageCircle className="w-5 h-5 text-gray-400 shrink-0" />
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-700">Get tips on Telegram</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    Message <span className="font-mono">@WellNetEthiopiaBot</span> — works without data
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Journey feed ──────────────────────────────────────── */}
        {tab === "feed" && (
          <div className="space-y-3">
            <p className="text-sm text-gray-500">Your wellness journey — today's story</p>
            {loadF ? (
              [...Array(4)].map((_,i) => <div key={i} className="h-24 bg-gray-100 rounded-2xl animate-pulse" />)
            ) : feedCards.length ? (
              feedCards.map((card: FeedCard, i: number) => {
                const style = CARD[card.color] || CARD.teal
                return (
                  <div key={i} className={cn("card border", style.bg)}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span>{FEED_EMOJI[card.type] || "🌿"}</span>
                      <div className={cn("text-sm font-semibold", style.title)}>{card.title}</div>
                    </div>
                    <div className={cn("text-xs leading-relaxed", style.body)}>{card.body}</div>
                    {card.cta_label && (
                      <button className={cn("mt-3 px-3 py-1.5 rounded-lg text-xs font-medium", style.btn)}>
                        {card.cta_label} →
                      </button>
                    )}
                  </div>
                )
              })
            ) : (
              <div className="card text-center py-6 text-sm text-gray-400">
                Log meals consistently to unlock your wellness journey feed.
              </div>
            )}
          </div>
        )}

        {/* ── Meal plan ─────────────────────────────────────────── */}
        {tab === "plan" && (
          <div className="space-y-3">
            {!plan ? (
              <div className="card text-center py-8">
                <Calendar className="w-10 h-10 text-wellnet-200 mx-auto mb-3" />
                <div className="text-sm font-semibold text-gray-700 mb-1">AI Family Meal Plan</div>
                <div className="text-xs text-gray-400 mb-5 max-w-xs mx-auto leading-relaxed">
                  7-day Ethiopian meal plan for you and your family.
                  Respects fasting days, pregnancy needs, and health conditions.
                </div>
                <button onClick={generatePlan} disabled={loadP}
                  className="btn-primary inline-flex items-center gap-2 px-6">
                  {loadP
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating…</>
                    : <><Sparkles className="w-4 h-4" /> Generate 7-day plan</>
                  }
                </button>
              </div>
            ) : plan.error ? (
              <div className="card text-center py-6 text-sm text-red-500">{plan.error}</div>
            ) : (
              <>
                {/* Action bar */}
                <div className="flex items-center justify-between no-print">
                  <span className="text-sm font-semibold text-gray-700">7-day family plan</span>
                  <div className="flex gap-2">
                    <button onClick={handlePrint}
                      className="flex items-center gap-1.5 btn-secondary px-3 py-2 text-xs">
                      <Printer className="w-3.5 h-3.5" /> Print
                    </button>
                    <button onClick={generatePlan} disabled={loadP}
                      className="text-xs text-wellnet-600 flex items-center gap-1 px-3 py-2">
                      <RefreshCw className={cn("w-3.5 h-3.5", loadP && "animate-spin")} /> Regenerate
                    </button>
                  </div>
                </div>

                {/* Print header — only visible when printing */}
                <div id="meal-plan-print" ref={printRef}>
                  <div className="print-only mb-6 pb-4 border-b border-gray-200">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-10 h-10 rounded-xl bg-wellnet-500 flex items-center justify-center">
                        <span style={{color:'white',fontWeight:'bold',fontSize:'16px'}}>W</span>
                      </div>
                      <div>
                        <div style={{fontWeight:'600',fontSize:'16px'}}>Well-Net — 7-Day Wellness Meal Plan</div>
                        <div style={{fontSize:'12px',color:'#666'}}>
                          Generated {new Date().toLocaleDateString("en-ET", {weekday:"long",year:"numeric",month:"long",day:"numeric"})}
                        </div>
                      </div>
                    </div>
                    <p style={{fontSize:'11px',color:'#888'}}>
                      Based on Ethiopian dietary science · Sources: FAO Ethiopia, PMC research, Heritage Nutrition
                    </p>
                  </div>

                  {/* Days */}
                  {(plan.days || []).map((day: any) => (
                    <div key={day.day} className="card mb-3" style={{breakInside:'avoid'}}>
                      <div className="text-sm font-semibold text-gray-800 mb-3 pb-2 border-b border-gray-100">
                        {day.day_name || `Day ${day.day}`}
                      </div>
                      {["breakfast","lunch","dinner"].map(meal => (
                        <div key={meal} className="flex gap-3 mb-2 last:mb-0">
                          <div className="w-16 text-xs font-medium text-gray-400 pt-0.5 capitalize shrink-0">
                            {meal}
                          </div>
                          <div className="flex-1 text-xs text-gray-700 leading-relaxed">
                            {day.meals?.[meal]?.foods?.join(", ") || "—"}
                            {day.meals?.[meal]?.notes && (
                              <span className="text-gray-400"> · {day.meals[meal].notes}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}

                  {/* Shopping list */}
                  {Array.isArray(plan.shopping_list) && plan.shopping_list.length > 0 && (
                    <div className="card bg-amber-50 border-amber-100" style={{breakInside:'avoid'}}>
                      <div className="text-sm font-semibold text-amber-800 mb-2">🛒 Shopping list</div>
                      <div className="flex flex-wrap gap-1.5">
                        {plan.shopping_list.map((item: string, i: number) => (
                          <span key={i} className="badge-amber text-xs">{item}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Print footer */}
                  <div className="print-only mt-6 pt-4 border-t border-gray-200 text-center">
                    <p style={{fontSize:'10px',color:'#999'}}>
                      Well-Net Ethiopian Wellness Ecosystem · wellnet.et · Partner of Kuriftu Resorts
                    </p>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </>
  )
}