"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { ChevronRight, ChevronDown, Loader2, X } from "lucide-react"
import FoodButton from "@/components/food/FoodButton"
import GutScoreRing from "@/components/wellness/GutScoreRing"
import { foodService, extractArray } from "@/services/wellnet"
import { useMealLogStore, useAuthStore } from "@/store"
import type { EthiopianFood, MealType } from "@/types"
import { cn, todayISO } from "@/lib/utils"

const CATEGORIES = [
  { id: "grains",     label: "Grains",     emoji: "🌾" },
  { id: "legumes",    label: "Legumes",    emoji: "🫘" },
  { id: "meat",       label: "Meat",       emoji: "🍖" },
  { id: "dairy",      label: "Dairy",      emoji: "🥛" },
  { id: "vegetables", label: "Vegetables", emoji: "🥦" },
  { id: "drinks",     label: "Drinks",     emoji: "☕" },
  { id: "special",    label: "Special",    emoji: "✨" },
]

const MEAL_TYPES: { id: MealType; label: string; emoji: string }[] = [
  { id: "breakfast", label: "Breakfast", emoji: "🌅" },
  { id: "lunch",     label: "Lunch",     emoji: "☀️"  },
  { id: "dinner",    label: "Dinner",    emoji: "🌙"  },
  { id: "snack",     label: "Snack",     emoji: "🍎"  },
]

function computeScore(foods: EthiopianFood[]) {
  if (!foods.length) return { score: 0, fiber: 0, ferm: 0, inflam: 0, protein: 0 }
  const fiber  = foods.reduce((a, f) => a + f.fiber_g,           0)
  const ferm   = foods.reduce((a, f) => a + f.fermentation_score, 0)
  const inflam = foods.reduce((a, f) => a + f.inflammatory_index, 0)
  const prot   = foods.reduce((a, f) => a + f.protein_g,          0)
  const fs  = Math.min(fiber  / 25, 1)
  const fes = Math.min(ferm   / 6,  1)
  const is  = Math.max(0, Math.min(1, (4 - inflam) / 8))
  const ps  = Math.min(prot   / 50, 1)
  return {
    score:   Math.round((fs * 0.40 + fes * 0.30 + is * 0.20 + ps * 0.10) * 100),
    fiber:   Math.round(fiber * 10) / 10,
    ferm:    Math.round(ferm  * 10) / 10,
    inflam,
    protein: Math.round(prot),
  }
}

const PAGE_SIZE = 20

