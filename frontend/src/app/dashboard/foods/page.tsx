"use client"

import { useEffect, useState, useMemo } from "react"
import { Search, X, ExternalLink, BookOpen, Leaf, ShoppingCart } from "lucide-react"
import { foodService, extractArray } from "@/services/wellnet"
import type { EthiopianFood } from "@/types"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { useMealLogStore } from "@/store"
import FoodName from "@/components/food/FoodName"
import { useRouter } from "next/navigation"

// ── Category config ───────────────────────────────────────────────────────────
const CATEGORIES = [
  { id: "all",           label: "All Foods",        emoji: "🌍" },
  { id: "grains",        label: "Grains & Teff",    emoji: "🌾" },
  { id: "legumes",       label: "Legumes / Wot",    emoji: "🫘" },
  { id: "meat",          label: "Meat & Fish",      emoji: "🍖" }, 
  { id: "dairy_poultry", label: "Dairy & Poultry",  emoji: "🥛" }, 
  { id: "vegetables",    label: "Vegetables",       emoji: "🥦" },
  { id: "drinks",        label: "Beverages",        emoji: "☕" }, 
  { id: "special",       label: "Special/Fats",     emoji: "✨" }, 
] as const

const CAT_COLOR: Record<string, { bg: string; text: string; border: string; bar: string }> = {
  grains:        { bg:"bg-amber-50",   text:"text-amber-700",   border:"border-amber-200",   bar:"bg-amber-500"  },
  legumes:       { bg:"bg-wellnet-50", text:"text-wellnet-700", border:"border-wellnet-200", bar:"bg-wellnet-500" },
  meat:          { bg:"bg-red-50",     text:"text-red-700",     border:"border-red-200",     bar:"bg-red-500"    },
  dairy_poultry: { bg:"bg-blue-50",    text:"text-blue-700",    border:"border-blue-200",    bar:"bg-blue-500"   }, 
  vegetables:    { bg:"bg-green-50",   text:"text-green-700",   border:"border-green-200",   bar:"bg-green-600"  },
  drinks:        { bg:"bg-purple-50",  text:"text-purple-700",  border:"border-purple-200",  bar:"bg-purple-500" }, 
  special:       { bg:"bg-orange-50",  text:"text-orange-700",  border:"border-orange-200",  bar:"bg-orange-500" },
}

// Recipes per slug — curated for the hackathon demo
const RECIPES: Record<string, { name: string; steps: string }[]> = {
  injera:       [
    { name:"Classic injera + misir wot", steps:"Tear injera, scoop misir wot and ayib. Eat together — the teff soaks up the berbere." },
    { name:"Breakfast injera roll",      steps:"Roll injera with scrambled eggs, tomato, and a pinch of berbere. Serve with buna." },
    { name:"Injera pizza (fasting)",     steps:"Lay injera flat, top with gomen, fasolia, kik alicha. Drizzle with olive oil." },
  ],
  misir_wot:    [
    { name:"Misir wot fasting bowl",     steps:"Serve over injera with shiro and gomen. Add a squeeze of lemon for brightness." },
    { name:"Misir soup",                 steps:"Thin with water, add tomato and onion. Simmer 15 min. Serve with dabo." },
  ],
  shiro:        [
    { name:"Shiro firfir",               steps:"Mix torn injera pieces into hot shiro. Add niter kibbeh. Eat immediately." },
    { name:"Shiro dip",                  steps:"Cool shiro, mix with lemon and garlic. Serve as dip with dabo slices." },
  ],
  teff_porridge:[
    { name:"Sweetened genfo",            steps:"Cook teff porridge, stir in honey and niter kibbeh. Top with ergo. Great for elders and children." },
  ],
  gomen:        [
    { name:"Gomen be tibs",              steps:"Sauté gomen with garlic and ginger. Add tibs pieces at the end. Serve with injera." },
    { name:"Fasting gomen",              steps:"Cook with onion, garlic, and vegetable oil. Add a squeeze of lemon before serving." },
  ],
  ayib:         [
    { name:"Ayib with greens",           steps:"Crumble fresh ayib over gomen or fasolia. The mild cheese balances spicy dishes perfectly." },
  ],
  ergo:         [
    { name:"Ergo with honey",            steps:"Serve cold ergo in a clay cup, drizzle with Ethiopian honey. Breakfast staple." },
  ],
  buna:         [
    { name:"Ethiopian coffee ceremony",  steps:"Roast, grind, and brew in jebena. Serve 3 rounds: Abol, Tona, Bereka. Add sugar or salt." },
  ],
}

