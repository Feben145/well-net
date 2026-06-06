"use client"

import { useEffect, useState } from "react"
import {
  Star,
  BadgeCheck,
  Globe,
  Calendar,
  Loader2,
} from "lucide-react"

import {
  expertService,
  extractArray,
} from "@/services/wellnet"

import type { Professional } from "@/types"

import { cn } from "@/lib/utils"
import { toast } from "sonner"

// Demo fallback data
const DEMO: Professional[] = [
  {
    id: "1",
    display_name: "Hana Bekele",
    title: "RD",
    specialty: "dietitian",
    bio: "Registered Dietitian specialising in Ethiopian gut health and pregnancy nutrition. Black Lion Hospital affiliated.",
    languages: ["Amharic", "English"],
    session_types: ["video", "in-person"],
    session_price_etb: 320,
    offpeak_price_etb: 220,
    rating: 4.9,
    review_count: 42,
    is_verified: true,
    is_kuriftu_partner: true,
    avatar_url: "",
    license_body: "moh",
  },
  {
    id: "2",
    display_name: "Tesfaye Girma",
    title: "Dr.",
    specialty: "gastroenterologist",
    bio: "Gastroenterologist at Black Lion Hospital. Specialist in IBS, IBD, and gut microbiome research.",
    languages: ["Amharic", "English"],
    session_types: ["video", "group"],
    session_price_etb: 650,
    offpeak_price_etb: 450,
    rating: 4.8,
    review_count: 28,
    is_verified: true,
    is_kuriftu_partner: false,
    avatar_url: "",
    license_body: "fmhaca",
  },
  {
    id: "3",
    display_name: "Selam Mekonnen",
    title: "CNS",
    specialty: "nutritionist",
    bio: "Certified Nutrition Specialist and Kuriftu Wellness partner. Expert in corporate wellness and teff-based diets.",
    languages: ["Amharic"],
    session_types: ["in-person", "group"],
    session_price_etb: 280,
    offpeak_price_etb: 180,
    rating: 4.7,
    review_count: 61,
    is_verified: true,
    is_kuriftu_partner: true,
    avatar_url: "",
    license_body: "kuriftu",
  },
  {
    id: "4",
    display_name: "Weini Tekle",
    title: "",
    specialty: "yoga_instructor",
    bio: "Yoga instructor partnered with Kuriftu Resorts. Iyengar yoga and mat pilates for mindful wellness journeys.",
    languages: ["Amharic", "English"],
    session_types: ["in-person", "group"],
    session_price_etb: 200,
    offpeak_price_etb: 120,
    rating: 4.9,
    review_count: 85,
    is_verified: true,
    is_kuriftu_partner: true,
    avatar_url: "",
    license_body: "kuriftu",
  },
]

const SPECIALTIES = [
  { id: "", label: "All" },
  { id: "dietitian", label: "Dietitian" },
  { id: "nutritionist", label: "Nutritionist" },
  { id: "gastroenterologist", label: "Gastro" },
  { id: "wellness_coach", label: "Wellness" },
  { id: "yoga_instructor", label: "Yoga" },
]

const LICENSE_LABEL: Record<string, string> = {
  moh: "MOH Ethiopia",
  fmhaca: "FMHACA",
  kuriftu: "Kuriftu Partner",
  other: "Licensed",
}

const AVATAR_COLORS = [
  "bg-wellnet-100 text-wellnet-700",
  "bg-purple-100 text-purple-700",
  "bg-amber-100 text-amber-700",
  "bg-blue-100 text-blue-700",
]

