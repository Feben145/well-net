// components/food/FoodButton.tsx
"use client"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"
import type { EthiopianFood } from "@/types"

interface Props {
  food: EthiopianFood
  selected: boolean
  onToggle: (food: EthiopianFood) => void
}

const CATEGORY_COLORS: Record<string, string> = {
  grains:     "hover:bg-amber-50  hover:border-amber-300  data-[sel=true]:bg-amber-500  data-[sel=true]:border-amber-500",
  legumes:    "hover:bg-wellnet-50 hover:border-wellnet-300 data-[sel=true]:bg-wellnet-500 data-[sel=true]:border-wellnet-500",
  meat:       "hover:bg-red-50   hover:border-red-300    data-[sel=true]:bg-red-500    data-[sel=true]:border-red-500",
  dairy:      "hover:bg-blue-50  hover:border-blue-300   data-[sel=true]:bg-blue-500   data-[sel=true]:border-blue-500",
  vegetables: "hover:bg-green-50 hover:border-green-300  data-[sel=true]:bg-green-500  data-[sel=true]:border-green-500",
  drinks:     "hover:bg-purple-50 hover:border-purple-300 data-[sel=true]:bg-purple-500 data-[sel=true]:border-purple-500",
  special:    "hover:bg-orange-50 hover:border-orange-300 data-[sel=true]:bg-orange-500 data-[sel=true]:border-orange-500",
}

export default function FoodButton({ food, selected, onToggle }: Props) {
  const colorClasses = CATEGORY_COLORS[food.category] || CATEGORY_COLORS.legumes

  return (
    <button
      data-sel={selected}
      onClick={() => onToggle(food)}
      className={cn(
        "relative flex flex-col items-start p-3 rounded-xl border text-left transition-all duration-150 active:scale-95",
        "border-gray-200 bg-white",
        colorClasses,
        selected && "text-white border-transparent"
      )}
    >
      {selected && (
        <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-white/30 flex items-center justify-center">
          <Check className="w-2.5 h-2.5" />
        </div>
      )}
      <div className={cn("text-xs font-medium leading-tight", selected ? "text-white" : "text-gray-800")}>
        {food.name_en.split(" — ")[0].split(" (")[0]}
      </div>
      {food.name_am && (
        <div className={cn("text-xs mt-0.5", selected ? "text-white/80" : "text-gray-400")}>
          {food.name_am}
        </div>
      )}
      <div className={cn("flex gap-1 mt-1.5 flex-wrap")}>
        {food.fermentation_score > 0 && (
          <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full font-medium",
            selected ? "bg-white/20 text-white" : "bg-wellnet-50 text-wellnet-700"
          )}>
            🧫 Fermented
          </span>
        )}
        {food.fasting_safe && (
          <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full font-medium",
            selected ? "bg-white/20 text-white" : "bg-amber-50 text-amber-700"
          )}>
            ✦ Fasting
          </span>
        )}
      </div>
    </button>
  )
}
