// src/components/ads/AdSidebar.tsx
"use client"
import { useEffect, useState, useRef } from "react"
import { ExternalLink, ChevronDown, ChevronUp, X, Megaphone, Loader2, Check } from "lucide-react"
import { cn } from "@/lib/utils"
import api from "@/lib/api"

interface Ad {
  id: string
  title: string
  tagline: string
  business_name: string
  category: string
  placement: string
  image_url: string
  cta_label: string
  cta_url: string
  badge: string
}

const CATEGORY_EMOJI: Record<string, string> = {
  spa:"🧖", gym:"💪", nutrition:"🥗", restaurant:"🍽️",
  food_product:"🌿", pharmacy:"💊", mental:"🧠", retreat:"🏔️", other:"✨",
}

const AD_CATEGORIES = [
  { id:"spa",          label:"Spa & Wellness Centre"   },
  { id:"gym",          label:"Gym & Fitness"           },
  { id:"nutrition",    label:"Nutrition Clinic"        },
  { id:"restaurant",   label:"Restaurant & Café"       },
  { id:"food_product", label:"Health Food Product"     },
  { id:"pharmacy",     label:"Pharmacy & Supplements"  },
  { id:"mental",       label:"Mental Health & Therapy" },
  { id:"retreat",      label:"Wellness Retreat"        },
  { id:"other",        label:"Other Health Service"    },
]

const AD_TIERS = [
  { id:"basic",    label:"Basic",    price:"5,000 ETB",  desc:"30 days · sidebar"                    },
  { id:"standard", label:"Standard", price:"12,000 ETB", desc:"60 days · sidebar + banner"           },
  { id:"premium",  label:"Premium",  price:"25,000 ETB", desc:"90 days · all placements + priority"  },
]

let _adCache: { ads: Ad[]; ts: number } | null = null
const AD_TTL_MS = 5 * 60 * 1000
const MAX_SIDEBAR_ADS = 3

// ── Advertise modal ───────────────────────────────────────────────────────────

