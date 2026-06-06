"use client"
import { useEffect, useState, useMemo } from "react"
import { Search, X, ExternalLink, BookOpen, Leaf, ShoppingCart, ChevronDown } from "lucide-react"
import { foodService, extractArray } from "@/services/wellnet"
import type { EthiopianFood } from "@/types"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { useMealLogStore } from "@/store"
import { useRouter } from "next/navigation"

// ── Category config ───────────────────────────────────────────────────────────
const CATEGORIES = [
  { id: "all",        label: "All",        emoji: "🌍" },
  { id: "grains",     label: "Grains",     emoji: "🌾" },
  { id: "legumes",    label: "Legumes",    emoji: "🫘" },
  { id: "meat",       label: "Meat",       emoji: "🍖" },
  { id: "dairy",      label: "Dairy",      emoji: "🥛" },
  { id: "vegetables", label: "Vegetables", emoji: "🥦" },
  { id: "drinks",     label: "Drinks",     emoji: "☕" },
  { id: "special",    label: "Special",    emoji: "✨" },
]

const CAT_COLOR: Record<string, { bg: string; text: string; border: string; bar: string }> = {
  grains:     { bg:"bg-amber-50",   text:"text-amber-700",   border:"border-amber-200",  bar:"bg-amber-500"  },
  legumes:    { bg:"bg-wellnet-50", text:"text-wellnet-700", border:"border-wellnet-200",bar:"bg-wellnet-500" },
  meat:       { bg:"bg-red-50",     text:"text-red-700",     border:"border-red-200",    bar:"bg-red-500"    },
  dairy:      { bg:"bg-blue-50",    text:"text-blue-700",    border:"border-blue-200",   bar:"bg-blue-500"   },
  vegetables: { bg:"bg-green-50",   text:"text-green-700",   border:"border-green-200",  bar:"bg-green-600"  },
  drinks:     { bg:"bg-purple-50",  text:"text-purple-700",  border:"border-purple-200", bar:"bg-purple-500" },
  special:    { bg:"bg-orange-50",  text:"text-orange-700",  border:"border-orange-200", bar:"bg-orange-500" },
}

const RECIPES: Record<string, { name: string; steps: string }[]> = {
  injera: [
    { name:"Classic injera + misir wot", steps:"Tear injera, scoop misir wot and ayib. Eat together — the teff soaks up the berbere." },
    { name:"Breakfast injera roll",      steps:"Roll injera with scrambled eggs, tomato, and a pinch of berbere. Serve with buna." },
    { name:"Injera pizza (fasting)",     steps:"Lay injera flat, top with gomen, fasolia, kik alicha. Drizzle with olive oil." },
  ],
  misir_wot: [
    { name:"Misir wot fasting bowl", steps:"Serve over injera with shiro and gomen. Add a squeeze of lemon for brightness." },
    { name:"Misir soup",             steps:"Thin with water, add tomato and onion. Simmer 15 min. Serve with dabo." },
  ],
  shiro: [
    { name:"Shiro firfir", steps:"Mix torn injera pieces into hot shiro. Add niter kibbeh. Eat immediately." },
    { name:"Shiro dip",    steps:"Cool shiro, mix with lemon and garlic. Serve as dip with dabo slices." },
  ],
  teff_porridge: [
    { name:"Sweetened genfo", steps:"Cook teff porridge, stir in honey and niter kibbeh. Top with ergo. Great for elders and children." },
  ],
  gomen: [
    { name:"Gomen be tibs", steps:"Sauté gomen with garlic and ginger. Add tibs pieces at the end. Serve with injera." },
    { name:"Fasting gomen", steps:"Cook with onion, garlic, and vegetable oil. Add a squeeze of lemon before serving." },
  ],
  ayib:         [{ name:"Ayib with greens",         steps:"Crumble fresh ayib over gomen or fasolia. The mild cheese balances spicy dishes perfectly." }],
  ergo:         [{ name:"Ergo with honey",           steps:"Serve cold ergo in a clay cup, drizzle with Ethiopian honey. Breakfast staple." }],
  buna:         [{ name:"Ethiopian coffee ceremony", steps:"Roast, grind, and brew in jebena. Serve 3 rounds: Abol, Tona, Bereka. Add sugar or salt." }],
}

