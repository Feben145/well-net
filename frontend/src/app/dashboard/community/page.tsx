"use client"
import { useEffect, useState, useCallback } from "react"
import {
  Users, Coffee, Heart, Coins, Globe,
  Plus, ChevronRight, Loader2, X, Copy,
  Check, AlertTriangle, ThumbsUp, Search,
} from "lucide-react"
import { communityService, foodService, extractArray } from "@/services/wellnet"
import { useAuthStore } from "@/store"
import GutScoreRing from "@/components/wellness/GutScoreRing"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import type { EthiopianFood } from "@/types"

// ── Local types ───────────────────────────────────────────────────────────────
interface Member  { id: string; username: string; display_name: string; role: string; circle_gut_score: number; gursha_given: number; gursha_received: number; edir_contributed: number }
interface Circle  { id: string; name: string; name_am: string; emoji: string; invite_code: string; member_count: number; max_members: number; group_gut_score: number; group_streak_days: number; edir_balance_etb: number; edir_goal_etb: number; edir_progress_pct: number; edir_target_pkg: string; members: Member[]; is_member: boolean; my_role: string; is_public: boolean }
interface Checkin { id: string; username: string; display_name: string; food_name: string; food_name_am: string; gut_score: number; message: string; mood_emoji: string }
interface Gursha  { id: string; from_username: string; food_name: string; food_name_am: string; message: string; status: string; is_expired: boolean }
interface Post    { id: string; author: { username: string; display_name: string }; post_type: string; title: string; body: string; emoji: string; score: number; streak: number; likes: number }

const TABS = [
  { id: "circles", label: "My Circles",  icon: Users  },
  { id: "jebena",  label: "Jebena ☕",   icon: Coffee },
  { id: "gursha",  label: "Gursha 🤝",   icon: Heart  },
  { id: "edir",    label: "Edir 💰",     icon: Coins  },
  { id: "feed",    label: "Community",   icon: Globe  },
]

const MOODS    = ["🌿","😊","💪","🙏","🔥","✨","💚","🌱"]
const EMOJIS   = ["🌿","🏃","🧘","🌱","💚","⚡","🌊","🌸","🦁","🐝"]

