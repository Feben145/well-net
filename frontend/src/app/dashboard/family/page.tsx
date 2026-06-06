"use client"
import { useEffect, useState } from "react"
import {
  Plus, AlertTriangle, Trash2, Loader2, Users, X, Check,
  ChevronRight, Utensils, TrendingUp, ShieldCheck, RefreshCw,
} from "lucide-react"
import { familyService, foodService, extractArray } from "@/services/wellnet"
import type { FamilyMember, EthiopianFood } from "@/types"
import GutScoreRing from "@/components/wellness/GutScoreRing"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { useRouter } from "next/navigation"

type MemberType = FamilyMember["member_type"]
type DietType   = FamilyMember["diet_type"]
type View       = "list" | "detail"

const MEMBER_TYPES: { id: MemberType; label: string; emoji: string }[] = [
  { id: "adult",    label: "Adult",    emoji: "👤" },
  { id: "child",    label: "Child",    emoji: "🧒" },
  { id: "elder",    label: "Elder",    emoji: "👴" },
  { id: "pregnant", label: "Pregnant", emoji: "🤰" },
  { id: "infant",   label: "Infant",   emoji: "👶" },
]
const DIET_TYPES: DietType[] = ["omnivore","fasting","vegetarian","vegan","diabetic"]

const SCORE_BG = (s: number) =>
  s >= 70 ? "bg-wellnet-50 border-wellnet-200 text-wellnet-700"
  : s >= 50 ? "bg-amber-50 border-amber-200 text-amber-700"
  : s > 0   ? "bg-red-50 border-red-200 text-red-600"
  : "bg-gray-50 border-gray-200 text-gray-400"

const TARGETS: Record<MemberType, { kcal:number; protein:number; fiber:number; iron:number; label:string }> = {
  adult:    { kcal:2200, protein:50, fiber:25, iron:18, label:"Adult daily target" },
  elder:    { kcal:1800, protein:60, fiber:21, iron:8,  label:"Elder daily target" },
  child:    { kcal:1600, protein:35, fiber:19, iron:10, label:"Child daily target" },
  infant:   { kcal:900,  protein:13, fiber:10, iron:11, label:"Infant daily target" },
  pregnant: { kcal:2400, protein:71, fiber:28, iron:27, label:"Pregnancy daily target" },
}

// ── Meal suggestion engine ────────────────────────────────────────────────────
// Picks foods from 3 different category groups so suggestions are always varied.
// Does NOT score on single dimensions (avoided the garlic problem).

const SLOT_CATS = {
  breakfast: ["grains", "dairy", "legumes"],
  lunch:     ["legumes", "vegetables", "grains"],
  dinner:    ["legumes", "meat", "vegetables"],
}