const SOURCE_LINKS: Record<string, string> = {
  "EPHI 2025":               "https://www.ephi.gov.et",
  "EPHI EFCT 2025":          "https://www.ephi.gov.et",
  "PMC12524473":             "https://pmc.ncbi.nlm.nih.gov/articles/PMC12524473/",
  "PMC6948299":              "https://pmc.ncbi.nlm.nih.gov/articles/PMC6948299/",
  "PMC8140839":              "https://pmc.ncbi.nlm.nih.gov/articles/PMC8140839/",
  "FAO":                     "https://www.fao.org/faostat/en/#data",
  "USDA":                    "https://fdc.nal.usda.gov/",
  "Heritage Nutrition 2023": "https://heritagenutrition.co.uk/the-ethiopian-dietary-pattern-a-nutritional-blueprint-for-well-being/",
}

const PAGE_SIZE = 30

function scoreColor(score: number) {
  if (score >= 75) return "text-wellnet-600"
  if (score >= 50) return "text-amber-600"
  return "text-red-500"
}

function inflammText(idx: number) {
  if (idx <= -2) return { label: "Strong anti-inflammatory", color: "text-wellnet-600" }
  if (idx === -1) return { label: "Anti-inflammatory",       color: "text-wellnet-600" }
  if (idx === 0)  return { label: "Neutral",                 color: "text-gray-500"    }
  if (idx === 1)  return { label: "Mildly inflammatory",     color: "text-amber-600"   }
  return                 { label: "Inflammatory",            color: "text-red-600"     }
}

function singleFoodScore(food: EthiopianFood): number {
  const fs  = Math.min(food.fiber_g / 25, 1)
  const fes = Math.min(food.fermentation_score / 6, 1)
  const is  = Math.max(0, Math.min(1, (4 - food.inflammatory_index) / 8))
  const ps  = Math.min(food.protein_g / 50, 1)
  return Math.round((fs * 0.4 + fes * 0.3 + is * 0.2 + ps * 0.1) * 100)
}

/**
 * Parse display_name from the API: "Injera teff  [እንጀራ]"
 * Returns { english, amharic } so we can bold the Amharic part independently.
 * Falls back to name_en / name_am if display_name is absent.
 */
function parseDisplayName(food: EthiopianFood): { english: string; amharic: string } {
  const raw = food.display_name || food.name_en
  const bracketMatch = raw.match(/^(.*?)\s*\[([^\]]+)\]\s*$/)
  if (bracketMatch) {
    return {
      english: bracketMatch[1].trim(),
      amharic: bracketMatch[2].trim(),
    }
  }
  // No bracket form — fall back
  return {
    english: food.name_en,
    amharic: food.name_am || "",
  }
}

/**
 * Clean English portion for compact card display:
 * strips trailing descriptor clauses like "raw", "boiled drained without salt", etc.
 */
