// types/index.ts — Well-Net shared TypeScript types

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface User {
  id: string
  email: string
  username: string
  phone: string
  preferred_language: "en" | "am"
  sms_notifications: boolean
}

export interface UserProfile {
  display_name: string
  date_of_birth: string | null
  gender: string
  height_cm: number | null
  weight_kg: number | null
  primary_goal: WellnessGoal
  secondary_goals: WellnessGoal[]
  activity_level: string
  diet_type: DietType
  is_pregnant: boolean
  has_diabetes: boolean
  has_hypertension: boolean
  has_anemia: boolean
  is_fasting_season: boolean
  kuriftu_guest: boolean
  kuriftu_membership_tier: "none" | "standard" | "premium"
  current_gut_score: number
  current_wellness_score: number
  wellness_streak_days: number
  age: number | null
  bmi: number | null
}

export type WellnessGoal =
  | "gut_health" | "weight_balance" | "energy" | "stress"
  | "sleep" | "immunity" | "mindfulness" | "general"

export type DietType =
  | "omnivore" | "fasting" | "vegetarian" | "vegan"
  | "no_pork" | "diabetic"

// ── Food ──────────────────────────────────────────────────────────────────────
/**
 * Aligned to the finalized EPHI 2025 structural router config.
 * Handled groups: grains, legumes, vegetables, meat (including group 09 fish), 
 * dairy_poultry, drinks (group 12 beverages), and special (tubers, fats, sugars, flours).
 */
export type FoodCategory =
  | "grains"
  | "legumes"
  | "vegetables"
  | "meat"
  | "dairy_poultry"
  | "drinks"
  | "special";

export interface EthiopianFood {
  id: number | string       // Supports standard database IDs
  slug: string              // State-specific slug identifier (e.g., 'beef_liver_boiled_drained')
  source: string            // E.g., 'ephi'
  name_en: string           // Clean, isolated English parent item name
  name_am: string           // Pristine, full Amharic name description (supports Amharic typography hierarchy)
  display_name: string      // Bilingual structured display name used in search results
  category: FoodCategory    // Aligned to the multi-form router configuration
  preparation_state?: string | null; // Raw string token representing the operational culinary status
  serving_description: string // Exact preparation form state label (e.g., 'Per 100g edible portion (grilled)')
  serving_g: number          // Base allocation metrics (usually 100.0)
  is_active: boolean

  // Macronutrients & Primary Micro
  calories_kcal: number
  protein_g: number
  fat_g: number
  cho_g: number
  fiber_g: number
  iron_mg: number

  // Composition Matrix Metrics
  glycemic_index: number
  fermentation_score: number // 0–3 (None, Low, Medium, High)
  prebiotic_score: number     // 0–3
  inflammatory_index: number // -2 (Anti-inflammatory) to +2 (Pro-inflammatory)

  // Health Guardrails & Dynamic Restriction Flags
  fasting_safe: boolean     // Enforces strict Orthodox dietary restrictions
  pregnancy_safe: boolean   // Explicitly locks out raw meats and regional alcohols
  diabetes_friendly: boolean // Evaluated against active GI and CHO limits

  // Tracking Metadata
  notes: string            // Summarized nutritional snapshot context
  source_citation: string  // Corresponds to the unique 6-digit EPHI identifier row
}

export interface FoodLogItem {
  food_id: string
  servings: number
}

export type MealType = "breakfast" | "lunch" | "dinner" | "snack"

export interface MealLogCreate {
  date: string           // YYYY-MM-DD
  meal_type: MealType
  foods: FoodLogItem[]
  notes?: string
  family_member_id?: string
}

// ── Scores ────────────────────────────────────────────────────────────────────
export interface ScoreResult {
  meal_log_id: string
  gut_score: number
  label: string
  color: string
  fiber_g: number
  protein_g: number
  iron_mg: number
  fermentation_total: number
  inflammatory_net: number
  sub_scores: {
    fiber: number
    fermentation: number
    inflammation: number
    protein: number
  }
  alerts: Alert[]
  kuriftu_tip: string
  top_foods: string[]
  weakest_dimension: string
}

export interface Alert {
  type: "warning" | "tip" | "caution"
  icon: string
  message: string
}

export interface DailyNutrition {
  date: string
  gut_score: number
  wellness_score: number
  fiber_g: number
  protein_g: number
  iron_mg: number
  fermentation_total: number
  inflammatory_net: number
  meal_count: number
  score_label: { label: string; color: string }
  kuriftu_tip: string
}

// ── AI ────────────────────────────────────────────────────────────────────────
export interface WellnessTip {
  title: string
  body: string
  icon: string
  color: "teal" | "amber" | "purple" | "green"
}

export interface WellnessTipsResponse {
  wellness_message: string
  tips: WellnessTip[]
  kuriftu_tip: string
}

export interface FeedCard {
  type: "insight" | "tip" | "retreat" | "challenge" | "milestone"
  title: string
  body: string
  cta_label: string | null
  cta_action: string | null
  color: "teal" | "amber" | "purple" | "green"
}

export interface JourneyFeedResponse {
  feed: FeedCard[]
  gut_score: number
  weekly_avg: number
  streak: number
}

// ── Professionals ─────────────────────────────────────────────────────────────
export interface Professional {
  id: string
  display_name: string
  title: string
  specialty: string
  bio: string
  languages: string[]
  session_types: string[]
  session_price_etb: number
  offpeak_price_etb: number | null
  rating: number
  review_count: number
  is_verified: boolean
  is_kuriftu_partner: boolean
  avatar_url: string
  license_body: string
}

// ── Packages ──────────────────────────────────────────────────────────────────
export interface WellnessPackage {
  id: string
  name: string
  package_type: string
  tagline: string
  price_etb: number
  billing_period: string
  max_members: number
  features: string[]
  is_featured: boolean
  kuriftu_discount_pct: number
}

// ── Notifications / Deals ─────────────────────────────────────────────────────
export interface OffPeakDeal {
  id: string
  title: string
  deal_type: string
  description: string
  location: string
  original_price_etb: number
  discounted_price_etb: number
  discount_pct: number
  valid_from: string
  valid_until: string
  slots_remaining: number
  booking_url: string
}

// ── Family ────────────────────────────────────────────────────────────────────
export interface FamilyMember {
  id: string
  name: string
  member_type: "adult" | "child" | "elder" | "pregnant" | "infant"
  age_years: number | null
  diet_type: string
  has_diabetes: boolean
  has_anemia: boolean
  current_gut_score: number
  notes: string
}