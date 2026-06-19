"use client"

import type { EthiopianFood } from "@/types"
import { formatPreparationState } from "@/services/wellnet"

interface FoodNameProps {
  food: EthiopianFood
  className?: string
}

export default function FoodName({ food, className }: FoodNameProps) {
  // 1. Scrub trailing eye-leader dots left over from tabular data extraction matrices
  const cleanNameEn = food.name_en?.replace(/\.+\s*$/, "")?.trim()
  const cleanNameAm = food.name_am?.replace(/\.+\s*$/, "")?.trim()

  // 2. Language fallback fallback hierarchy matrix (Prevents printing naked reference numbers)
  const baseName = cleanNameEn || cleanNameAm || `Food Item #${food.id}`

  // 3. Process the preparation string through your centralized formatting helper
  const preparationState = food.preparation_state 
    ? ` (${String(formatPreparationState(food.preparation_state))})` 
    : ""

  return (
    <span className={className}>
      {baseName}{preparationState}
    </span>
  )
}