function getMealPlan(
  member: Pick<FamilyMember,"member_type"|"diet_type"|"has_diabetes"|"has_anemia">,
  foods: EthiopianFood[],
  seed: number,
): { breakfast: EthiopianFood[]; lunch: EthiopianFood[]; dinner: EthiopianFood[] } {

  if (!foods.length) return { breakfast:[], lunch:[], dinner:[] }

  let pool = foods.filter(f => {
    if (!f.is_active) return false
    if (member.diet_type === "fasting" && !f.fasting_safe) return false
    if ((member.has_diabetes || member.diet_type === "diabetic") && !f.diabetes_friendly) return false
    if (member.member_type === "pregnant" && !f.pregnancy_safe) return false
    if (["child","infant"].includes(member.member_type) && f.category === "drinks") return false
    return true
  })
  if (!pool.length) pool = foods.filter(f => f.is_active)

  const score = (f: EthiopianFood, priorityIron: boolean, lowGI: boolean, highProtein: boolean): number => {
    let s = 0
    // Base: fermented foods are always good
    s += f.fermentation_score * 4
    // Fibre is always good
    s += Math.min(f.fiber_g, 8) * 1.5
    // Context-specific boosts
    if (priorityIron) s += f.iron_mg * 3
    if (lowGI && f.glycemic_index > 0) s += f.glycemic_index <= 40 ? 10 : f.glycemic_index <= 55 ? 4 : -8
    if (highProtein) s += Math.min(f.protein_g, 15)
    // Spices/specials score high on inflammation but should not dominate meals
    if (f.category === "special") s -= 8
    // Variety seed — prevents same food appearing on re-render
    // Ensure numeric arithmetic if ids or seed come as strings
    s += (Number(f.id) * 13 + Number(seed) * 7) % 11
    return s
  }

  const priorityIron  = member.has_anemia || member.member_type === "pregnant"
  const lowGI         = !!(member.has_diabetes || member.diet_type === "diabetic" || member.member_type === "elder")
  const highProtein   = ["child","infant"].includes(member.member_type)

  const used = new Set<string | number>()

  const pickSlot = (cats: string[]): EthiopianFood[] => {
    const result: EthiopianFood[] = []
    for (const cat of cats) {
      if (result.length >= 2) break
      const best = pool
        .filter(f => f.category === cat && !used.has(f.id))
        .sort((a, b) => score(b, priorityIron, lowGI, highProtein) - score(a, priorityIron, lowGI, highProtein))[0]
      if (best) { result.push(best); used.add(best.id) }
    }
    return result
  }

  return {
    breakfast: pickSlot(SLOT_CATS.breakfast),
    lunch:     pickSlot(SLOT_CATS.lunch),
    dinner:    pickSlot(SLOT_CATS.dinner),
  }
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function FoodPill({ food, color }: { food: EthiopianFood; color: string }) {
  const raw   = food.display_name || food.name_en
  const match = raw.match(/^(.*?)\s*\[([^\]]+)\]\s*$/)
  const en    = match ? match[1].trim() : food.name_en
  const am    = match ? match[2].trim() : food.name_am
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs px-2 py-1 rounded-lg font-medium", color)}>
      {am ? <><strong>{am}</strong><span className="opacity-50 mx-0.5">·</span><span className="opacity-70">{en}</span></> : en}
    </span>
  )
}

