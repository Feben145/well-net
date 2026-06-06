"use client"

import { useEffect, useRef } from "react"
import { cn } from "@/lib/utils"

interface Props {
  score: number
  size?: "sm" | "md" | "lg"
  showLabel?: boolean
  animate?: boolean
}

const SIZES = {
  sm: {
    wh: 72,
    r: 27,
    sw: 5,
    num: "text-lg",
    lbl: "text-xs",
  },
  md: {
    wh: 110,
    r: 42,
    sw: 7,
    num: "text-3xl",
    lbl: "text-sm",
  },
  lg: {
    wh: 150,
    r: 57,
    sw: 9,
    num: "text-4xl",
    lbl: "text-base",
  },
}

function scoreColor(s: number) {
  if (s >= 85) return "#1D9E75"
  if (s >= 70) return "#5DCAA5"
  if (s >= 55) return "#9FE1CB"
  if (s >= 40) return "#EF9F27"
  return "#E24B4A"
}

function scoreLabel(s: number) {
  if (s === 0) return "Not logged"
  if (s >= 85) return "Excellent"
  if (s >= 70) return "Great"
  if (s >= 55) return "Good"
  if (s >= 40) return "Fair"
  return "Needs attention"
}

export default function GutScoreRing({
  score,
  size = "md",
  showLabel = true,
  animate = true,
}: Props) {
  const arcRef = useRef<SVGCircleElement>(null)

  const { wh, r, sw, num, lbl } = SIZES[size]

  const circ = 2 * Math.PI * r
  const clipped = Math.max(0, Math.min(score, 100))
  const offset = circ - (circ * clipped) / 100
  const color = scoreColor(clipped)

  useEffect(() => {
    const el = arcRef.current

    // prevent ref-before-mount errors
    if (!el || !animate) return

    // reset animation
    el.style.transition = "none"
    el.setAttribute("stroke-dashoffset", String(circ))

    // animate after paint
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (!arcRef.current) return

        arcRef.current.style.transition =
          "stroke-dashoffset 1s ease-out"

        arcRef.current.setAttribute(
          "stroke-dashoffset",
          String(offset)
        )
      })
    })
  }, [circ, offset, animate])

  return (
    <div className="flex flex-col items-center gap-1.5 shrink-0">
      <div
        className="relative flex items-center justify-center"
        style={{ width: wh, height: wh }}
      >
        <svg
          width={wh}
          height={wh}
          viewBox={`0 0 ${wh} ${wh}`}
          className="absolute inset-0"
          aria-hidden="true"
        >
          {/* Track */}
          <circle
            cx={wh / 2}
            cy={wh / 2}
            r={r}
            fill="none"
            stroke="#E5E7EB"
            strokeWidth={sw}
          />

          {/* Progress */}
          <circle
            ref={arcRef}
            cx={wh / 2}
            cy={wh / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={sw}
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={animate ? circ : offset}
            transform={`rotate(-90 ${wh / 2} ${wh / 2})`}
          />
        </svg>

        {/* Number */}
        <div className="relative z-10 text-center select-none">
          <div
            className={cn(
              "font-bold leading-none tabular-nums",
              num
            )}
            style={{ color }}
          >
            {clipped}
          </div>

          {size !== "sm" && (
            <div className="text-[10px] text-gray-400 mt-0.5">
              / 100
            </div>
          )}
        </div>
      </div>

      {/* Label */}
      {showLabel && (
        <span
          className={cn("font-semibold", lbl)}
          style={{ color }}
        >
          {scoreLabel(clipped)}
        </span>
      )}
    </div>
  )
}
