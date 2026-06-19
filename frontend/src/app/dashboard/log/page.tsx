// frontend/src/app/dashboard/log/page.tsx
"use client"
import { useEffect, useState, useMemo } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { ChevronRight, ChevronDown, Loader2, X } from "lucide-react"
import FoodButton from "@/components/food/FoodButton"
import GutScoreRing from "@/components/wellness/GutScoreRing"
import { foodService, extractArray } from "@/services/wellnet"
import { useMealLogStore, useAuthStore } from "@/store"
import type { EthiopianFood, MealType } from "@/types"
import { cn, todayISO } from "@/lib/utils"

// ── FIXED CATEGORIES ARRAY ──────────────────────────────────────────────────
const CATEGORIES = [
  { id: "grains",         label: "Grains",         emoji: "🌾" },
  { id: "legumes",        label: "Legumes",        emoji: "🫘" },
  { id: "meat",           label: "Meat & Fish",    emoji: "🍖" }, // UI label expanded to include Group 09
  { id: "dairy_poultry",  label: "Dairy & Poultry", emoji: "🥛" },
  { id: "vegetables",     label: "Vegetables",     emoji: "🥦" },
  { id: "drinks",         label: "Drinks",         emoji: "☕" },
  { id: "special",        label: "Special",        emoji: "✨" },
] as const

const MEAL_TYPES: { id: MealType; label: string; emoji: string }[] = [
  { id: "breakfast", label: "Breakfast", emoji: "🌅" },
  { id: "lunch",     label: "Lunch",     emoji: "☀️"  },
  { id: "dinner",    label: "Dinner",    emoji: "🌙"  },
  { id: "snack",     label: "Snack",     emoji: "🍎"  },
]

// ── TYPE-SAFE LIVE NUTRITION MATH ───────────────────────────────────────────
function computeScore(selectedItems: Array<{ food: EthiopianFood; servings: number }>) {
  if (!selectedItems.length) {
    return { score: 0, fiber: 0, ferm: 0, inflam: 0, protein: 0 }
  }

  let totalFiber = 0
  let totalFerm = 0
  let totalInflam = 0
  let totalProtein = 0

  // Accumulate macronutrients properly weighted against dynamic tracking quantities
  selectedItems.forEach(({ food, servings }) => {
    const multiplier = servings || 1
    totalFiber += (food.fiber_g || 0) * multiplier
    totalFerm += (food.fermentation_score || 0) * multiplier
    totalInflam += (food.inflammatory_index || 0) * multiplier
    totalProtein += (food.protein_g || 0) * multiplier
  })

  // Normalize metrics vectors to build live baseline target lines
  const fiberScore = Math.min(totalFiber / 25, 1)
  const fermScore = Math.min(totalFerm / 6, 1)
  const inflamScore = Math.max(0, Math.min(1, (4 - totalInflam) / 8))
  const proteinScore = Math.min(totalProtein / 50, 1)

  // Weighted Composition Matrix (40% Fiber, 30% Fermentation, 20% Anti-Inflammation, 10% Protein)
  const finalScore = Math.round(
    (fiberScore * 0.40 + fermScore * 0.30 + inflamScore * 0.20 + proteinScore * 0.10) * 100
  )

  return {
    score: finalScore,
    fiber: Math.round(totalFiber * 10) / 10,
    ferm: Math.round(totalFerm * 10) / 10,
    inflam: totalInflam,
    protein: Math.round(totalProtein),
  }
}

const PAGE_SIZE = 20