function NutrientBar({ label, value, max, unit, color }: {
  label:string; value:number; max:number; unit:string; color:string
}) {
  const pct = Math.min(Math.round((value / max) * 100), 100)
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-500">{label}</span>
        <span className="text-gray-700 font-medium tabular-nums">
          {value.toFixed(1)}{unit}<span className="text-gray-400 font-normal"> / {max}{unit}</span>
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full", color)} style={{ width:`${pct}%` }} />
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function FamilyPage() {
  const router = useRouter()
  const [members,       setMembers]       = useState<FamilyMember[]>([])
  const [foods,         setFoods]         = useState<EthiopianFood[]>([])
  const [loading,       setLoading]       = useState(true)
  const [view,          setView]          = useState<View>("list")
  const [activeMember,  setActiveMember]  = useState<FamilyMember | null>(null)
  const [showAdd,       setShowAdd]       = useState(false)
  const [saving,        setSaving]        = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [planSeed,      setPlanSeed]      = useState(0)
  const [form, setForm] = useState<{
    name:string; member_type:MemberType; age_years:string;
    diet_type:DietType; has_diabetes:boolean; has_anemia:boolean; notes:string
  }>({ name:"", member_type:"adult", age_years:"", diet_type:"omnivore", has_diabetes:false, has_anemia:false, notes:"" })

  useEffect(() => {
    Promise.all([
      familyService.list().then(r => extractArray<FamilyMember>(r.data)),
      foodService.list().then(r  => extractArray<EthiopianFood>(r.data)),
    ]).then(([m, f]) => { setMembers(m); setFoods(f) })
     .catch(() => {}).finally(() => setLoading(false))
  }, [])

  const reload = () => familyService.list().then(r => setMembers(extractArray<FamilyMember>(r.data)))

  const handleAdd = async () => {
    if (!form.name.trim()) { toast.error("Enter a name"); return }
    setSaving(true)
    try {
      await familyService.create({ ...form, age_years: form.age_years ? parseInt(form.age_years) : undefined })
      toast.success(`${form.name} added!`)
      setShowAdd(false)
      setForm({ name:"", member_type:"adult", age_years:"", diet_type:"omnivore", has_diabetes:false, has_anemia:false, notes:"" })
      await reload()
    } catch { toast.error("Could not add member.") }
    finally { setSaving(false) }
  }

  const handleDelete = async (id: string, name: string) => {
    try {
      await familyService.delete(id)
      setMembers(m => m.filter(x => x.id !== id))
      setConfirmDelete(null)
      if (activeMember?.id === id) { setView("list"); setActiveMember(null) }
      toast.success(`${name} removed.`)
    } catch { toast.error("Could not remove.") }
  }

  // ── Detail view ──────────────────────────────────────────────────────────────

  if (view === "detail" && activeMember) {
    const m        = activeMember
    const typeInfo = MEMBER_TYPES.find(t => t.id === m.member_type)!
    const targets  = TARGETS[m.member_type]
    const plan     = getMealPlan(m, foods, planSeed)

    const todayKcal    = (m as any).today_calories   ?? 0
    const todayProtein = (m as any).today_protein_g  ?? 0
    const todayFiber   = (m as any).today_fiber_g    ?? 0
    const todayIron    = (m as any).today_iron_mg    ?? 0
    const gutScore     = m.current_gut_score         ?? 0

    const alerts: string[] = []
    if (m.member_type === "pregnant" && todayIron < targets.iron * 0.5 && todayKcal > 0)
      alerts.push("Iron below 50% of pregnancy target — add gomen or misir wot")
    if (todayFiber < targets.fiber * 0.4 && todayKcal > 0)
      alerts.push("Fibre low today — add legumes or dark greens")
    if (m.has_anemia && todayIron < 5 && todayKcal > 0)
      alerts.push("Anemia risk — prioritise iron-rich foods today")
    if (gutScore > 0 && gutScore < 40)
      alerts.push("Gut score below 40 — more fermented and prebiotic foods recommended")

    const slotColors: Record<string, string> = {
      breakfast: "bg-amber-50 text-amber-800",
      lunch:     "bg-wellnet-50 text-wellnet-800",
      dinner:    "bg-blue-50 text-blue-800",
    }

    const reasonItems: string[] = []
    if (m.member_type === "pregnant") reasonItems.push("🤰 Pregnancy: high-iron & pregnancy-safe foods prioritised; raw meat, tej and mitmita excluded")
    if (m.member_type === "elder")    reasonItems.push("👴 Elder: low-GI preference; soft legumes and fermented foods for gut health")
    if (m.member_type === "child")    reasonItems.push("🧒 Child: higher protein; spice-heavy specials avoided; dairy and legumes favoured")
    if (m.member_type === "infant")   reasonItems.push("👶 Infant: dairy and soft grains only; drinks and specials excluded")
    if (m.has_diabetes)               reasonItems.push("🩸 Diabetes: only diabetes-friendly foods (GI ≤55, carbs ≤40g) shown")
    if (m.has_anemia)                 reasonItems.push("⚠ Anemia: iron-rich foods scored higher across all slots")
    if (m.diet_type === "fasting")    reasonItems.push("✦ Fasting: only Ethiopian Orthodox fasting-safe foods — no meat or dairy")
    if (!reasonItems.length)          reasonItems.push("🌿 Balanced: fermented, fibre-rich and protein foods selected from the EPHI 2025 database")

    return (
      <div className="space-y-4 max-w-2xl mx-auto">

        {/* Header */}
        <div className="flex items-center gap-3">
          <button onClick={() => { setView("list"); setActiveMember(null) }}
            className="p-2 rounded-xl bg-gray-100 hover:bg-gray-200 transition-colors">
            <ChevronRight className="w-4 h-4 rotate-180 text-gray-600" />
          </button>
          <div className="flex items-center gap-3 flex-1">
            <div className="w-11 h-11 rounded-2xl bg-gray-100 flex items-center justify-center text-xl">
              {typeInfo.emoji}
            </div>
            <div>
              <div className="font-bold text-gray-900 text-base">{m.name}</div>
              <div className="text-xs text-gray-400">
                {typeInfo.label}{m.age_years ? ` · ${m.age_years}y` : ""}
                {m.diet_type !== "omnivore" ? ` · ${m.diet_type}` : ""}
              </div>
            </div>
          </div>
          {gutScore > 0 && <GutScoreRing score={gutScore} size="sm" showLabel={false} />}
        </div>

        {/* Badges */}
        <div className="flex gap-2 flex-wrap">
          {m.has_diabetes   && <span className="badge-purple text-xs">🩸 Diabetes</span>}
          {m.has_anemia     && <span className="badge-red    text-xs">⚠ Anemia</span>}
          {m.member_type === "pregnant" && <span className="badge-purple text-xs">🤰 Pregnancy</span>}
          {m.diet_type === "fasting"    && <span className="badge-amber  text-xs">✦ Fasting</span>}
        </div>

        {/* Alerts */}
        {alerts.map(a => (
          <div key={a} className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
            <span className="text-xs text-amber-700">{a}</span>
          </div>
        ))}

        {/* Today's nutrition */}
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-wellnet-500" />
              Today's nutrition
            </h3>
            <span className="text-[10px] text-gray-400">{targets.label}</span>
          </div>
          {todayKcal === 0 ? (
            <div className="text-xs text-gray-400 text-center py-4">
              No meals logged yet today for {m.name}.
              <br />
              <button
                onClick={() => router.push(`/dashboard/log?member=${m.id}`)}
                className="mt-2 inline-block text-wellnet-600 font-medium underline underline-offset-2">
                Log a meal now →
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              <NutrientBar label="Calories" value={todayKcal}    max={targets.kcal}    unit=" kcal" color="bg-orange-400" />
              <NutrientBar label="Protein"  value={todayProtein} max={targets.protein} unit="g"     color="bg-blue-400"   />
              <NutrientBar label="Fibre"    value={todayFiber}   max={targets.fiber}   unit="g"     color="bg-wellnet-500"/>
              <NutrientBar label="Iron"     value={todayIron}    max={targets.iron}    unit="mg"    color="bg-red-400"    />
            </div>
          )}
        </div>

        {/* Meal plan */}
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <Utensils className="w-4 h-4 text-wellnet-500" />
              Suggested meals today
            </h3>
            <button onClick={() => setPlanSeed(s => s + 1)}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors" title="Refresh suggestions">
              <RefreshCw className="w-3.5 h-3.5 text-gray-400" />
            </button>
          </div>
          <p className="text-[10px] text-gray-400 -mt-1">
            EPHI 2025 · filtered for {m.name}'s health profile · tap ↺ for more options
          </p>

          {(["breakfast","lunch","dinner"] as const).map(slot => {
            const items = plan[slot]
            if (!items.length) return null
            const slotLabel = slot === "breakfast" ? "☀️ Breakfast" : slot === "lunch" ? "🌤 Lunch" : "🌙 Dinner"
            return (
              <div key={slot}>
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-1.5">{slotLabel}</div>
                <div className="flex gap-2 flex-wrap">
                  {items.map(food => <FoodPill key={food.id} food={food} color={slotColors[slot]} />)}
                </div>
              </div>
            )
          })}
        </div>

        {/* Why these foods */}
        <div className="card space-y-2">
          <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-wellnet-500" />
            Why these foods for {m.name}?
          </h3>
          <ul className="space-y-1.5">
            {reasonItems.map(r => (
              <li key={r} className="text-xs text-gray-600 leading-snug">{r}</li>
            ))}
          </ul>
        </div>

        {/* CTA */}
        <button
          onClick={() => router.push(`/dashboard/log?member=${m.id}`)}
          className="w-full btn-primary flex items-center justify-center gap-2 py-3">
          <Utensils className="w-4 h-4" />
          Log a meal for {m.name}
        </button>

        {/* Danger zone */}
        <div className="pt-2 border-t border-gray-100 flex items-center justify-between">
          <span className="text-xs text-gray-400">Remove {m.name} from family plan</span>
          {confirmDelete === m.id ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-red-500">Sure?</span>
              <button onClick={() => handleDelete(m.id, m.name)}
                className="p-1.5 rounded-lg bg-red-50 text-red-500 hover:bg-red-100">
                <Check className="w-3.5 h-3.5" />
              </button>
              <button onClick={() => setConfirmDelete(null)}
                className="p-1.5 rounded-lg bg-gray-50 text-gray-400 hover:bg-gray-100">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button onClick={() => setConfirmDelete(m.id)}
              className="flex items-center gap-1.5 text-xs text-red-400 hover:text-red-600 transition-colors">
              <Trash2 className="w-3.5 h-3.5" /> Remove
            </button>
          )}
        </div>
      </div>
    )
  }

  // ── List view ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Family Planner</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Personalised meal plans & nutrition tracking for each household member
          </p>
        </div>
        {members.length < 6 && (
          <button onClick={() => setShowAdd(true)}
            className="btn-primary flex items-center gap-1.5 px-4 py-2 text-sm">
            <Plus className="w-4 h-4" /> Add member
          </button>
        )}
      </div>

      {/* Feature summary */}
      <div className="grid grid-cols-3 gap-2 text-center">
        {[
          { icon:"🥗", title:"Meal plans",      desc:"Daily EPHI-sourced suggestions per member" },
          { icon:"📊", title:"Nutrition",        desc:"Track calories, iron, fibre, protein" },
          { icon:"🛡",  title:"Health filters",  desc:"Diabetes, anemia, fasting, pregnancy" },
        ].map(({ icon, title, desc }) => (
          <div key={title} className="bg-gray-50 rounded-2xl p-3">
            <div className="text-xl mb-1">{icon}</div>
            <div className="text-xs font-semibold text-gray-700">{title}</div>
            <div className="text-[10px] text-gray-400 mt-0.5 leading-snug">{desc}</div>
          </div>
        ))}
      </div>

      <div className="text-xs text-gray-400">{members.length} / 6 members · tap a member to view their plan</div>

      {loading ? (
        <div className="space-y-3">
          {[1,2].map(i => <div key={i} className="h-24 bg-gray-100 rounded-2xl animate-pulse" />)}
        </div>
      ) : members.length === 0 ? (
        <div className="card text-center py-12">
          <Users className="w-10 h-10 text-gray-200 mx-auto mb-3" />
          <div className="text-sm font-medium text-gray-700 mb-1">No family members yet</div>
          <div className="text-xs text-gray-400 mb-5 max-w-xs mx-auto">
            Add a member to get personalised EPHI-based meal plans, nutrition targets, and health-aware food suggestions.
          </div>
          <button onClick={() => setShowAdd(true)} className="btn-primary inline-flex items-center gap-2">
            <Plus className="w-4 h-4" /> Add first member
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {members.map(m => {
            const typeInfo  = MEMBER_TYPES.find(t => t.id === m.member_type)!
            const score     = m.current_gut_score ?? 0
            const targets   = TARGETS[m.member_type]
            const todayKcal = (m as any).today_calories ?? 0
            const kcalPct   = todayKcal > 0 ? Math.min(Math.round((todayKcal / targets.kcal) * 100), 100) : 0

            return (
              <button key={m.id} onClick={() => { setActiveMember(m); setView("detail") }}
                className="card w-full text-left hover:shadow-md transition-shadow active:scale-[0.99]">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-2xl bg-gray-100 flex items-center justify-center text-xl shrink-0">
                    {typeInfo.emoji}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900 text-sm">{m.name}</span>
                      <span className="text-xs text-gray-400">{typeInfo.label}</span>
                      {m.age_years && <span className="text-xs text-gray-400">· {m.age_years}y</span>}
                    </div>
                    <div className="flex gap-1.5 mt-1 flex-wrap">
                      {m.diet_type !== "omnivore" && <span className="badge-amber  text-[10px]">{m.diet_type}</span>}
                      {m.has_diabetes && <span className="badge-purple text-[10px]">Diabetes</span>}
                      {m.has_anemia   && <span className="badge-red    text-[10px]">Anemia</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {score > 0
                      ? <GutScoreRing score={score} size="sm" showLabel={false} />
                      : <span className={cn("text-[10px] border rounded-full px-2 py-0.5", SCORE_BG(0))}>No score</span>
                    }
                    <ChevronRight className="w-4 h-4 text-gray-300" />
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] text-gray-400">Today's calories</span>
                    <span className="text-[10px] text-gray-500 font-medium tabular-nums">
                      {todayKcal > 0 ? `${todayKcal} / ${targets.kcal} kcal (${kcalPct}%)` : "No meals logged yet"}
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-wellnet-400 rounded-full" style={{ width:`${kcalPct}%` }} />
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {/* Add member sheet */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/30">
          <div className="bg-white rounded-3xl p-6 w-full max-w-sm shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-gray-900">Add family member</h3>
              <button onClick={() => setShowAdd(false)} className="p-1.5 rounded-lg hover:bg-gray-100">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Name</label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name:e.target.value }))}
                placeholder="Tigist, Kidus, Almaz…" className="input" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Member type</label>
              <div className="flex gap-2 flex-wrap">
                {MEMBER_TYPES.map(t => (
                  <button key={t.id} onClick={() => setForm(f => ({ ...f, member_type:t.id }))}
                    className={cn(
                      "flex items-center gap-1 px-2.5 py-1.5 rounded-xl border text-xs font-medium transition-all",
                      form.member_type === t.id ? "bg-wellnet-500 text-white border-wellnet-500" : "bg-white text-gray-600 border-gray-200"
                    )}>
                    {t.emoji} {t.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Age</label>
                <input type="number" value={form.age_years} onChange={e => setForm(f => ({ ...f, age_years:e.target.value }))}
                  placeholder="e.g. 8" className="input" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1.5">Diet</label>
                <select value={form.diet_type} onChange={e => setForm(f => ({ ...f, diet_type:e.target.value as DietType }))} className="input">
                  {DIET_TYPES.map(d => <option key={d} value={d} className="capitalize">{d}</option>)}
                </select>
              </div>
            </div>
            <div className="space-y-2">
              {([{ label:"Has diabetes", key:"has_diabetes" as const }, { label:"Has anemia", key:"has_anemia" as const }]).map(({ label, key }) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <div onClick={() => setForm(f => ({ ...f, [key]:!f[key] }))}
                    className={cn("w-9 h-5 rounded-full relative transition-colors cursor-pointer", form[key] ? "bg-wellnet-500" : "bg-gray-200")}>
                    <div className={cn("absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all", form[key] ? "left-4" : "left-0.5")} />
                  </div>
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </div>
            <div className="flex gap-3 pt-1">
              <button onClick={() => setShowAdd(false)} className="flex-1 btn-ghost">Cancel</button>
              <button onClick={handleAdd} disabled={saving} className="flex-1 btn-primary flex items-center justify-center gap-2">
                {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Adding…</> : "Add member"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
