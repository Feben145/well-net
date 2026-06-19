
//frontend/src/services/wellnet.ts
import api from "@/lib/api"
import type {
  User, UserProfile, FamilyMember,
  EthiopianFood, MealLogCreate, ScoreResult,
  DailyNutrition, WellnessTipsResponse, JourneyFeedResponse,
  Professional, WellnessPackage, OffPeakDeal,
} from "@/types"

/**
 * DRF can return either a plain array OR a paginated object { results:[], count:N }.
 * This helper always gives back a plain array regardless.
 */
export function extractArray<T>(data: any): T[] {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authService = {
  register: (data: {
    email: string; username: string
    password: string; password2: string
  }) => api.post("/auth/register/", data),

  login: async (email: string, password: string) => {
    const { data } = await api.post("/auth/login/", { email, password })
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", data.access)
      localStorage.setItem("refresh_token", data.refresh)
    }
    return data
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
    }
  },

  getMe: () => api.get<User>("/auth/me/"),
  getProfile: () => api.get<UserProfile>("/auth/profile/"),
  updateProfile: (data: Partial<UserProfile>) => api.patch<UserProfile>("/auth/profile/", data),
}

// ── Family ────────────────────────────────────────────────────────────────────
export const familyService = {
  list: () => api.get<FamilyMember[]>("/auth/family/"),
  create: (data: Partial<FamilyMember>) => api.post<FamilyMember>("/auth/family/", data),
  update: (id: string, data: Partial<FamilyMember>) =>
    api.patch<FamilyMember>(`/auth/family/${id}/`, data),
  delete: (id: string) => api.delete(`/auth/family/${id}/`),
}

// ── Foods ─────────────────────────────────────────────────────────────────────
export const foodService = {
  list: (params?: { category?: string; fasting_safe?: boolean; search?: string }) =>
    api.get<EthiopianFood[]>("/foods/", { params }),

  logMeal: (data: MealLogCreate) =>
    api.post<ScoreResult>("/foods/log/", data),

  getMealLogs: (date?: string) =>
    api.get("/foods/logs/", { params: date ? { date } : {} }),

  getDaily: (date?: string) =>
    api.get<DailyNutrition>("/foods/daily/", { params: date ? { date } : {} }),

  getWeekly: () => api.get<{
    week_data: DailyNutrition[]
    avg_gut_score: number
    avg_fiber_g: number
    best_day: string | null
  }>("/foods/weekly/"),
}

// ── AI / Wellness ─────────────────────────────────────────────────────────────
// ── AI / Wellness ─────────────────────────────────────────────────────────────
export const aiService = {
  getTips: () => api.get<WellnessTipsResponse>("/ai/tips/"),
  getMealPlan: (days = 7) => api.post("/ai/meal-plan/", { days }),
  getFeed: () => api.get<JourneyFeedResponse>("/ai/feed/"),
}

// ── Experts ───────────────────────────────────────────────────────────────────
export const expertService = {
  list: (params?: { specialty?: string; is_kuriftu_partner?: boolean }) =>
    api.get<Professional[]>("/experts/", { params }),

  book: (professionalId: string, data: {
    scheduled_at: string
    duration_minutes: number
    session_type: string
  }) => api.post(`/experts/${professionalId}/book/`, data),

  mySessions: () => api.get("/experts/my-sessions/"),
}

// ── Packages ──────────────────────────────────────────────────────────────────
export const packageService = {
  list: () => api.get<WellnessPackage[]>("/packages/"),
  mySubscriptions: () => api.get("/packages/my/"),
}

// ── Notifications / Deals ─────────────────────────────────────────────────────
export const notificationService = {
  getDeals: () => api.get<OffPeakDeal[]>("/notifications/deals/"),
  getHistory: () => api.get("/notifications/history/"),
}
// Add this alongside your other string formatting utilities
export function formatPreparationState(stateString: string | null | undefined): string {
  if (!stateString) return "";
  
  const lower = stateString.toLowerCase().trim();
  
  // If it contains both, "Boiled" is the active nutritional state you are tracking
  if (lower.includes("boiled") && lower.includes("tire")) {
    return "Boiled (from raw base)";
  }
  
  // Capitalize the first letter for clean UI presentation
  return stateString.charAt(0).toUpperCase() + stateString.slice(1);
}


// ── Community ─────────────────────────────────────────────────────────────────
export const communityService = {
  // Circles
  myCircles:    ()                    => api.get("/community/circles/"),
  createCircle: (data: any)           => api.post("/community/circles/", data),
  getCircle:    (id: string)          => api.get(`/community/circles/${id}/`),
  joinCircle:   (invite_code: string) => api.post("/community/circles/join/", { invite_code }),
  leaveCircle:  (id: string)          => api.post(`/community/circles/${id}/leave/`),

  // Jebena
  jebenaCheckin: (data: {
    circle_id: string; food_slug: string; message?: string; mood_emoji?: string
  }) => api.post("/community/jebena/", data),
  circleFeed: (circle_id: string) =>
    api.get(`/community/circles/${circle_id}/jebena/`),

  // Gursha
  myGursha:     ()                                                                   => api.get("/community/gursha/"),
  sendGursha:   (data: {
    circle_id: string; to_username: string; food_slug: string; message?: string
  })                                                                                 => api.post("/community/gursha/send/", data),
  acceptGursha: (id: string)                                                         => api.post(`/community/gursha/${id}/accept/`),

  // Edir
  contributeEdir: (circle_id: string, amount_etb: number, note?: string) =>
    api.post(`/community/circles/${circle_id}/edir/`, { amount_etb, note }),

  // Feed
  feed:     () => api.get("/community/feed/"),
  likePost: (post_id: string) => api.post(`/community/feed/${post_id}/like/`),
}