const SOURCE_LINKS: Record<string, string> = {
  "PMC12524473": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12524473/",
  "PMC6948299":  "https://pmc.ncbi.nlm.nih.gov/articles/PMC6948299/",
  "PMC8140839":  "https://pmc.ncbi.nlm.nih.gov/articles/PMC8140839/",
  "FAO":         "https://www.fao.org/faostat/en/#data",
  "USDA":        "https://fdc.nal.usda.gov/",
  "Heritage Nutrition 2023": "https://heritagenutrition.co.uk/the-ethiopian-dietary-pattern-a-nutritional-blueprint-for-well-being/",
}

function scoreColor(score: number) {
  if (score >= 75) return "text-wellnet-600"
  if (score >= 50) return "text-amber-600"
  return "text-red-500"
}

function inflammText(idx: number) {
  if (idx <= -2) return { label: "Strong anti-inflammatory", color: "text-wellnet-600" }
  if (idx === -1) return { label: "Anti-inflammatory",        color: "text-wellnet-600" }
  if (idx === 0)  return { label: "Neutral",                                 color: "text-gray-500" }
  if (idx === 1)  return { label: "Mildly inflammatory",     color: "text-amber-600" }
  return              { label: "Inflammatory",            color: "text-red-600" }
}

function singleFoodScore(food: EthiopianFood): number {
  const fs  = Math.min((food.fiber_g || 0) / 25, 1)
  const fes = Math.min((food.fermentation_score || 0) / 6, 1)
  const is  = Math.max(0, Math.min(1, (4 - (food.inflammatory_index || 0)) / 8))
  const ps  = Math.min((food.protein_g || 0) / 50, 1)
  return Math.round((fs * 0.4 + fes * 0.3 + is * 0.2 + ps * 0.1) * 100)
}

function foodNameText(food: EthiopianFood) {
  return food.name_en || food.name_am || "Food"
}

