// lib/utils.ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatScore(score: number): string {
  if (score >= 85) return "Excellent"
  if (score >= 70) return "Great"
  if (score >= 55) return "Good"
  if (score >= 40) return "Fair"
  return "Needs attention"
}

export function scoreColor(score: number): string {
  if (score >= 85) return "#1D9E75"
  if (score >= 70) return "#5DCAA5"
  if (score >= 55) return "#9FE1CB"
  if (score >= 40) return "#EF9F27"
  return "#E24B4A"
}

export function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("en-ET", {
    weekday: "short", month: "short", day: "numeric"
  })
}

export function todayISO(): string {
  return new Date().toISOString().split("T")[0]
}