export default function ExpertsPage() {
  const [experts, setExperts] =
    useState<Professional[]>([])

  const [loading, setLoading] =
    useState(true)

  const [specialty, setSpecialty] =
    useState("")

  const [kuriftu, setKuriftu] =
    useState(false)

  const [booking, setBooking] =
    useState<Professional | null>(null)

  const [confirming, setConfirming] =
    useState(false)

  useEffect(() => {
    load()
  }, [specialty, kuriftu])

  const load = async () => {
    setLoading(true)

    try {
      const params: any = {}

      if (specialty) {
        params.specialty = specialty
      }

      if (kuriftu) {
        params.is_kuriftu_partner = true
      }

      const r =
        await expertService.list(params)

      const arr =
        extractArray<Professional>(
          r.data
        )

      setExperts(
        arr.length > 0
          ? arr
          : DEMO.filter((d) => {
              if (
                specialty &&
                d.specialty !== specialty
              ) {
                return false
              }

              if (
                kuriftu &&
                !d.is_kuriftu_partner
              ) {
                return false
              }

              return true
            })
      )
    } catch {
      setExperts(DEMO)
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmBook =
    async () => {
      if (!booking) return

      setConfirming(true)

      try {
        const dt = new Date()

        dt.setDate(
          dt.getDate() + 1
        )

        dt.setHours(10, 0, 0, 0)

        await expertService.book(
          booking.id,
          {
            scheduled_at:
              dt.toISOString(),
            duration_minutes: 30,
            session_type:
              booking.session_types?.[0] ||
              "video",
          }
        )

        toast.success(
          `Session booked with ${booking.title} ${booking.display_name}!`
        )

        setBooking(null)
      } catch {
        toast.error(
          "Booking failed — please try again."
        )
      } finally {
        setConfirming(false)
      }
    }

  const initials = (name: string) =>
    name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase()

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">
          Wellness Experts
        </h1>

        <p className="text-sm text-gray-500 mt-0.5">
          Licensed Ethiopian health
          professionals — MOH &
          FMHACA verified
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {SPECIALTIES.map((s) => (
          <button
            key={s.id}
            onClick={() =>
              setSpecialty(s.id)
            }
            className={cn(
              "shrink-0 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all",
              specialty === s.id
                ? "bg-gray-900 text-white border-gray-900"
                : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
            )}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Kuriftu toggle */}
      <label className="flex items-center gap-2.5 cursor-pointer w-fit">
        <div
          onClick={() =>
            setKuriftu((p) => !p)
          }
          className={cn(
            "w-10 h-6 rounded-full relative transition-colors shrink-0",
            kuriftu
              ? "bg-wellnet-500"
              : "bg-gray-200"
          )}
        >
          <div
            className={cn(
              "absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all",
              kuriftu
                ? "left-5"
                : "left-1"
            )}
          />
        </div>

        <span className="text-sm text-gray-600">
          Kuriftu partners only
        </span>
      </label>

      {/* Loading */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-44 bg-gray-100 rounded-2xl animate-pulse"
            />
          ))}
        </div>
      ) : experts.length === 0 ? (
        <div className="card text-center py-8 text-sm text-gray-400">
          No professionals match.
        </div>
      ) : (
        <div className="space-y-3">
          {experts.map(
            (pro, idx) => (
              <div
                key={pro.id}
                className="card"
              >
                <div className="flex items-start gap-3">
                  {/* Avatar */}
                  <div
                    className={cn(
                      "w-12 h-12 rounded-2xl flex items-center justify-center text-sm font-bold shrink-0",
                      AVATAR_COLORS[
                        idx %
                          AVATAR_COLORS.length
                      ]
                    )}
                  >
                    {initials(
                      pro.display_name
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    {/* Top row */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-sm font-bold text-gray-900">
                            {pro.title}{" "}
                            {
                              pro.display_name
                            }
                          </span>

                          {pro.is_verified && (
                            <BadgeCheck className="w-4 h-4 text-wellnet-500 shrink-0" />
                          )}
                        </div>

                        <div className="text-xs text-gray-500 capitalize mt-0.5">
                          {pro.specialty.replace(
                            "_",
                            " "
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />

                        <span className="text-xs font-semibold text-gray-700">
                          {pro.rating}
                        </span>

                        <span className="text-xs text-gray-400">
                          (
                          {
                            pro.review_count
                          }
                          )
                        </span>
                      </div>
                    </div>

                    {/* Bio */}
                    <p className="text-xs text-gray-500 mt-1.5 leading-relaxed line-clamp-2">
                      {pro.bio}
                    </p>

                    {/* Badges */}
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      <span className="badge-teal">
                        <BadgeCheck className="w-2.5 h-2.5" />

                        {LICENSE_LABEL[
                          pro.license_body
                        ] || "Licensed"}
                      </span>

                      {pro.is_kuriftu_partner && (
                        <span className="badge-teal">
                          🏨 Kuriftu
                        </span>
                      )}

                      {pro.languages.map(
                        (l) => (
                          <span
                            key={l}
                            className="badge-amber"
                          >
                            <Globe className="w-2.5 h-2.5" />{" "}
                            {l}
                          </span>
                        )
                      )}

                      {pro.session_types.map(
                        (st) => (
                          <span
                            key={st}
                            className="badge-purple text-[10px]"
                          >
                            {st ===
                            "video"
                              ? "📹"
                              : st ===
                                "group"
                              ? "👥"
                              : "🤝"}{" "}
                            {st}
                          </span>
                        )
                      )}
                    </div>

                    {/* Bottom row */}
                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                      <div className="flex items-baseline gap-1.5 flex-wrap">
                        <span className="text-sm font-bold text-gray-900">
                          {Number(
                            pro.session_price_etb
                          ).toLocaleString()}{" "}
                          ETB
                        </span>

                        {pro.offpeak_price_etb && (
                          <span className="text-xs text-wellnet-600">
                            {Number(
                              pro.offpeak_price_etb
                            ).toLocaleString()}{" "}
                            ETB off-peak
                          </span>
                        )}

                        <span className="text-xs text-gray-400">
                          / 30 min
                        </span>
                      </div>

                      <button
                        onClick={() =>
                          setBooking(pro)
                        }
                        className="btn-primary flex items-center gap-1.5 px-3 py-2 text-xs"
                      >
                        <Calendar className="w-3.5 h-3.5" />
                        Book
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      )}

      {/* Booking modal */}
      {booking && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/30">
          <div className="bg-white rounded-3xl p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-0.5">
              Confirm booking
            </h3>

            <p className="text-sm text-gray-500 mb-4">
              30-min session with{" "}
              {booking.title}{" "}
              {booking.display_name}
            </p>

            <div className="bg-gray-50 rounded-2xl p-4 space-y-2 mb-4">
              {[
                [
                  "Session fee",
                  `${Number(
                    booking.session_price_etb
                  ).toLocaleString()} ETB`,
                ],
                [
                  "Platform fee (20%)",
                  `${Math.round(
                    Number(
                      booking.session_price_etb
                    ) * 0.2
                  ).toLocaleString()} ETB`,
                ],
              ].map(([k, v]) => (
                <div
                  key={k}
                  className="flex justify-between text-sm"
                >
                  <span className="text-gray-500">
                    {k}
                  </span>

                  <span className="font-medium">
                    {v}
                  </span>
                </div>
              ))}

              <div className="flex justify-between text-sm font-bold border-t border-gray-200 pt-2">
                <span>Total</span>

                <span className="text-wellnet-600">
                  {Number(
                    booking.session_price_etb
                  ).toLocaleString()}{" "}
                  ETB
                </span>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() =>
                  setBooking(null)
                }
                className="flex-1 btn-ghost"
              >
                Cancel
              </button>

              <button
                onClick={
                  handleConfirmBook
                }
                disabled={confirming}
                className="flex-1 btn-primary flex items-center justify-center gap-2"
              >
                {confirming ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Booking…
                  </>
                ) : (
                  "Confirm"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