// ── Page ──────────────────────────────────────────────────────────────────────
export default function CommunityPage() {
  const { user } = useAuthStore()
  const [tab,          setTab]          = useState("circles")
  const [circles,      setCircles]      = useState<Circle[]>([])
  const [activeCircle, setActiveCircle] = useState<Circle | null>(null)
  const [jebenaFeed,   setJebenaFeed]   = useState<Checkin[]>([])
  const [gursha,       setGursha]       = useState<Gursha[]>([])
  const [feed,         setFeed]         = useState<Post[]>([])
  const [foods,        setFoods]        = useState<EthiopianFood[]>([])
  const [loading,      setLoading]      = useState(true)

  // Modal visibility
  const [showCreate, setShowCreate] = useState(false)
  const [showJoin,   setShowJoin]   = useState(false)
  const [showJebena, setShowJebena] = useState(false)
  const [showGursha, setShowGursha] = useState(false)
  const [showEdir,   setShowEdir]   = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [cRes, gRes, fRes, foodRes] = await Promise.allSettled([
        communityService.myCircles(),
        communityService.myGursha(),
        communityService.feed(),
        foodService.list(),
      ])
      if (cRes.status === "fulfilled") {
        const arr = extractArray<Circle>(cRes.value.data)
        setCircles(arr)
        if (arr.length > 0) {
          setActiveCircle(arr[0])
          loadJebena(arr[0].id)
        }
      }
      if (gRes.status === "fulfilled") setGursha(extractArray<Gursha>(gRes.value.data))
      if (fRes.status === "fulfilled") setFeed(extractArray<Post>(fRes.value.data))
      if (foodRes.status === "fulfilled") setFoods(extractArray<EthiopianFood>(foodRes.value.data))
    } finally {
      setLoading(false)
    }
  }, [])

  const loadJebena = async (circleId: string) => {
    try {
      const r = await communityService.circleFeed(circleId)
      setJebenaFeed(extractArray<Checkin>(r.data))
    } catch {}
  }

  useEffect(() => { load() }, [load])

  const selectCircle = (c: Circle) => {
    setActiveCircle(c)
    loadJebena(c.id)
  }

  const copyCode = (code: string) => {
    navigator.clipboard?.writeText(code).catch(() => {})
    toast.success(`Code ${code} copied!`)
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-5">

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Users className="w-5 h-5 text-wellnet-500" />
          Wellness Community
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Circle together — Ethiopian wellness is communal
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-hide">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={cn(
              "shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-all",
              tab === t.id
                ? "bg-wellnet-500 text-white border-wellnet-500"
                : "bg-white text-gray-600 border-gray-200 hover:border-wellnet-300"
            )}
          >
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {/* ── CIRCLES ────────────────────────────────────────────────────────── */}
      {tab === "circles" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-1.5 px-4 py-2 text-sm">
              <Plus className="w-4 h-4" /> Create circle
            </button>
            <button onClick={() => setShowJoin(true)} className="btn-secondary flex items-center gap-1.5 px-4 py-2 text-sm">
              Join with code
            </button>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1,2].map(i => <div key={i} className="h-36 bg-gray-100 rounded-2xl animate-pulse" />)}
            </div>
          ) : circles.length === 0 ? (
            <div className="card text-center py-12">
              <Users className="w-10 h-10 text-gray-200 mx-auto mb-3" />
              <p className="text-sm font-semibold text-gray-700 mb-1">No wellness circles yet</p>
              <p className="text-xs text-gray-400 mb-4 max-w-xs mx-auto">
                Create a circle with family, friends, or coworkers and share your wellness journey together.
              </p>
              <button onClick={() => setShowCreate(true)} className="btn-primary inline-flex items-center gap-2">
                <Plus className="w-4 h-4" /> Create first circle
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {circles.map(c => (
                <button key={c.id} onClick={() => { selectCircle(c); setTab("jebena") }}
                  className="card w-full text-left hover:shadow-md hover:border-wellnet-200 transition-all"
                >
                  <div className="flex items-start gap-3">
                    {/* Emoji avatar */}
                    <div className="w-12 h-12 rounded-2xl bg-wellnet-50 flex items-center justify-center text-2xl shrink-0">
                      {c.emoji}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-bold text-gray-900">{c.name}</span>
                        {c.name_am && <span className="text-xs text-gray-400">({c.name_am})</span>}
                        {c.my_role === "admin" && <span className="badge-amber text-[10px]">Admin</span>}
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{c.member_count} / {c.max_members} members</p>

                      {/* Stats row */}
                      <div className="flex gap-2 mt-2">
                        <div className="bg-wellnet-50 rounded-xl px-2.5 py-1.5 text-center">
                          <div className="text-[9px] text-wellnet-600">Group score</div>
                          <div className="text-sm font-bold text-wellnet-700">{c.group_gut_score || "—"}</div>
                        </div>
                        <div className="bg-amber-50 rounded-xl px-2.5 py-1.5 text-center">
                          <div className="text-[9px] text-amber-600">🔥 Streak</div>
                          <div className="text-sm font-bold text-amber-700">{c.group_streak_days}d</div>
                        </div>
                        <div className="bg-purple-50 rounded-xl px-2.5 py-1.5 text-center">
                          <div className="text-[9px] text-purple-600">💰 Edir</div>
                          <div className="text-sm font-bold text-purple-700">{c.edir_progress_pct}%</div>
                        </div>
                      </div>
                    </div>

                    {/* Invite code chip */}
                    <button
                      onClick={e => { e.stopPropagation(); copyCode(c.invite_code) }}
                      className="shrink-0 flex items-center gap-1 bg-gray-100 hover:bg-gray-200 px-2 py-1 rounded-lg text-[10px] font-mono text-gray-600 transition-colors"
                    >
                      {c.invite_code} <Copy className="w-2.5 h-2.5" />
                    </button>
                  </div>

                  {/* Member avatars + open hint */}
                  <div className="flex items-center gap-1 mt-3 pt-3 border-t border-gray-100">
                    {c.members.slice(0, 6).map((m, i) => (
                      <div key={i} title={m.display_name || m.username}
                        className="w-6 h-6 rounded-full bg-wellnet-100 text-wellnet-700 text-[9px] font-bold flex items-center justify-center border-2 border-white"
                      >
                        {(m.display_name || m.username)[0].toUpperCase()}
                      </div>
                    ))}
                    {c.member_count > 6 && (
                      <span className="text-[10px] text-gray-400 ml-1">+{c.member_count - 6}</span>
                    )}
                    <span className="ml-auto text-[10px] text-wellnet-600 font-medium flex items-center gap-1">
                      Open <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── JEBENA ─────────────────────────────────────────────────────────── */}
      {tab === "jebena" && (
        <div className="space-y-4">
          {/* Circle selector */}
          {circles.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
              {circles.map(c => (
                <button key={c.id} onClick={() => selectCircle(c)}
                  className={cn(
                    "shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all",
                    activeCircle?.id === c.id
                      ? "bg-wellnet-500 text-white border-wellnet-500"
                      : "bg-white text-gray-600 border-gray-200 hover:border-wellnet-300"
                  )}
                >
                  {c.emoji} {c.name}
                </button>
              ))}
            </div>
          )}

          {/* Hero card */}
          <div className="card bg-gradient-to-br from-amber-50 to-wellnet-50 border-amber-200">
            <div className="flex items-start gap-3 mb-3">
              <span className="text-3xl">☕</span>
              <div>
                <p className="text-sm font-bold text-amber-800">Jebena moment</p>
                <p className="text-xs text-amber-600 leading-relaxed">
                  Daily wellness check-in — log one food, share with your circle.
                  Like the coffee ceremony, but for gut health.
                </p>
              </div>
            </div>
            {activeCircle && (
              <div className="flex items-center gap-3 mb-3">
                <div className="flex-1 bg-white/60 rounded-xl px-3 py-2">
                  <p className="text-[10px] text-gray-500 mb-0.5">{activeCircle.name} group score</p>
                  <p className="text-2xl font-bold text-wellnet-600">
                    {activeCircle.group_gut_score > 0 ? `${activeCircle.group_gut_score}` : "—"}
                    <span className="text-sm font-normal text-gray-400"> / 100</span>
                  </p>
                </div>
                <span className="text-3xl">
                  {(activeCircle.group_gut_score || 0) >= 75 ? "🏆" : (activeCircle.group_gut_score || 0) >= 55 ? "💪" : "🌱"}
                </span>
              </div>
            )}
            <button
              onClick={() => { if (!activeCircle) { toast.error("Create or join a circle first"); return }; setShowJebena(true) }}
              className="w-full btn-primary flex items-center justify-center gap-2 py-2.5"
            >
              <Coffee className="w-4 h-4" /> Log my Jebena food
            </button>
          </div>

          {/* Today's check-ins */}
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-2">Today's check-ins</p>
            {jebenaFeed.length === 0 ? (
              <div className="card text-center py-8">
                <Coffee className="w-8 h-8 text-amber-200 mx-auto mb-2" />
                <p className="text-sm text-gray-400">
                  No check-ins yet. Be the first to pour the jebena ☕
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {jebenaFeed.map(c => (
                  <div key={c.id} className="card flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-wellnet-100 text-wellnet-700 font-bold text-sm flex items-center justify-center shrink-0">
                      {(c.display_name || c.username)[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-sm font-semibold text-gray-800">{c.display_name || c.username}</span>
                        <span className="text-base">{c.mood_emoji}</span>
                      </div>
                      <div className="text-xs mt-0.5">
                        {c.food_name_am && <span className="font-bold text-gray-700">{c.food_name_am} </span>}
                        <span className="text-gray-400">({c.food_name})</span>
                      </div>
                      {c.message && <p className="text-xs text-gray-500 italic mt-0.5">"{c.message}"</p>}
                    </div>
                    <GutScoreRing score={c.gut_score} size="sm" showLabel={false} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── GURSHA ─────────────────────────────────────────────────────────── */}
      {tab === "gursha" && (
        <div className="space-y-4">
          <div className="card bg-gradient-to-br from-pink-50 to-wellnet-50 border-pink-100">
            <div className="flex items-start gap-3 mb-3">
              <span className="text-3xl">🤝</span>
              <div>
                <p className="text-sm font-bold text-pink-800">Gursha challenge</p>
                <p className="text-xs text-pink-600 leading-relaxed">
                  In Ethiopian culture, gursha means feeding a loved one from your own hand.
                  Recommend a food to a circle member — when they log it, both earn points.
                </p>
              </div>
            </div>
            <button
              onClick={() => { if (!activeCircle) { toast.error("Join a circle first"); return }; setShowGursha(true) }}
              className="w-full btn-primary flex items-center justify-center gap-2"
            >
              <Heart className="w-4 h-4" /> Send a Gursha
            </button>
          </div>

          {/* Pending gursha for me */}
          {gursha.length > 0 ? (
            <div>
              <p className="text-sm font-semibold text-gray-700 mb-2">
                Waiting for you ({gursha.length})
              </p>
              <div className="space-y-2">
                {gursha.map(g => (
                  <GurshaCard key={g.id} gursha={g} onAccept={async () => {
                    try {
                      await communityService.acceptGursha(g.id)
                      toast.success("Gursha accepted! +15 points 🌿")
                      setGursha(prev => prev.filter(x => x.id !== g.id))
                    } catch {
                      toast.error("Could not accept — may have expired")
                    }
                  }} />
                ))}
              </div>
            </div>
          ) : (
            <div className="card text-center py-6">
              <Heart className="w-8 h-8 text-pink-200 mx-auto mb-2" />
              <p className="text-sm text-gray-400">No pending Gursha challenges.</p>
              <p className="text-xs text-gray-400 mt-1">Send one to a circle member above!</p>
            </div>
          )}
        </div>
      )}

      {/* ── EDIR ───────────────────────────────────────────────────────────── */}
      {tab === "edir" && (
        <div className="space-y-4">
          <div className="card bg-gradient-to-br from-purple-50 to-wellnet-50 border-purple-100">
            <div className="flex items-start gap-3">
              <span className="text-3xl">💰</span>
              <div>
                <p className="text-sm font-bold text-purple-800">Edir wellness fund</p>
                <p className="text-xs text-purple-600 leading-relaxed">
                  Like a traditional Ethiopian edir — your circle pools small amounts toward
                  a shared Kuriftu wellness experience. When the goal is reached, book together!
                </p>
              </div>
            </div>
          </div>

          {circles.length === 0 ? (
            <div className="card text-center py-6 text-sm text-gray-400">
              Join or create a circle first to start an edir fund.
            </div>
          ) : (
            circles.map(c => (
              <div key={c.id} className="card">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xl">{c.emoji}</span>
                  <div>
                    <p className="text-sm font-bold text-gray-800">{c.name}</p>
                    <p className="text-xs text-gray-500">Goal: {c.edir_target_pkg}</p>
                  </div>
                </div>

                {/* Progress */}
                <div className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">Fund progress</span>
                    <span className="font-bold text-purple-600">{c.edir_progress_pct}%</span>
                  </div>
                  <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full transition-all duration-700"
                      style={{ width: `${c.edir_progress_pct}%` }} />
                  </div>
                  <div className="flex justify-between text-xs mt-1 text-gray-400">
                    <span>{Number(c.edir_balance_etb).toLocaleString()} ETB raised</span>
                    <span>Goal: {Number(c.edir_goal_etb).toLocaleString()} ETB</span>
                  </div>
                </div>

                {c.edir_progress_pct >= 100 ? (
                  <div className="bg-wellnet-50 border border-wellnet-200 rounded-xl p-3 text-center">
                    <p className="text-sm font-bold text-wellnet-700 mb-2">🎉 Goal reached! Book together!</p>
                    <a href="https://kurifturesorts.com" target="_blank" rel="noopener"
                      className="btn-primary text-sm px-6 inline-block">
                      Book Kuriftu group experience
                    </a>
                  </div>
                ) : (
                  <button onClick={() => { setActiveCircle(c); setShowEdir(true) }}
                    className="w-full btn-secondary flex items-center justify-center gap-2">
                    <Coins className="w-4 h-4" /> Contribute to fund
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* ── COMMUNITY FEED ─────────────────────────────────────────────────── */}
      {tab === "feed" && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">Public wellness wins from the community</p>
          {loading ? (
            [...Array(3)].map((_,i) => <div key={i} className="h-20 bg-gray-100 rounded-2xl animate-pulse" />)
          ) : feed.length === 0 ? (
            <div className="card text-center py-8">
              <Globe className="w-8 h-8 text-gray-200 mx-auto mb-2" />
              <p className="text-sm text-gray-400">No public posts yet.</p>
              <p className="text-xs text-gray-400 mt-1">Make your circle public so wins appear here.</p>
            </div>
          ) : (
            feed.map(post => (
              <FeedPostCard key={post.id} post={post} onLike={async () => {
                try {
                  await communityService.likePost(post.id)
                  setFeed(prev => prev.map(p => p.id === post.id ? { ...p, likes: p.likes + 1 } : p))
                } catch {}
              }} />
            ))
          )}
        </div>
      )}

      {/* ── MODALS ─────────────────────────────────────────────────────────── */}
      {showCreate && (
        <CreateCircleModal
          onClose={() => setShowCreate(false)}
          onCreate={async data => {
            try {
              const r = await communityService.createCircle(data)
              toast.success(`${data.emoji} ${data.name} created! Code: ${r.data.invite_code}`)
              setShowCreate(false)
              load()
            } catch { toast.error("Could not create circle") }
          }}
        />
      )}

      {showJoin && (
        <JoinModal
          onClose={() => setShowJoin(false)}
          onJoin={async code => {
            try {
              await communityService.joinCircle(code)
              toast.success("Joined! Welcome to the circle 🌿")
              setShowJoin(false)
              load()
            } catch { toast.error("Invalid invite code — check and try again") }
          }}
        />
      )}

      {showJebena && activeCircle && (
        <JebenaModal
          circle={activeCircle}
          foods={foods}
          onClose={() => setShowJebena(false)}
          onCheckin={async data => {
            try {
              const r = await communityService.jebenaCheckin({ circle_id: activeCircle.id, ...data })
              toast.success(`☕ Logged! Score: ${r.data.gut_score}/100`)
              setShowJebena(false)
              loadJebena(activeCircle.id)
            } catch { toast.error("Already checked in today, or food not found") }
          }}
        />
      )}

      {showGursha && activeCircle && (
        <GurshaModal
          circle={activeCircle}
          foods={foods}
          currentUsername={user?.username || ""}
          onClose={() => setShowGursha(false)}
          onSend={async data => {
            try {
              await communityService.sendGursha({ circle_id: activeCircle.id, ...data })
              toast.success(`Gursha sent to @${data.to_username} 🤝`)
              setShowGursha(false)
            } catch { toast.error("Could not send Gursha — check the username") }
          }}
        />
      )}

      {showEdir && activeCircle && (
        <EdirModal
          circle={activeCircle}
          onClose={() => setShowEdir(false)}
          onContribute={async (amount, note) => {
            try {
              const r = await communityService.contributeEdir(activeCircle.id, amount, note)
              toast.success(`${amount} ETB contributed! Fund at ${r.data.progress_pct}% 💰`)
              setShowEdir(false)
              load()
            } catch { toast.error("Could not process contribution") }
          }}
        />
      )}
    </div>
  )
}

// ── Gursha card ────────────────────────────────────────────────────────────────
function GurshaCard({ gursha, onAccept }: { gursha: Gursha; onAccept: () => void }) {
  const [busy, setBusy] = useState(false)
  return (
    <div className="card border-pink-100 bg-pink-50">
      <div className="flex items-start gap-3">
        <span className="text-2xl shrink-0">🤝</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-800">@{gursha.from_username} is feeding you</p>
          <div className="text-xs mt-0.5">
            {gursha.food_name_am && <span className="font-bold text-gray-700">{gursha.food_name_am} </span>}
            <span className="text-gray-400">({gursha.food_name})</span>
          </div>
          {gursha.message && <p className="text-xs text-pink-700 italic mt-1">"{gursha.message}"</p>}
          {gursha.is_expired && (
            <div className="flex items-center gap-1 mt-1.5 text-xs text-amber-600">
              <AlertTriangle className="w-3 h-3" /> Expired
            </div>
          )}
        </div>
        {!gursha.is_expired && (
          <button
            onClick={async () => { setBusy(true); await onAccept(); setBusy(false) }}
            disabled={busy}
            className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1 shrink-0"
          >
            {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
            Accept
          </button>
        )}
      </div>
    </div>
  )
}

// ── Feed post card ─────────────────────────────────────────────────────────────
function FeedPostCard({ post, onLike }: { post: Post; onLike: () => void }) {
  const COLORS: Record<string, string> = {
    streak:"bg-amber-50 border-amber-200", score:"bg-wellnet-50 border-wellnet-200",
    gursha:"bg-pink-50 border-pink-200",   jebena:"bg-orange-50 border-orange-200",
    kuriftu:"bg-blue-50 border-blue-200",  challenge:"bg-purple-50 border-purple-200",
  }
  return (
    <div className={cn("card border", COLORS[post.post_type] ?? "bg-gray-50")}>
      <div className="flex items-start gap-3">
        <span className="text-2xl shrink-0">{post.emoji}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-gray-800">
              {post.author?.display_name || post.author?.username}
            </span>
            {post.score > 0 && <span className="badge-teal text-[10px]">{post.score}/100</span>}
            {post.streak > 0 && <span className="badge-amber text-[10px]">🔥 {post.streak}d</span>}
          </div>
          <p className="text-sm font-semibold text-gray-900 mt-0.5">{post.title}</p>
          {post.body && <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{post.body}</p>}
        </div>
      </div>
      <div className="flex justify-end mt-2 pt-2 border-t border-gray-100">
        <button onClick={onLike}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-wellnet-600 transition-colors">
          <ThumbsUp className="w-3.5 h-3.5" /> {post.likes}
        </button>
      </div>
    </div>
  )
}

// ── Modal shell ────────────────────────────────────────────────────────────────
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/30"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-3xl w-full max-w-sm shadow-2xl max-h-[88vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-100">
          <h3 className="text-base font-bold text-gray-900">{title}</h3>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center">
            <X className="w-4 h-4 text-gray-600" />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  )
}

// Toggle helper
function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <div onClick={() => onChange(!value)}
        className={cn("w-10 h-6 rounded-full relative transition-colors shrink-0", value ? "bg-wellnet-500" : "bg-gray-200")}>
        <div className={cn("absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all", value ? "left-5" : "left-1")} />
      </div>
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  )
}

// ── Create circle modal ────────────────────────────────────────────────────────
function CreateCircleModal({ onClose, onCreate }: { onClose: () => void; onCreate: (d: any) => void }) {
  const [name, setName] = useState("")
  const [nameAm, setNameAm] = useState("")
  const [emoji, setEmoji] = useState("🌿")
  const [isPublic, setPublic] = useState(false)
  const [saving, setSaving] = useState(false)

  return (
    <Modal title="Create a wellness circle" onClose={onClose}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Circle name *</label>
          <input value={name} onChange={e => setName(e.target.value)}
            placeholder="e.g. Addis Wellness Crew" className="input" autoFocus />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Amharic name (optional)</label>
          <input value={nameAm} onChange={e => setNameAm(e.target.value)}
            placeholder="የአዲስ ጤና ቡድን" className="input" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-2">Circle emoji</label>
          <div className="flex gap-2 flex-wrap">
            {EMOJIS.map(e => (
              <button key={e} onClick={() => setEmoji(e)}
                className={cn("w-9 h-9 rounded-xl text-xl flex items-center justify-center border transition-all",
                  emoji === e ? "border-wellnet-400 bg-wellnet-50" : "border-gray-200 hover:border-gray-300")}>
                {e}
              </button>
            ))}
          </div>
        </div>
        <Toggle label="Show wins on community feed" value={isPublic} onChange={setPublic} />
        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 btn-ghost">Cancel</button>
          <button disabled={!name.trim() || saving}
            onClick={async () => { setSaving(true); await onCreate({ name, name_am: nameAm, emoji, is_public: isPublic }); setSaving(false) }}
            className="flex-1 btn-primary flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Plus className="w-4 h-4" /> Create</>}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ── Join circle modal ──────────────────────────────────────────────────────────
function JoinModal({ onClose, onJoin }: { onClose: () => void; onJoin: (code: string) => void }) {
  const [code, setCode] = useState("")
  const [saving, setSaving] = useState(false)
  return (
    <Modal title="Join a wellness circle" onClose={onClose}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Invite code</label>
          <input value={code} onChange={e => setCode(e.target.value.toUpperCase())}
            placeholder="e.g. JEBENA42" maxLength={8}
            className="input font-mono tracking-widest text-center text-lg" />
          <p className="text-xs text-gray-400 mt-1 text-center">
            Ask a circle member to share their 8-character code
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 btn-ghost">Cancel</button>
          <button disabled={code.length < 6 || saving}
            onClick={async () => { setSaving(true); await onJoin(code); setSaving(false) }}
            className="flex-1 btn-primary flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Join circle"}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ── Jebena modal ───────────────────────────────────────────────────────────────
function JebenaModal({ circle, foods, onClose, onCheckin }: {
  circle: Circle; foods: EthiopianFood[]
  onClose: () => void; onCheckin: (d: any) => void
}) {
  const [foodSlug, setFoodSlug] = useState("")
  const [message, setMessage] = useState("")
  const [mood, setMood] = useState("🌿")
  const [query, setQuery] = useState("")
  const [saving, setSaving] = useState(false)

  const filtered = foods.filter(f =>
    !query ||
    f.name_en.toLowerCase().includes(query.toLowerCase()) ||
    (f.name_am && f.name_am.includes(query))
  ).slice(0, 12)

  return (
    <Modal title={`☕ Jebena — ${circle.name}`} onClose={onClose}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">What did you eat today? *</label>
          <div className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input value={query} onChange={e => setQuery(e.target.value)}
              placeholder="Search Ethiopian foods…" className="input pl-8 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-1.5 max-h-44 overflow-y-auto">
            {filtered.map(f => (
              <button key={f.slug} onClick={() => { setFoodSlug(f.slug); setQuery("") }}
                className={cn("text-left px-3 py-2 rounded-xl border text-xs transition-all",
                  foodSlug === f.slug
                    ? "bg-wellnet-500 text-white border-wellnet-500"
                    : "bg-white border-gray-200 hover:border-wellnet-300")}>
                {f.name_am && <span className="font-bold block">{f.name_am}</span>}
                <span className={foodSlug === f.slug ? "text-white/80" : "text-gray-500"}>
                  {f.name_en.split(" — ")[0].split(" (")[0]}
                </span>
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="col-span-2 text-xs text-gray-400 text-center py-3">No foods found</p>
            )}
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Mood</label>
          <div className="flex gap-2 flex-wrap">
            {MOODS.map(m => (
              <button key={m} onClick={() => setMood(m)}
                className={cn("w-9 h-9 rounded-xl text-xl flex items-center justify-center border transition-all",
                  mood === m ? "border-wellnet-400 bg-wellnet-50" : "border-gray-200 hover:border-gray-300")}>
                {m}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Message to circle (optional)</label>
          <input value={message} onChange={e => setMessage(e.target.value)}
            placeholder="Good morning! Starting strong 💪" className="input" maxLength={200} />
        </div>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 btn-ghost">Cancel</button>
          <button disabled={!foodSlug || saving}
            onClick={async () => { setSaving(true); await onCheckin({ food_slug: foodSlug, message, mood_emoji: mood }); setSaving(false) }}
            className="flex-1 btn-primary flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Coffee className="w-4 h-4" /> Log Jebena</>}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ── Gursha modal ───────────────────────────────────────────────────────────────
function GurshaModal({ circle, foods, currentUsername, onClose, onSend }: {
  circle: Circle; foods: EthiopianFood[]; currentUsername: string
  onClose: () => void; onSend: (d: any) => void
}) {
  const [toUser, setToUser] = useState("")
  const [foodSlug, setFoodSlug] = useState("")
  const [message, setMessage] = useState("")
  const [saving, setSaving] = useState(false)

  const otherMembers = circle.members.filter(m => m.username !== currentUsername)

  return (
    <Modal title="🤝 Send a Gursha" onClose={onClose}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Send to *</label>
          {otherMembers.length === 0 ? (
            <p className="text-xs text-gray-400 py-2">No other members in this circle yet.</p>
          ) : (
            <div className="grid grid-cols-2 gap-1.5">
              {otherMembers.map(m => (
                <button key={m.username} onClick={() => setToUser(m.username)}
                  className={cn("flex items-center gap-2 px-3 py-2 rounded-xl border text-xs transition-all",
                    toUser === m.username
                      ? "bg-wellnet-500 text-white border-wellnet-500"
                      : "bg-white border-gray-200 hover:border-wellnet-300")}>
                  <div className="w-6 h-6 rounded-full bg-wellnet-100 text-wellnet-700 text-[9px] font-bold flex items-center justify-center shrink-0">
                    {(m.display_name || m.username)[0].toUpperCase()}
                  </div>
                  <span className="truncate">{m.display_name || m.username}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Recommend this food *</label>
          <div className="grid grid-cols-2 gap-1.5 max-h-36 overflow-y-auto">
            {foods.slice(0, 12).map(f => (
              <button key={f.slug} onClick={() => setFoodSlug(f.slug)}
                className={cn("text-left px-3 py-2 rounded-xl border text-xs transition-all",
                  foodSlug === f.slug
                    ? "bg-wellnet-500 text-white border-wellnet-500"
                    : "bg-white border-gray-200 hover:border-wellnet-300")}>
                {f.name_am && <span className="font-bold block">{f.name_am}</span>}
                <span className={foodSlug === f.slug ? "text-white/80" : "text-gray-500"}>
                  {f.name_en.split(" — ")[0].split(" (")[0]}
                </span>
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Message (optional)</label>
          <input value={message} onChange={e => setMessage(e.target.value)}
            placeholder="Try this today — it'll boost your score!" className="input" maxLength={200} />
        </div>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 btn-ghost">Cancel</button>
          <button disabled={!toUser || !foodSlug || saving}
            onClick={async () => { setSaving(true); await onSend({ to_username: toUser, food_slug: foodSlug, message }); setSaving(false) }}
            className="flex-1 btn-primary flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Heart className="w-4 h-4" /> Send Gursha</>}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ── Edir modal ─────────────────────────────────────────────────────────────────
function EdirModal({ circle, onClose, onContribute }: {
  circle: Circle; onClose: () => void
  onContribute: (amount: number, note: string) => void
}) {
  const [amount, setAmount] = useState("")
  const [note, setNote] = useState("")
  const [saving, setSaving] = useState(false)
  const PRESETS = [10, 20, 50, 100]

  return (
    <Modal title={`💰 Contribute to ${circle.name}`} onClose={onClose}>
      <div className="space-y-4">
        {/* Current fund status */}
        <div className="bg-purple-50 rounded-2xl p-4 text-center">
          <p className="text-xs text-purple-500 mb-1">Current fund</p>
          <p className="text-xl font-bold text-purple-700">
            {Number(circle.edir_balance_etb).toLocaleString()} / {Number(circle.edir_goal_etb).toLocaleString()} ETB
          </p>
          <div className="h-2 bg-purple-100 rounded-full mt-2 overflow-hidden">
            <div className="h-full bg-purple-500 rounded-full transition-all"
              style={{ width: `${circle.edir_progress_pct}%` }} />
          </div>
          <p className="text-[10px] text-purple-400 mt-1">{circle.edir_progress_pct}% of goal</p>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Amount (ETB) *</label>
          <div className="grid grid-cols-4 gap-2 mb-2">
            {PRESETS.map(p => (
              <button key={p} onClick={() => setAmount(String(p))}
                className={cn("py-2 rounded-xl border text-sm font-medium transition-all",
                  amount === String(p)
                    ? "bg-wellnet-500 text-white border-wellnet-500"
                    : "bg-white border-gray-200 hover:border-gray-300")}>
                {p}
              </button>
            ))}
          </div>
          <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
            placeholder="Or enter custom amount" className="input" min={1} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1.5">Note (optional)</label>
          <input value={note} onChange={e => setNote(e.target.value)}
            placeholder="For the Kuriftu group trip!" className="input" />
        </div>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 btn-ghost">Cancel</button>
          <button disabled={!amount || Number(amount) <= 0 || saving}
            onClick={async () => { setSaving(true); await onContribute(Number(amount), note); setSaving(false) }}
            className="flex-1 btn-primary flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Coins className="w-4 h-4" /> Contribute</>}
          </button>
        </div>
      </div>
    </Modal>
  )
}