export default function LogPage() {
  const router = useRouter()
  const { profile } = useAuthStore()
  const { selectedFoods, activeCategory, toggleFood, setCategory, clearSelection } = useMealLogStore()

  const [allFoods, setAllFoods] = useState<EthiopianFood[]>([])
  const [mealType, setMealType] = useState<MealType>("lunch")
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)

  const isFasting = profile?.is_fasting_season ?? false
  const isPregnant = profile?.is_pregnant ?? false

  useEffect(() => {
    foodService.list()
      .then(r => setAllFoods(extractArray<EthiopianFood>(r.data)))
      .catch(() => toast.error("Could not load food list"))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { 
    setVisibleCount(PAGE_SIZE) 
  }, [activeCategory])

  // ── PRE-COMPUTED CATEGORY MAP QUANTITIES (OPTIMIZED GRAPH PERFORMANCE) ───
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    CATEGORIES.forEach(c => { counts[c.id] = 0 })
    
    allFoods.forEach(f => {
      const dbCat = (f.category || "").toLowerCase().trim()
      const resolvedCat = dbCat === "dairy" ? "dairy_poultry" : dbCat
      if (resolvedCat in counts) {
        // Quantify item availability matching user profile status parameters
        if (isFasting && !f.fasting_safe) return
        if (isPregnant && !f.pregnancy_safe) return
        counts[resolvedCat]++
      }
    })
    return counts
  }, [allFoods, isFasting, isPregnant])

  // ── DEEP TRUST FILTERING ENGINE ───────────────────────────────────────────
  const filteredFoods = useMemo(() => {
    return allFoods.filter(f => {
      const dbCategory = (f.category || "").toLowerCase().trim()
      const resolvedCategory = dbCategory === "dairy" ? "dairy_poultry" : dbCategory

      if (resolvedCategory !== activeCategory) return false
      if (isFasting && !f.fasting_safe) return false
      if (isPregnant && !f.pregnancy_safe) return false
      return true
    })
  }, [allFoods, activeCategory, isFasting, isPregnant])

  const visibleFoods = filteredFoods.slice(0, visibleCount)
  const selectedList = Array.from(selectedFoods.values())
  const computed = computeScore(selectedList)

  const SUB = [
    { label: "Fiber", pct: Math.min((computed.fiber / 25) * 100, 100) },
    { label: "Fermentation", pct: Math.min((computed.ferm / 6) * 100, 100) },
    { label: "Inflammation", pct: Math.max(0, Math.min(((4 - computed.inflam) / 8) * 100, 100)) },
    { label: "Protein", pct: Math.min((computed.protein / 50) * 100, 100) },
  ]

  const handleSubmit = async () => {
    if (!selectedList.length) { 
      toast.error("Select at least one food first")
      return 
    }
    setSubmitting(true)
    try {
      const res = await foodService.logMeal({
        date: todayISO(),
        meal_type: mealType,
        foods: selectedList.map(({ food, servings }) => ({ 
          food_id: String(food.id), 
          servings: servings || 1 
        })),
      })
      clearSelection()
      toast.success(`Logged! Score: ${res.data.gut_score} — ${res.data.label}`)
      router.push("/dashboard")
    } catch (err: any) {
      const msg = err?.response?.data?.error || "Could not log meal. Please try again."
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-bold text-gray-900 tracking-tight">
          How are you nourishing yourself?
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Tap foods to build your meal — your score updates live
        </p>
      </div>

      {/* Meal type selection row */}
      <div className="flex gap-2 flex-wrap">
        {MEAL_TYPES.map(mt => (
          <button
            key={mt.id}
            onClick={() => setMealType(mt.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium border transition-all",
              mealType === mt.id
                ? "bg-wellnet-500 text-white border-wellnet-500 shadow-sm"
                : "bg-white text-gray-600 border-gray-200 hover:border-wellnet-300"
            )}
          >
            {mt.emoji} {mt.label}
          </button>
        ))}
      </div>

      {/* High-Precision Living Score Panel */}
      <div className="card bg-white border border-gray-100 shadow-sm p-4 rounded-2xl">
        <div className="flex items-start gap-4">
          <GutScoreRing score={computed.score} size="sm" animate />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">
              {selectedList.length
                ? `${selectedList.length} food${selectedList.length > 1 ? "s" : ""} configured`
                : "Select items from the composition tables"}
            </p>
            {SUB.map(({ label, pct }) => (
              <div key={label} className="mb-1.5">
                <div className="flex justify-between text-[10px] text-gray-500 mb-0.5 font-medium">
                  <span>{label}</span>
                  <span>{Math.round(pct)}%</span>
                </div>
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-wellnet-500 rounded-full transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Selected Bilingual Item Micro Chips */}
        {selectedList.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-gray-100">
            {selectedList.map(({ food }) => (
              <button
                key={food.id}
                onClick={() => toggleFood(food)}
                className="flex items-center gap-1.5 text-xs bg-wellnet-50 text-wellnet-700 px-2.5 py-1 rounded-full hover:bg-red-50 hover:text-red-600 transition-colors border border-wellnet-100/50"
              >
                <span className="font-medium">
                  {food.name_am || food.name_en.split(" — ")[0]}
                </span>
                <X className="w-3 h-3 opacity-60" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* High-density Category Slider tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {CATEGORIES.map(cat => {
          const count = categoryCounts[cat.id] || 0
          return (
            <button
              key={cat.id}
              onClick={() => setCategory(cat.id)}
              className={cn(
                "shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all",
                activeCategory === cat.id
                  ? "bg-gray-900 text-white border-gray-900 shadow-sm"
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
              )}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
              <span className={cn(
                "text-[9px] px-1.5 py-0.5 rounded-md font-bold transition-colors",
                activeCategory === cat.id ? "bg-white/20 text-white" : "bg-gray-100 text-gray-400"
              )}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Reactive Interactive Food Grid Selection Layer */}
      {loading ? (
        <div className="grid grid-cols-2 gap-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-50 border border-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filteredFoods.length === 0 ? (
        <div className="card text-center py-12 text-sm text-gray-400 border border-dashed rounded-2xl bg-gray-50/50">
          {isFasting
            ? "✦ Orthodox fasting restrictions apply — non-compliant foods hidden."
            : isPregnant
            ? "🤰 Clinical pregnancy safety guidelines apply — high risk items hidden."
            : "No active records found in this category index."}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            {visibleFoods.map(food => (
              <FoodButton
                key={food.id}
                food={food}
                selected={selectedFoods.has(String(food.id))}
                onToggle={toggleFood}
              />
            ))}
          </div>

          {/* Pagination Anchor Control */}
          {visibleCount < filteredFoods.length && (
            <button
              onClick={() => setVisibleCount(c => c + PAGE_SIZE)}
              className="w-full bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 py-2.5 rounded-xl text-xs font-medium flex items-center justify-center gap-1.5 transition-colors shadow-sm"
            >
              <ChevronDown className="w-3.5 h-3.5" />
              Show more ({filteredFoods.length - visibleCount} remaining in {activeCategory})
            </button>
          )}
        </>
      )}

      {/* Dynamic Cohort Mode Alert Banners */}
      {(isFasting || isPregnant) && (
        <div className="card bg-amber-50/60 border border-amber-100/70 p-3 rounded-xl flex items-start gap-2">
          <span className="text-xs text-amber-800 font-medium leading-relaxed">
            {isFasting  && "✦ Operational Framework: Orthodox Fasting Mode active. All dairy, poultry, and animal-muscle proteins are automatically restricted from menu matrices."}
            {isFasting && isPregnant && <br />}
            {isPregnant && "🤰 Operational Framework: Gestational Care Mode active. Higher-risk categories including unpasteurized metrics, raw foods, and regional ferments are suppressed."}
          </span>
        </div>
      )}

      {/* Primary Execution Command Button */}
      <button
        onClick={handleSubmit}
        disabled={submitting || !selectedList.length}
        className={cn(
          "w-full bg-wellnet-500 text-white hover:bg-wellnet-600 font-semibold py-3.5 rounded-xl text-sm flex items-center justify-center gap-2 shadow-md transition-all active:scale-[0.99]",
          (submitting || !selectedList.length) && "opacity-40 cursor-not-allowed transform-none"
        )}
      >
        {submitting ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Analyzing meal parameters…</span>
          </>
        ) : (
          <>
            <span>Log meal & commit to wellness index</span>
            <ChevronRight className="w-4 h-4" />
          </>
        )}
      </button>
    </div>
  )
}