function AdvertiseModal({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState({
    business_name:"", contact_email:"", contact_phone:"",
    title:"", tagline:"", category:"spa", tier:"basic",
    image_url:"", cta_url:"", cta_label:"Learn more",
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitted,  setSubmitted]  = useState(false)
  const [error,      setError]      = useState("")
  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async () => {
    if (!form.business_name || !form.contact_email || !form.title || !form.cta_url) {
      setError("Please fill in all required fields."); return
    }
    setError(""); setSubmitting(true)
    try {
      await api.post("/ads/submit/", form)
      setSubmitted(true)
    } catch (e: any) {
      setError(e?.response?.data?.error || "Something went wrong. Please try again.")
    } finally { setSubmitting(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-gray-100">
          <div>
            <h2 className="text-base font-bold text-gray-900">Advertise on Well-Net</h2>
            <p className="text-xs text-gray-500 mt-0.5">Reach wellness-focused users across Ethiopia</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        {submitted ? (
          <div className="px-6 py-10 text-center">
            <div className="w-14 h-14 rounded-full bg-wellnet-50 flex items-center justify-center mx-auto mb-4">
              <Check className="w-7 h-7 text-wellnet-500" />
            </div>
            <h3 className="text-sm font-bold text-gray-900 mb-2">Request received!</h3>
            <p className="text-xs text-gray-500 leading-relaxed">
              Our team will contact you at <strong>{form.contact_email}</strong> within 24 hours
              to confirm payment and get your ad live.
            </p>
            <p className="text-xs text-gray-400 mt-3">Payment via bank transfer or CBE Birr after confirmation.</p>
            <button onClick={onClose} className="mt-6 btn-primary px-6 py-2 text-sm">Done</button>
          </div>
        ) : (
          <div className="px-6 py-5 space-y-4">
            {/* Tier */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-2">Choose a plan <span className="text-red-400">*</span></label>
              <div className="space-y-2">
                {AD_TIERS.map(t => (
                  <button key={t.id} onClick={() => set("tier", t.id)}
                    className={cn("w-full flex items-center justify-between px-3 py-2.5 rounded-xl border text-left transition-all",
                      form.tier === t.id ? "border-wellnet-400 bg-wellnet-50" : "border-gray-200 hover:border-gray-300")}>
                    <div>
                      <span className="text-xs font-semibold text-gray-800">{t.label}</span>
                      <span className="text-[10px] text-gray-400 ml-2">{t.desc}</span>
                    </div>
                    <span className={cn("text-xs font-bold", form.tier === t.id ? "text-wellnet-600" : "text-gray-500")}>{t.price}</span>
                  </button>
                ))}
              </div>
            </div>
            {/* Business info */}
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Business name <span className="text-red-400">*</span></label>
                <input value={form.business_name} onChange={e => set("business_name", e.target.value)} placeholder="e.g. Harmony Wellness Spa" className="input w-full text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Email <span className="text-red-400">*</span></label>
                <input type="email" value={form.contact_email} onChange={e => set("contact_email", e.target.value)} placeholder="you@business.com" className="input w-full text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
                <input value={form.contact_phone} onChange={e => set("contact_phone", e.target.value)} placeholder="+251 9…" className="input w-full text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Ad title <span className="text-red-400">*</span></label>
              <input value={form.title} onChange={e => set("title", e.target.value)} placeholder="e.g. Restore Your Balance" className="input w-full text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Short tagline</label>
              <input value={form.tagline} onChange={e => set("tagline", e.target.value)} placeholder="e.g. Premium spa treatments in Addis" className="input w-full text-sm" maxLength={160} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Category <span className="text-red-400">*</span></label>
                <select value={form.category} onChange={e => set("category", e.target.value)} className="input w-full text-sm">
                  {AD_CATEGORIES.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Button text</label>
                <input value={form.cta_label} onChange={e => set("cta_label", e.target.value)} placeholder="Learn more" className="input w-full text-sm" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Website / booking URL <span className="text-red-400">*</span></label>
              <input type="url" value={form.cta_url} onChange={e => set("cta_url", e.target.value)} placeholder="https://yourbusiness.com" className="input w-full text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Ad image URL <span className="text-gray-400 font-normal">(optional)</span></label>
              <input type="url" value={form.image_url} onChange={e => set("image_url", e.target.value)} placeholder="https://…/image.jpg" className="input w-full text-sm" />
            </div>
            {error && <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{error}</p>}
            <p className="text-[10px] text-gray-400 leading-relaxed">
              Payment confirmed via bank transfer or CBE Birr after our team reviews your submission. Your ad goes live only after payment is verified.
            </p>
            <div className="flex gap-3 pt-1">
              <button onClick={onClose} className="flex-1 btn-ghost text-sm">Cancel</button>
              <button onClick={handleSubmit} disabled={submitting}
                className="flex-1 btn-primary text-sm flex items-center justify-center gap-2">
                {submitting ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Submitting…</> : "Submit request"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Ad card ───────────────────────────────────────────────────────────────────

function AdCard({ ad }: { ad: Ad }) {
  const handleClick = () => {
    api.post(`/ads/${ad.id}/click/`).catch(() => {})
    window.open(ad.cta_url, "_blank", "noopener,noreferrer")
  }
  return (
    <div className="rounded-2xl border border-gray-100 bg-white overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {ad.image_url ? (
        <div className="relative w-full aspect-[4/3] bg-gray-50 overflow-hidden">
          <img src={ad.image_url} alt={ad.title} className="w-full h-full object-cover" loading="lazy" />
          {ad.badge && <span className="absolute top-2 left-2 bg-wellnet-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">{ad.badge}</span>}
        </div>
      ) : (
        <div className="relative w-full h-20 bg-gradient-to-br from-wellnet-50 to-wellnet-100 flex items-center justify-center">
          <span className="text-3xl">{CATEGORY_EMOJI[ad.category] ?? "✨"}</span>
          {ad.badge && <span className="absolute top-2 left-2 bg-wellnet-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">{ad.badge}</span>}
        </div>
      )}
      <div className="p-3">
        <div className="flex items-start justify-between gap-1 mb-0.5">
          <div className="text-xs font-bold text-gray-900 leading-snug line-clamp-1">{ad.title}</div>
          <span className="text-[9px] text-gray-400 shrink-0 mt-0.5">Ad</span>
        </div>
        {ad.tagline && <p className="text-[10px] text-gray-500 leading-snug line-clamp-2 mb-2">{ad.tagline}</p>}
        <div className="text-[9px] text-gray-400 mb-2">{CATEGORY_EMOJI[ad.category]} {ad.business_name}</div>
        <button onClick={handleClick} className="w-full bg-wellnet-500 hover:bg-wellnet-600 text-white text-xs font-semibold py-1.5 px-3 rounded-lg flex items-center justify-center gap-1.5 transition-colors">
          {ad.cta_label} <ExternalLink className="w-2.5 h-2.5" />
        </button>
      </div>
    </div>
  )
}

// ── Placeholder slot ──────────────────────────────────────────────────────────

function AdPlaceholder({ onAdvertise }: { onAdvertise: () => void }) {
  return (
    <button onClick={onAdvertise}
      className="w-full rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50/50 hover:border-wellnet-300 hover:bg-wellnet-50/30 transition-all p-4 text-center group">
      <div className="w-8 h-8 rounded-xl bg-white shadow-sm border border-gray-100 flex items-center justify-center mx-auto mb-2 group-hover:border-wellnet-200 transition-colors">
        <Megaphone className="w-4 h-4 text-gray-300 group-hover:text-wellnet-400 transition-colors" />
      </div>
      <div className="text-xs font-semibold text-gray-400 group-hover:text-wellnet-600 transition-colors">Your ad here</div>
      <div className="text-[10px] text-gray-300 mt-0.5 group-hover:text-wellnet-400 transition-colors">from 5,000 ETB / month</div>
    </button>
  )
}

// ── Desktop sidebar ───────────────────────────────────────────────────────────

export function AdSidebarDesktop() {
  const [ads,      setAds]      = useState<Ad[]>([])
  const [loading,  setLoading]  = useState(true)
  const [showForm, setShowForm] = useState(false)
  const fetchedRef = useRef(false)

  useEffect(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true
    if (_adCache && Date.now() - _adCache.ts < AD_TTL_MS) {
      setAds(_adCache.ads); setLoading(false); return
    }
    api.get("/ads/?placement=sidebar&limit=3")
      .then(r => { const list = Array.isArray(r.data) ? r.data : []; _adCache = { ads: list, ts: Date.now() }; setAds(list) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const placeholders = Math.max(0, MAX_SIDEBAR_ADS - ads.length)

  return (
    <>
      <aside className="hidden xl:flex flex-col w-64 shrink-0 gap-3">
        <div className="flex items-center gap-1.5 text-[10px] text-gray-400 font-medium uppercase tracking-wider">
          <Megaphone className="w-3 h-3" /> Sponsored
        </div>
        {loading ? (
          [1,2].map(i => (
            <div key={i} className="rounded-2xl border border-gray-100 overflow-hidden">
              <div className="h-32 bg-gray-100 animate-pulse" />
              <div className="p-3 space-y-2">
                <div className="h-3 bg-gray-100 rounded-full animate-pulse w-3/4" />
                <div className="h-3 bg-gray-100 rounded-full animate-pulse w-full" />
                <div className="h-6 bg-gray-100 rounded-lg animate-pulse mt-3" />
              </div>
            </div>
          ))
        ) : (
          <>
            {ads.map(ad => <AdCard key={ad.id} ad={ad} />)}
            {Array.from({ length: placeholders }).map((_, i) => (
              <AdPlaceholder key={`ph-${i}`} onAdvertise={() => setShowForm(true)} />
            ))}
          </>
        )}
        <button onClick={() => setShowForm(true)}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-xl border border-gray-200 bg-white hover:border-wellnet-300 hover:bg-wellnet-50 transition-all text-xs text-gray-500 hover:text-wellnet-600 font-medium">
          <Megaphone className="w-3 h-3" /> Advertise with us
        </button>
      </aside>
      {showForm && <AdvertiseModal onClose={() => setShowForm(false)} />}
    </>
  )
}

// ── Mobile banner ─────────────────────────────────────────────────────────────

export function AdBannerMobile() {
  const [ad,        setAd]        = useState<Ad | null>(null)
  const [expanded,  setExpanded]  = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const [showForm,  setShowForm]  = useState(false)
  const [loading,   setLoading]   = useState(true)
  const fetchedRef = useRef(false)

  useEffect(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true
    if (_adCache && Date.now() - _adCache.ts < AD_TTL_MS && _adCache.ads.length > 0) {
      setAd(_adCache.ads[0]); setLoading(false); return
    }
    api.get("/ads/?placement=banner&limit=1")
      .then(r => { const list = Array.isArray(r.data) ? r.data : []; if (list.length > 0) { if (!_adCache) _adCache = { ads: list, ts: Date.now() }; setAd(list[0]) } })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (!loading && !ad && !dismissed) return (
    <>
      <div className="xl:hidden fixed bottom-16 left-0 right-0 z-40 px-3 pb-1">
        <button onClick={() => setShowForm(true)}
          className="w-full flex items-center justify-between px-4 py-2.5 rounded-2xl border-2 border-dashed border-gray-200 bg-white shadow-sm">
          <div className="flex items-center gap-2">
            <Megaphone className="w-4 h-4 text-gray-300" />
            <div className="text-left">
              <div className="text-xs font-semibold text-gray-500">Advertise with Well-Net</div>
              <div className="text-[10px] text-gray-400">Reach wellness users · from 5,000 ETB</div>
            </div>
          </div>
          <span className="text-[10px] text-wellnet-600 font-semibold border border-wellnet-200 bg-wellnet-50 px-2 py-1 rounded-lg">Learn more</span>
        </button>
      </div>
      {showForm && <AdvertiseModal onClose={() => setShowForm(false)} />}
    </>
  )

  if (loading || !ad || dismissed) return null

  return (
    <>
      <div className="xl:hidden fixed bottom-16 left-0 right-0 z-40 px-3 pb-1">
        <div className="rounded-2xl border border-gray-200 bg-white shadow-lg overflow-hidden">
          <button onClick={() => setExpanded(e => !e)} className="w-full flex items-center gap-3 px-3 py-2.5">
            <div className="w-8 h-8 rounded-xl bg-wellnet-50 flex items-center justify-center shrink-0 text-base overflow-hidden">
              {ad.image_url ? <img src={ad.image_url} alt="" className="w-full h-full object-cover rounded-xl" /> : CATEGORY_EMOJI[ad.category] ?? "✨"}
            </div>
            <div className="flex-1 min-w-0 text-left">
              <div className="text-xs font-semibold text-gray-800 truncate">{ad.title}</div>
              <div className="text-[10px] text-gray-400 truncate">{ad.business_name}</div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[9px] text-gray-400">Ad</span>
              {expanded ? <ChevronDown className="w-3.5 h-3.5 text-gray-400" /> : <ChevronUp className="w-3.5 h-3.5 text-gray-400" />}
            </div>
          </button>
          {expanded && (
            <div className="border-t border-gray-100 px-3 pb-3 pt-2">
              {ad.tagline && <p className="text-xs text-gray-500 mb-2.5 leading-relaxed">{ad.tagline}</p>}
              <div className="flex gap-2">
                <button onClick={() => { api.post(`/ads/${ad.id}/click/`).catch(()=>{}); window.open(ad.cta_url,"_blank","noopener,noreferrer") }}
                  className="flex-1 bg-wellnet-500 hover:bg-wellnet-600 text-white text-xs font-semibold py-2 rounded-xl flex items-center justify-center gap-1.5 transition-colors">
                  {ad.cta_label} <ExternalLink className="w-3 h-3" />
                </button>
                <button onClick={() => setDismissed(true)} className="px-3 py-2 rounded-xl border border-gray-200 text-xs text-gray-400">Close</button>
              </div>
            </div>
          )}
        </div>
      </div>
      {showForm && <AdvertiseModal onClose={() => setShowForm(false)} />}
    </>
  )
}