export default function LogPage() {
  const router = useRouter()
  const { profile } = useAuthStore()
  const { selectedFoods, activeCategory, toggleFood, setCategory, clearSelection } = useMealLogStore()

  const [allFoods,    setAllFoods]    = useState<EthiopianFood[]>([])
  const [mealType,    setMealType]    = useState<MealType>("lunch")
  const [loading,     setLoading]     = useState(true)
  const [submitting,  setSubmitting]  = useState(false)
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)

  const isFasting  = profile?.is_fasting_season ?? false
  const isPregnant = profile?.is_pregnant        ?? false

  useEffect(() => {
    foodService.list()
      .then(r => setAllFoods(extractArray<EthiopianFood>(r.data)))
      .catch(() => toast.error("Could not load food list"))
      .finally(() => setLoading(false))
  }, [])

  // Reset pagination when category changes
  useEffect(() => { setVisibleCount(PAGE_SIZE) }, [activeCategory])

  const filteredFoods = allFoods.filter(f => {
    if (f.category !== activeCategory)          return false
    if (isFasting  && !f.fasting_safe)          return false
    if (isPregnant && !f.pregnancy_safe)        return false
    return true
  })

  const visibleFoods = filteredFoods.slice(0, visibleCount)

  const selectedList = Array.from(selectedFoods.values())
  const computed     = computeScore(selectedList.map(v => v.food))

  const SUB = [
    { label: "Fiber",        pct: Math.min((computed.fiber   / 25) * 100, 100) },
    { label: "Fermentation", pct: Math.min((computed.ferm    / 6)  * 100, 100) },
    { label: "Inflammation", pct: Math.max(0, Math.min(((4 - computed.inflam) / 8) * 100, 100)) },
    { label: "Protein",      pct: Math.min((computed.protein / 50) * 100, 100) },
  ]

  const handleSubmit = async () => {
    if (!selectedList.length) { toast.error("Select at least one food first"); return }
    setSubmitting(true)
    try {
      const res = await foodService.logMeal({
        date:      todayISO(),
        meal_type: mealType,
        foods:     selectedList.map(({ food, servings }) => ({ food_id: food.id, servings })),
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
        <h1 className="text-xl font-bold text-gray-900">
          How are you nourishing yourself?
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Tap foods to build your meal — your score updates live
        </p>
      </div>

      {/* Meal type */}
      <div className="flex gap-2 flex-wrap">
        {MEAL_TYPES.map(mt => (
          <button
            key={mt.id}
            onClick={() => setMealType(mt.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-medium border transition-all",
              mealType === mt.id
                ? "bg-wellnet-500 text-white border-wellnet-500"
                : "bg-white text-gray-600 border-gray-200 hover:border-wellnet-300"
            )}
          >
            {mt.emoji} {mt.label}
          </button>
        ))}
      </div>

      {/* Live score */}
      <div className="card">
        <div className="flex items-start gap-4">
          <GutScoreRing score={computed.score} size="sm" animate />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-500 mb-2">
              {selectedList.length
                ? `${selectedList.length} food${selectedList.length > 1 ? "s" : ""} selected`
                : "Select foods below"}
            </p>
            {SUB.map(({ label, pct }) => (
              <div key={label} className="mb-1.5">
                <div className="flex justify-between text-[10px] text-gray-400 mb-0.5">
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

        {/* Selected chips */}
        {selectedList.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-gray-100">
            {selectedList.map(({ food }) => (
              <button
                key={food.id}
                onClick={() => toggleFood(food)}
                className="flex items-center gap-1 text-xs bg-wellnet-50 text-wellnet-700 px-2.5 py-1 rounded-full hover:bg-red-50 hover:text-red-600 transition-colors"
              >
                {food.name_am || food.name_en.split(" (")[0]}
                <X className="w-2.5 h-2.5" />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Category tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => setCategory(cat.id)}
            className={cn(
              "shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all",
              activeCategory === cat.id
                ? "bg-gray-900 text-white border-gray-900"
                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
            )}
          >
            {cat.emoji} {cat.label}
            {/* Show count per category */}
            <span className={cn(
              "text-[9px] px-1 py-0.5 rounded-full",
              activeCategory === cat.id ? "bg-white/20" : "bg-gray-100 text-gray-400"
            )}>
              {allFoods.filter(f => f.category === cat.id).length}
            </span>
          </button>
        ))}
      </div>

      {/* Food grid */}
      {loading ? (
        <div className="grid grid-cols-2 gap-2">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filteredFoods.length === 0 ? (
        <div className="card text-center py-8 text-sm text-gray-400">
          {isFasting
            ? "No fasting-safe foods in this category"
            : isPregnant
            ? "No pregnancy-safe foods here"
            : "No foods in this category"}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            {visibleFoods.map(food => (
              <FoodButton
                key={food.id}
                food={food}
                selected={selectedFoods.has(food.id)}
                onToggle={toggleFood}
              />
            ))}
          </div>

          {/* Load more */}
          {visibleCount < filteredFoods.length && (
            <button
              onClick={() => setVisibleCount(c => c + PAGE_SIZE)}
              className="w-full btn-secondary py-2.5 text-xs flex items-center justify-center gap-1.5"
            >
              <ChevronDown className="w-3.5 h-3.5" />
              Show more ({filteredFoods.length - visibleCount} remaining in {activeCategory})
            </button>
          )}
        </>
      )}

      {/* Fasting / pregnancy notice */}
      {(isFasting || isPregnant) && (
        <div className="card bg-amber-50 border-amber-100 py-2.5">
          <p className="text-xs text-amber-700 font-medium">
            {isFasting  && "✦ Fasting mode — non-fasting foods are hidden"}
            {isPregnant && "🤰 Pregnancy mode — unsafe foods are hidden"}
          </p>
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={submitting || !selectedList.length}
        className={cn(
          "w-full btn-primary flex items-center justify-center gap-2 py-3 text-sm font-semibold",
          (submitting || !selectedList.length) && "opacity-50 cursor-not-allowed"
        )}
      >
        {submitting
          ? <><Loader2 className="w-4 h-4 animate-spin" /> Analysing meal…</>
          : <>Log meal & get gut score <ChevronRight className="w-4 h-4" /></>
        }
      </button>
    </div>
  )
}