function shortEnglishName(english: string): string {
  return english
    .split(/\s*(?:—|–)\s*/)[0]   // remove " — subtitle"
    .split(/\s*,\s*(?:raw|boiled|grilled|dried|fresh|peeled|whole|split|flour|stew|sauce)/i)[0]
    .trim()
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function FoodsPage() {
  const router = useRouter()
  const { addFood } = useMealLogStore()

  const [foods,     setFoods]     = useState<EthiopianFood[]>([])
  const [loading,   setLoading]   = useState(true)
  const [query,     setQuery]     = useState("")
  const [category,  setCategory]  = useState("all")
  const [fasting,   setFasting]   = useState(false)
  const [pregnancy, setPregnancy] = useState(false)
  const [diabetes,  setDiabetes]  = useState(false)
  const [selected,  setSelected]  = useState<EthiopianFood | null>(null)
  const [page,      setPage]      = useState(1)

  useEffect(() => {
    foodService.list()
      .then(r => setFoods(extractArray<EthiopianFood>(r.data)))
      .catch(() => toast.error("Could not load food database"))
      .finally(() => setLoading(false))
  }, [])

  // Reset page when filters change
  useEffect(() => { setPage(1) }, [query, category, fasting, pregnancy, diabetes])

  const filtered = useMemo(() => {
    return foods.filter(f => {
      if (category !== "all" && f.category !== category) return false
      if (fasting   && !f.fasting_safe)      return false
      if (pregnancy && !f.pregnancy_safe)    return false
      if (diabetes  && !f.diabetes_friendly) return false
      if (query) {
        const q = query.toLowerCase()
        return (
          f.name_en.toLowerCase().includes(q) ||
          (f.name_am || "").toLowerCase().includes(q) ||
          (f.display_name || "").toLowerCase().includes(q) ||
          f.category.toLowerCase().includes(q) ||
          (f.notes || "").toLowerCase().includes(q)
        )
      }
      return true
    })
  }, [foods, category, query, fasting, pregnancy, diabetes])

  const paginated = useMemo(
    () => filtered.slice(0, page * PAGE_SIZE),
    [filtered, page]
  )

  const handleAddToLog = (food: EthiopianFood) => {
    addFood(food)
    // Use the Amharic name if present, otherwise the clean English name
    const { english, amharic } = parseDisplayName(food)
    toast.success(`${amharic || shortEnglishName(english)} added to your meal`)
    setSelected(null)
    router.push("/dashboard/log")
  }

  const c = (food: EthiopianFood) => CAT_COLOR[food.category] ?? CAT_COLOR.legumes

  return (
    <div className="space-y-5">

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-wellnet-500" />
          Ethiopian Food Database
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {foods.length} verified foods · EPHI 2025, FAO, PMC, USDA & Heritage Nutrition
        </p>
      </div>

      {/* EPHI badge */}
      <div className="flex items-center gap-2.5 bg-green-50 border border-green-200 rounded-xl px-3 py-2.5">
        <span className="text-lg shrink-0">🇪🇹</span>
        <div>
          <div className="text-xs font-semibold text-green-800">
            Powered by EPHI Food Composition Table 2025
          </div>
          <div className="text-[10px] text-green-600 mt-0.5">
            Ethiopia's official nutrition authority · 437 lab-verified foods · per 100g edible portion
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search in English or አማርኛ…"
          className="input pl-9 pr-9"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Category tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => setCategory(cat.id)}
            className={cn(
              "shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all",
              category === cat.id
                ? "bg-gray-900 text-white border-gray-900"
                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
            )}
          >
            {cat.emoji} {cat.label}
          </button>
        ))}
      </div>

      {/* Filter toggles */}
      <div className="flex gap-3 flex-wrap">
        {[
          { label: "✦ Fasting-safe",       val: fasting,   set: setFasting   },
          { label: "🤰 Pregnancy-safe",    val: pregnancy, set: setPregnancy },
          { label: "🩸 Diabetes-friendly", val: diabetes,  set: setDiabetes  },
        ].map(({ label, val, set }) => (
          <button
            key={label}
            onClick={() => set(!val)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all",
              val
                ? "bg-wellnet-500 text-white border-wellnet-500"
                : "bg-white text-gray-600 border-gray-200 hover:border-wellnet-300"
            )}
          >
            {label}
          </button>
        ))}
        <span className="text-xs text-gray-400 self-center">
          {filtered.length} result{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Food grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="h-36 bg-gray-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-10">
          <Leaf className="w-10 h-10 text-gray-200 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No foods match your filters.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {paginated.map(food => {
              const col   = c(food)
              const score = singleFoodScore(food)
              const { english, amharic } = parseDisplayName(food)
              return (
                <button
                  key={food.id}
                  onClick={() => setSelected(food)}
                  className={cn(
                    "text-left p-3.5 rounded-2xl border transition-all hover:shadow-md active:scale-95",
                    col.bg, col.border
                  )}
                >
                  {/* Name — Amharic bold, English below */}
                  {amharic && (
                    <div className={cn("text-sm font-bold leading-tight", col.text)}>
                      {amharic}
                    </div>
                  )}
                  <div className={cn(
                    "text-xs font-medium text-gray-700 leading-tight line-clamp-2",
                    amharic ? "mt-0.5" : "mt-0"
                  )}>
                    {shortEnglishName(english)}
                  </div>

                  {/* Category badge */}
                  <span className={cn(
                    "inline-block text-[9px] font-semibold px-1.5 py-0.5 rounded-full mt-1.5 uppercase tracking-wide",
                    col.bg, col.text
                  )}>
                    {food.category}
                  </span>

                  {/* Nutrition bars */}
                  <div className="mt-2.5 space-y-1">
                    {[
                      { label: "Fiber",   val: food.fiber_g,   max: 25, unit: "g"  },
                      { label: "Protein", val: food.protein_g, max: 50, unit: "g"  },
                      { label: "Iron",    val: food.iron_mg,   max: 18, unit: "mg" },
                    ].map(({ label, val, max, unit }) => (
                      <div key={label}>
                        <div className="flex justify-between text-[9px] text-gray-500 mb-0.5">
                          <span>{label}</span>
                          <span className="font-medium">{val}{unit}</span>
                        </div>
                        <div className="h-1 bg-white/60 rounded-full overflow-hidden">
                          <div
                            className={cn("h-full rounded-full", col.bar)}
                            style={{ width: `${Math.min((val / max) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Flags */}
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {food.fermentation_score > 0 && (
                      <span className="text-[9px] bg-white/70 text-wellnet-700 px-1.5 py-0.5 rounded-full font-medium">
                        🧫 Fermented
                      </span>
                    )}
                    {food.fasting_safe && (
                      <span className="text-[9px] bg-white/70 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">
                        ✦ Fasting
                      </span>
                    )}
                    {food.glycemic_index > 0 && (
                      <span className="text-[9px] bg-white/70 text-gray-600 px-1.5 py-0.5 rounded-full font-medium">
                        GI {food.glycemic_index}
                      </span>
                    )}
                  </div>

                  {/* Gut score */}
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[9px] text-gray-400">Gut score</span>
                    <span className={cn("text-xs font-bold tabular-nums", scoreColor(score))}>
                      {score}/100
                    </span>
                  </div>
                </button>
              )
            })}
          </div>

          {/* Load more */}
          {paginated.length < filtered.length && (
            <button
              onClick={() => setPage(p => p + 1)}
              className="w-full btn-secondary py-3 text-sm flex items-center justify-center gap-2"
            >
              <ChevronDown className="w-4 h-4" />
              Load more ({filtered.length - paginated.length} remaining)
            </button>
          )}
        </>
      )}

      {/* ── Detail modal ──────────────────────────────────────────────────── */}
      {selected && (() => {
        const { english, amharic } = parseDisplayName(selected)
        return (
          <div
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/30"
            onClick={e => { if (e.target === e.currentTarget) setSelected(null) }}
          >
            <div className="bg-white rounded-3xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto">

              {/* Modal header */}
              <div className={cn("px-6 pt-6 pb-4 rounded-t-3xl", c(selected).bg)}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    {/* Amharic name — bold, large */}
                    {amharic && (
                      <div className={cn("text-2xl font-bold mb-1 leading-tight", c(selected).text)}>
                        {amharic}
                      </div>
                    )}
                    {/* English name — clean, no trailing descriptors for the heading */}
                    <div className="text-base font-semibold text-gray-800 leading-snug">
                      {english}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {selected.serving_description}
                    </div>
                  </div>
                  <button
                    onClick={() => setSelected(null)}
                    className="w-8 h-8 rounded-full bg-white/60 flex items-center justify-center shrink-0"
                  >
                    <X className="w-4 h-4 text-gray-600" />
                  </button>
                </div>

                {/* Flags */}
                <div className="flex gap-1.5 mt-3 flex-wrap">
                  <span className={cn("badge-teal border text-xs", c(selected).border, c(selected).text, "bg-white/60")}>
                    {selected.category}
                  </span>
                  {selected.fasting_safe      && <span className="badge-amber text-xs">✦ Fasting-safe</span>}
                  {selected.pregnancy_safe    && <span className="badge-purple text-xs">🤰 Pregnancy-safe</span>}
                  {selected.diabetes_friendly && <span className="badge-teal text-xs">🩸 Diabetes-friendly</span>}
                  {selected.fermentation_score > 0 && <span className="badge-teal text-xs">🧫 Fermented</span>}
                </div>
              </div>

              <div className="px-6 py-5 space-y-5">

                {/* Nutrition table */}
                <div>
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
                    Nutrition per serving
                  </h3>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { label: "Calories",       val: `${selected.calories_kcal} kcal`,                              key: "calories" },
                      { label: "Fiber",          val: `${selected.fiber_g}g`,                                         key: "fiber"    },
                      { label: "Protein",        val: `${selected.protein_g}g`,                                       key: "protein"  },
                      { label: "Iron",           val: `${selected.iron_mg}mg`,                                        key: "iron"     },
                      { label: "Glycemic index", val: selected.glycemic_index > 0 ? String(selected.glycemic_index) : "—", key: "gi" },
                      { label: "Fermentation",   val: `${selected.fermentation_score}/3`,                             key: "ferm"     },
                      { label: "Prebiotics",     val: `${selected.prebiotic_score}/3`,                                key: "pre"      },
                      { label: "Inflammation",   val: inflammText(selected.inflammatory_index).label,                 key: "inf"      },
                    ].map(({ label, val, key }) => (
                      <div key={key} className="bg-gray-50 rounded-xl px-3 py-2.5">
                        <div className="text-[10px] text-gray-400 mb-0.5">{label}</div>
                        <div className={cn(
                          "text-sm font-bold",
                          key === "inf" ? inflammText(selected.inflammatory_index).color : "text-gray-800"
                        )}>
                          {val}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Nutrition bars */}
                <div>
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
                    % of daily target (per serving)
                  </h3>
                  {[
                    { label: "Fiber",   val: selected.fiber_g,   max: 25, unit: "g"  },
                    { label: "Protein", val: selected.protein_g, max: 50, unit: "g"  },
                    { label: "Iron",    val: selected.iron_mg,   max: 18, unit: "mg" },
                  ].map(({ label, val, max, unit }) => (
                    <div key={label} className="mb-2.5">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-600 font-medium">{label}</span>
                        <span className="text-gray-400 tabular-nums">
                          {val}{unit} / {max}{unit}
                          <span className="ml-1 font-bold text-gray-700">
                            ({Math.round((val / max) * 100)}%)
                          </span>
                        </span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={cn("h-full rounded-full transition-all", c(selected).bar)}
                          style={{ width: `${Math.min((val / max) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Notes */}
                {selected.notes && (
                  <div className={cn("rounded-2xl p-4 border", c(selected).bg, c(selected).border)}>
                    <div className={cn("text-xs font-bold mb-1.5 uppercase tracking-wide", c(selected).text)}>
                      Why it's good for your gut
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">{selected.notes}</p>
                  </div>
                )}

                {/* Recipes */}
                {RECIPES[selected.slug]?.length > 0 && (
                  <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
                      Recipe ideas
                    </h3>
                    <div className="space-y-2">
                      {RECIPES[selected.slug].map((r, i) => (
                        <div key={i} className="bg-gray-50 rounded-xl p-3">
                          <div className="text-sm font-semibold text-gray-800 mb-1">{r.name}</div>
                          <p className="text-xs text-gray-500 leading-relaxed">{r.steps}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Sources */}
                {selected.source_citation && (
                  <div>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                      Verified sources
                    </h3>
                    <div className="flex flex-wrap gap-1.5">
                      {selected.source_citation.split(",").map(s => {
                        const src = s.trim()
                        const key = Object.keys(SOURCE_LINKS).find(k => src.includes(k))
                        const url = key ? SOURCE_LINKS[key] : null
                        return url ? (
                          <a
                            key={src}
                            href={url}
                            target="_blank"
                            rel="noopener"
                            className="flex items-center gap-1 badge-teal hover:bg-wellnet-100 transition-colors"
                          >
                            {src} <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ) : (
                          <span key={src} className="badge-teal">{src}</span>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Add to log */}
                <button
                  onClick={() => handleAddToLog(selected)}
                  className="w-full btn-primary flex items-center justify-center gap-2 py-3"
                >
                  <ShoppingCart className="w-4 h-4" />
                  Add to today's meal log
                </button>
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}