export default function FoodsPage() {
  const router = useRouter()
  const { addFood } = useMealLogStore()

  const [foods,      setFoods]      = useState<EthiopianFood[]>([])
  const [loading,    setLoading]    = useState(true)
  const [query,      setQuery]      = useState("")
  const [category,   setCategory]   = useState("all")
  const [fasting,    setFasting]    = useState(false)
  const [pregnancy,  setPregnancy]  = useState(false)
  const [diabetes,   setDiabetes]   = useState(false)
  const [selected,   setSelected]   = useState<EthiopianFood | null>(null)

  useEffect(() => {
    foodService.list()
      .then(r => setFoods(extractArray<EthiopianFood>(r.data)))
      .catch(() => toast.error("Could not load food database"))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    return foods.filter(f => {
      const nameLower = (f.name_en || "").toLowerCase()
      let dbCategory = (f.category || "").toLowerCase().trim()
      
      if (nameLower.includes("carp") || nameLower.includes("fish") || nameLower.includes("fillet")) {
        dbCategory = "meat"
      }

      let resolvedCategory = dbCategory
      if (dbCategory === "dairy") {
        resolvedCategory = "dairy_poultry"
      } else if (dbCategory === "beverage") {
        resolvedCategory = "drinks"
      }

      if (pregnancy) {
        const isAlcoholic = 
          nameLower.includes("vodka") ||
          nameLower.includes("tella") || 
          nameLower.includes("tej") || 
          nameLower.includes("katikala") || 
          nameLower.includes("beer") || 
          nameLower.includes("wine") || 
          nameLower.includes("alcohol")
          
        if (isAlcoholic || !f.pregnancy_safe) return false
      }

      if (category !== "all" && resolvedCategory !== category) return false
      
      if (fasting   && !f.fasting_safe)       return false
      if (diabetes  && !f.diabetes_friendly)  return false

      if (query) {
        const q = query.toLowerCase()
        return (
          f.name_en?.toLowerCase().includes(q) ||
          f.name_am?.toLowerCase().includes(q) ||
          f.notes?.toLowerCase().includes(q)
        )
      }
      
      return true
    })
  }, [foods, category, query, fasting, pregnancy, diabetes])

  // ── FIX TS(2345): Explicit lookup handling string/number variants cleanly ──
  const handleAddToLog = (food: EthiopianFood) => {
    // Normalizing the payload configuration guarantees the exact primitive type matches requirements
    const typeSafeFood = {
      ...food,
      id: String(food.id)
    }
    addFood(typeSafeFood)
    toast.success(`${foodNameText(food)} added to your meal log`)
    setSelected(null)
    router.push("/dashboard/log")
  }

  const c = (food: EthiopianFood) => {
    const nameLower = (food.name_en || "").toLowerCase()
    let rawCat = (food.category || "").toLowerCase().trim()
    
    if (nameLower.includes("carp") || nameLower.includes("fish") || nameLower.includes("fillet")) {
      rawCat = "meat"
    }

    let resolvedKey = rawCat
    if (rawCat === "dairy") resolvedKey = "dairy_poultry"
    if (rawCat === "beverage") resolvedKey = "drinks"
    
    return CAT_COLOR[resolvedKey] ?? CAT_COLOR.legumes
  }
  
  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-wellnet-500" />
          Ethiopian Food Database
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          {foods.length} verified foods · sourced from FAO, PMC, USDA & Heritage Nutrition
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search by name, Amharic, or category…"
          className="w-full bg-white border border-gray-200 rounded-xl py-2 pl-9 pr-9 text-sm focus:outline-none focus:border-wellnet-400 transition-colors"
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
                ? "bg-gray-900 text-white border-gray-900 shadow-sm"
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
          { label: "✦ Fasting-safe",        val: fasting,   set: setFasting   },
          { label: "🤰 Pregnancy-safe",    val: pregnancy, set: setPregnancy },
          { label: "🩸 Diabetes-friendly", val: diabetes,  set: setDiabetes  },
        ].map(({ label, val, set }) => (
          <button
            key={label}
            onClick={() => set(!val)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all",
              val
                ? "bg-wellnet-500 text-white border-wellnet-500 shadow-sm"
                : "bg-white text-gray-600 border-gray-200 hover:border-wellnet-300"
            )}
          >
            {label}
          </button>
        ))}
        <span className="text-xs text-gray-400 self-center font-medium">
          {filtered.length} result{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Food grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[...Array(9)].map((_, i) => (
            <div key={i} className="h-36 bg-gray-50 border border-gray-100 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-12 border border-dashed rounded-2xl bg-gray-50/50">
          <Leaf className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500 font-medium">No foods match your active configuration matrices.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {filtered.map(food => {
            const col   = c(food)
            const score = singleFoodScore(food)
            return (
              <button
                key={String(food.id)}
                onClick={() => setSelected(food)}
                className={cn(
                  "text-left p-3.5 rounded-2xl border transition-all hover:shadow-md hover:-translate-y-0.5 active:scale-95 flex flex-col justify-between",
                  col.bg, col.border
                )}
              >
                <div className="w-full">
                  <FoodName food={food} className="leading-snug line-clamp-2" />

                  <span className={cn(
                    "inline-block text-[9px] font-bold px-2 py-0.5 rounded-md mt-2 uppercase tracking-wider",
                    "bg-white/80 backdrop-blur-sm shadow-sm border border-black/5", col.text
                  )}>
                    {food.category || "General"}
                  </span>

                  {/* Top 3 nutrition bars */}
                  <div className="mt-3 space-y-1.5">
                    {[
                      { label: "Fiber",   val: food.fiber_g,   max: 25 },
                      { label: "Protein", val: food.protein_g, max: 50 },
                      { label: "Iron",    val: food.iron_mg,   max: 18 },
                    ].map(({ label, val, max }) => (
                      <div key={label}>
                        <div className="flex justify-between text-[9px] text-gray-500 mb-0.5 font-medium">
                          <span>{label}</span>
                          <span className="font-semibold tabular-nums">{val || 0}g</span>
                        </div>
                        <div className="h-1 bg-white/60 rounded-full overflow-hidden">
                          <div
                            className={cn("h-full rounded-full transition-all duration-300", col.bar)}
                            style={{ width: `${Math.min(((val || 0) / max) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="w-full mt-3">
                  {/* Bottom chips flags block */}
                  <div className="flex gap-1 flex-wrap">
                    {(food.fermentation_score || 0) > 0 && (
                      <span className="text-[9px] bg-white/90 shadow-sm border border-black/5 text-wellnet-700 px-1.5 py-0.5 rounded-md font-semibold">
                        🧫 Fermented
                      </span>
                    )}
                    {food.fasting_safe && (
                      <span className="text-[9px] bg-white/90 shadow-sm border border-black/5 text-amber-700 px-1.5 py-0.5 rounded-md font-semibold">
                        ✦ Fasting
                      </span>
                    )}
                    {(food.glycemic_index || 0) > 0 && (
                      <span className="text-[9px] bg-white/90 shadow-sm border border-black/5 text-gray-600 px-1.5 py-0.5 rounded-md font-semibold tabular-nums">
                        GI {food.glycemic_index}
                      </span>
                    )}
                  </div>

                  {/* Gut contribution output indicators */}
                  <div className="mt-2.5 pt-2 border-t border-black/5 flex items-center justify-between">
                    <span className="text-[9px] text-gray-400 font-medium">Gut Index</span>
                    <span className={cn("text-xs font-bold tabular-nums", scoreColor(score))}>
                      {score}/100
                    </span>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}

     {/* ── Detail modal ────────────────────────────────────────── */}
{selected && (
  <div
    className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
    onClick={e => { if (e.target === e.currentTarget) setSelected(null) }}
  >
    <div className="bg-white rounded-3xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto border border-gray-100">

      {/* Modal header */}
      <div className={cn("px-6 pt-6 pb-4 rounded-t-3xl border-b border-black/5", c(selected).bg)}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <FoodName food={selected} className="leading-snug text-lg font-bold text-gray-900" />
            <div className="text-xs text-gray-500 mt-0.5 font-medium">
              {selected.serving_description || "Standard 100g portion sizing"}
            </div>
          </div>
          <button
            onClick={() => setSelected(null)}
            className="w-8 h-8 rounded-full bg-white/80 shadow-sm border border-black/5 flex items-center justify-center shrink-0 hover:bg-white transition-colors"
          >
            <X className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        {/* Quick flags array list */}
        <div className="flex gap-1.5 mt-3.5 flex-wrap">
          <span className={cn("text-xs font-bold px-2.5 py-0.5 rounded-md border shadow-sm bg-white/80 capitalize", c(selected).text, c(selected).border)}>
            {selected.category || "General Food"}
          </span>
          {selected.fasting_safe      && <span className="text-xs font-semibold bg-amber-100/80 border border-amber-200 text-amber-800 px-2.5 py-0.5 rounded-md shadow-sm">✦ Fasting-safe</span>}
          {selected.pregnancy_safe    && <span className="text-xs font-semibold bg-purple-100/80 border border-purple-200 text-purple-800 px-2.5 py-0.5 rounded-md shadow-sm">🤰 Pregnancy-safe</span>}
          {selected.diabetes_friendly && <span className="text-xs font-semibold bg-teal-100/80 border border-teal-200 text-teal-800 px-2.5 py-0.5 rounded-md shadow-sm">🩸 Diabetes-friendly</span>}
          {(selected.fermentation_score || 0) > 0 && <span className="text-xs font-semibold bg-wellnet-100/80 border border-wellnet-200 text-wellnet-800 px-2.5 py-0.5 rounded-md shadow-sm">🧫 Fermented</span>}
        </div>
      </div>

      <div className="px-6 py-5 space-y-5">
        {/* Nutritional Breakdown Grid */}
        <div>
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
            Nutritional Facts
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Calories",      val: `${selected.calories_kcal || 0} kcal`,               key: "calories" },
              { label: "Fiber",          val: `${selected.fiber_g || 0}g`,                        key: "fiber" },
              { label: "Protein",        val: `${selected.protein_g || 0}g`,                       key: "protein" },
              { label: "Fat",            val: `${selected.fat_g ?? 0}g`,                          key: "fat" },
              { label: "Carbohydrates", val: `${selected.cho_g ?? 0}g`,                          key: "cho" },
              { label: "Iron",          val: `${selected.iron_mg || 0}mg`,                        key: "iron" },
              { label: "Glycemic index",val: (selected.glycemic_index || 0) > 0 ? String(selected.glycemic_index) : "—", key: "gi" },
              { label: "Fermentation",  val: `${selected.fermentation_score || 0}/3`,   key: "ferm" },
              { label: "Prebiotics",    val: `${selected.prebiotic_score || 0}/3`,      key: "pre" },
              { label: "Inflammation Index", val: inflammText(selected.inflammatory_index || 0).label, key: "inf" },
            ].map(({ label, val, key }) => (
              <div key={key} className="bg-gray-50 border border-gray-100 rounded-xl px-3 py-2.5">
                <div className="text-[10px] text-gray-400 font-semibold uppercase mb-0.5 tracking-wider">{label}</div>
                <div className={cn(
                  "text-sm font-bold",
                  key === "inf" ? inflammText(selected.inflammatory_index || 0).color : "text-gray-800"
                )}>
                  {val}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Daily Progress Target Tracks */}
        <div>
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
            Contribution to your daily goals
          </h3>
          {[
            { label: "Fiber",     val: selected.fiber_g,   max: 25, unit: "g"  },
            { label: "Protein",   val: selected.protein_g, max: 50, unit: "g"  },
            { label: "Iron",      val: selected.iron_mg,   max: 18, unit: "mg" },
          ].map(({ label, val, max, unit }) => (
            <div key={label} className="mb-2.5">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-600 font-semibold">{label}</span>
                <span className="text-gray-400 font-medium tabular-nums">
                  {val || 0}{unit} / {max}{unit}
                  <span className="ml-1.5 font-bold text-gray-700">
                    ({Math.round(((val || 0) / max) * 100)}%)
                  </span>
                </span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden border border-gray-200/40">
                <div
                  className={cn("h-full rounded-full transition-all duration-500", c(selected).bar)}
                  style={{ width: `${Math.min(((val || 0) / max) * 100, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Health & Gut Insight Card 
        {selected.notes && (
          <div className={cn("rounded-2xl p-4 border shadow-sm", c(selected).bg, c(selected).border)}>
            <div className={cn("text-xs font-bold mb-1.5 uppercase tracking-wider", c(selected).text)}>
              Gut Health Insight
            </div>
            <p className="text-sm text-gray-700 leading-relaxed font-medium">{selected.notes}</p>
          </div>
        )}  */}

        {/* Meal Preparation Ideas Block
        {selected.slug && RECIPES[selected.slug]?.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
              Preparation & Serving Ideas
            </h3>
            <div className="space-y-2">
              {RECIPES[selected.slug].map((r, i) => (
                <div key={i} className="bg-gray-50 border border-gray-100 rounded-xl p-3 shadow-sm">
                  <div className="text-sm font-bold text-gray-800 mb-1">
                    {r.name}
                  </div>
                  <p className="text-xs text-gray-500 font-medium leading-relaxed">{r.steps}</p>
                </div>
              ))}
            </div>
          </div>
        )}  

        {/* EPHI validation source badge */}
        {selected.source === "ephi" && (
          <div className="flex items-center gap-2 bg-blue-50/80 border border-blue-100 rounded-xl px-3 py-2.5 shadow-sm">
            <span className="text-blue-600 text-xs font-extrabold tracking-wider bg-white px-1.5 py-0.5 rounded border border-blue-200 shrink-0">EPHI 2025</span>
            <span className="text-blue-700 text-[11px] font-semibold leading-tight">
              Verified by the Ethiopian Public Health Institute Guidelines
            </span>
          </div>
        )}

        {/* Reference Citations */}
        {selected.source_citation && (
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
              Source Documentation
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {selected.source_citation.split(",").map(s => {
                const src  = s.trim()
                const key  = Object.keys(SOURCE_LINKS).find(k => src.includes(k))
                const url  = key ? SOURCE_LINKS[key] : null
                return url ? (
                  <a
                    key={src}
                    href={url}
                    target="_blank"
                    rel="noopener"
                    className="flex items-center gap-1 bg-teal-50 border border-teal-200 text-teal-800 px-2.5 py-1 rounded-md text-xs font-semibold hover:bg-wellnet-100 transition-colors shadow-sm"
                  >
                    {src} <ExternalLink className="w-2.5 h-2.5 opacity-70" />
                  </a>
                ) : (
                  <span key={src} className="bg-gray-50 border border-gray-200 text-gray-600 px-2.5 py-1 rounded-md text-xs font-semibold shadow-sm">
                    {src}
                  </span>
                )
              })}
            </div>
          </div>
        )}

        {/* Primary CTA Action Button */}
        <button
          onClick={() => handleAddToLog(selected)}
          className="w-full bg-wellnet-500 hover:bg-wellnet-600 font-bold text-white flex items-center justify-center gap-2 py-3.5 rounded-xl text-sm shadow-md transition-all active:scale-[0.99]"
        >
          <ShoppingCart className="w-4 h-4" />
          <span>Add to Daily Meal Log</span>
        </button>
      </div>
    </div>
  </div>
)}    </div>
  )
}
