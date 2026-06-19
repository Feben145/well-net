// ── frontend/src/store/index.ts ──
import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { User, UserProfile, EthiopianFood, ScoreResult, DailyNutrition } from "@/types"

// 1. Export AuthState Interface & Store Hook
export interface AuthState {
  user: User | null
  profile: UserProfile | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  setProfile: (profile: UserProfile) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      profile: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: true }),
      setProfile: (profile) => set({ profile }),
      logout: () => set({ user: null, profile: null, isAuthenticated: false }),
    }),
    { name: "wellnet-auth" }
  )
)

// 2. Export MealLogState Interface & Store Hook
export interface MealLogState {
  selectedFoods: Map<string, { food: EthiopianFood; servings: number }>
  activeCategory: string
  lastScore: ScoreResult | null
  todayNutrition: DailyNutrition | null
  addFood: (food: EthiopianFood, servings?: number) => void
  removeFood: (foodId: string) => void
  toggleFood: (food: EthiopianFood) => void
  updateServings: (foodId: string, servings: number) => void
  clearSelection: () => void
  setCategory: (cat: string) => void
  setLastScore: (score: ScoreResult) => void
  setTodayNutrition: (nutrition: DailyNutrition) => void
}

export const useMealLogStore = create<MealLogState>((set, get) => ({
  selectedFoods: new Map(),
  activeCategory: "all",
  lastScore: null,
  todayNutrition: null,

  addFood: (food, servings = 1) => {
    const map = new Map(get().selectedFoods)
    map.set(String(food.id), { food, servings })
    set({ selectedFoods: map })
  },
  removeFood: (foodId) => {
    const map = new Map(get().selectedFoods)
    map.delete(foodId)
    set({ selectedFoods: map })
  },
  toggleFood: (food) => {
    const map = new Map(get().selectedFoods)
    if (map.has(String(food.id))) {
      map.delete(String(food.id))
    } else {
      map.set(String(food.id), { food, servings: 1 })
    }
    set({ selectedFoods: map })
  },
  updateServings: (foodId, servings) => {
    const map = new Map(get().selectedFoods)
    const existing = map.get(foodId)
    if (existing) map.set(foodId, { ...existing, servings })
    set({ selectedFoods: map })
  },
  clearSelection: () => set({ selectedFoods: new Map() }),
  setCategory: (cat) => set({ activeCategory: cat }),
  setLastScore: (score) => set({ lastScore: score }),
  setTodayNutrition: (nutrition) => set({ todayNutrition: nutrition }),
}))

// 3. Export UI Hooks
interface UIState {
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}))