"use client"
import { useEffect, useState } from "react"
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadarChart, PolarGrid,
  PolarAngleAxis, Radar,
} from "recharts"
import { TrendingUp, Award, Flame, Calendar } from "lucide-react"
import { foodService } from "@/services/wellnet"
import { useAuthStore } from "@/store"
import { scoreColor, formatScore } from "@/lib/utils"

interface WeekData {
  date: string
  gut_score: number
  fiber_g: number
  protein_g: number
  iron_mg: number
  fermentation_total: number
  score_label: { label: string; color: string }
}

const DAY_NAMES = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

export default function WeeklyPage() {
  const { profile } = useAuthStore()
  const [data, setData] = useState<WeekData[]>([])
  const [weekly, setWeekly] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    foodService.getWeekly()
      .then(r => {
        setWeekly(r.data)
        setData(r.data.week_data || [])
      })
      .finally(() => setLoading(false))
  }, [])

  // Chart-friendly data
  const chartData = data.map((d, i) => ({
    day: DAY_NAMES[new Date(d.date).getDay() === 0 ? 6 : new Date(d.date).getDay() - 1],
    score: d.gut_score,
    fiber: Math.round(d.fiber_g),
    protein: Math.round(d.protein_g),
    iron: Math.round(d.iron_mg * 10) / 10,
    fermentation: d.fermentation_total,
  }))

  const avgScore = weekly?.avg_gut_score ?? 0
  const bestDay = weekly?.best_day ?? "—"
  const streak = profile?.wellness_streak_days ?? 0

  const radarData = chartData.length > 0 ? [
    { metric: "Fiber",        value: Math.round((chartData.reduce((a,d) => a + d.fiber, 0) / chartData.length) / 25 * 100) },
    { metric: "Fermentation", value: Math.round((chartData.reduce((a,d) => a + d.fermentation, 0) / chartData.length) / 9 * 100) },
    { metric: "Protein",      value: Math.round((chartData.reduce((a,d) => a + d.protein, 0) / chartData.length) / 50 * 100) },
    { metric: "Iron",         value: Math.round((chartData.reduce((a,d) => a + d.iron, 0) / chartData.length) / 18 * 100) },
    { metric: "Consistency",  value: Math.round((chartData.filter(d => d.score > 0).length / 7) * 100) },
  ] : []

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-wellnet-500" /> Weekly Report
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">Your last 7 days of wellness</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: TrendingUp, label: "Avg score",  value: avgScore, color: "text-wellnet-600", bg: "bg-wellnet-50" },
          { icon: Award,      label: "Best day",   value: bestDay,  color: "text-amber-600",  bg: "bg-amber-50" },
          { icon: Flame,      label: "Streak",     value: `${streak}d`, color: "text-red-500", bg: "bg-red-50" },
        ].map(({ icon: Icon, label, value, color, bg }) => (
          <div key={label} className="card text-center py-4">
            <div className={`w-8 h-8 rounded-xl ${bg} flex items-center justify-center mx-auto mb-2`}>
              <Icon className={`w-4 h-4 ${color}`} />
            </div>
            <div className={`text-lg font-bold ${color}`}>{value}</div>
            <div className="text-xs text-gray-400 mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1,2,3].map(i => <div key={i} className="h-48 bg-gray-100 rounded-2xl animate-pulse" />)}
        </div>
      ) : chartData.length === 0 ? (
        <div className="card text-center py-8">
          <Calendar className="w-10 h-10 text-gray-200 mx-auto mb-3" />
          <div className="text-sm text-gray-500">Log meals for 3+ days to unlock weekly charts.</div>
        </div>
      ) : (
        <>
          {/* Gut score area chart */}
          <div className="card">
            <div className="text-sm font-semibold text-gray-800 mb-4">Gut score — 7 days</div>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#1D9E75" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#1D9E75" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#9CA3AF" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#9CA3AF" }} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: "1px solid #E5E7EB", fontSize: 12 }}
                  formatter={(v: any) => [`${v} / 100`, "Score"]}
                />
                <Area
                  type="monotone" dataKey="score"
                  stroke="#1D9E75" strokeWidth={2}
                  fill="url(#scoreGrad)"
                  dot={{ fill: "#1D9E75", r: 4 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Fiber + Protein bar chart */}
          <div className="card">
            <div className="text-sm font-semibold text-gray-800 mb-4">Fiber & protein — daily totals (g)</div>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: "#9CA3AF" }} />
                <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: "1px solid #E5E7EB", fontSize: 12 }}
                />
                <Bar dataKey="fiber"   fill="#1D9E75" radius={[3,3,0,0]} name="Fiber (g)" />
                <Bar dataKey="protein" fill="#EF9F27" radius={[3,3,0,0]} name="Protein (g)" />
              </BarChart>
            </ResponsiveContainer>
            <div className="flex gap-4 mt-2">
              <div className="flex items-center gap-1.5 text-xs text-gray-500">
                <div className="w-2.5 h-2.5 rounded-sm bg-wellnet-500" /> Fiber (g)
              </div>
              <div className="flex items-center gap-1.5 text-xs text-gray-500">
                <div className="w-2.5 h-2.5 rounded-sm bg-amber-400" /> Protein (g)
              </div>
            </div>
          </div>

          {/* Radar chart — weekly nutrition balance */}
          {radarData.length > 0 && (
            <div className="card">
              <div className="text-sm font-semibold text-gray-800 mb-2">Weekly nutrition balance</div>
              <p className="text-xs text-gray-400 mb-3">How balanced your week was across all dimensions</p>
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#E5E7EB" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: "#6B7280" }} />
                  <Radar
                    name="Weekly avg"
                    dataKey="value"
                    stroke="#1D9E75"
                    fill="#1D9E75"
                    fillOpacity={0.2}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, fontSize: 12 }}
                    formatter={(v: any) => [`${v}%`, ""]}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Day-by-day breakdown */}
          <div className="card">
            <div className="text-sm font-semibold text-gray-800 mb-3">Day by day</div>
            <div className="space-y-2">
              {chartData.map((d, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-8 text-xs font-medium text-gray-400">{d.day}</div>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${d.score}%`,
                        backgroundColor: scoreColor(d.score)
                      }}
                    />
                  </div>
                  <div className="w-10 text-right text-xs font-medium" style={{ color: scoreColor(d.score) }}>
                    {d.score || "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}