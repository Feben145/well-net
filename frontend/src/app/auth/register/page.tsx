"use client"
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Leaf, Eye, EyeOff, Loader2, ChevronRight, ChevronLeft } from "lucide-react"
import { authService } from "@/services/wellnet"
import { useAuthStore } from "@/store"
import { cn } from "@/lib/utils"

const GOALS = [
  { id:"gut_health",     label:"Gut health",   emoji:"🌿" },
  { id:"energy",         label:"Boost energy", emoji:"⚡" },
  { id:"weight_balance", label:"Weight",       emoji:"⚖️" },
  { id:"stress",         label:"Stress",       emoji:"🧘" },
  { id:"immunity",       label:"Immunity",     emoji:"🛡️" },
  { id:"mindfulness",    label:"Mindfulness",  emoji:"🌙" },
  { id:"sleep",          label:"Sleep",        emoji:"😴" },
  { id:"general",        label:"General",      emoji:"🌟" },
]

const DIETS = [
  { id:"omnivore",   label:"Omnivore" },
  { id:"fasting",    label:"Ethiopian fasting" },
  { id:"vegetarian", label:"Vegetarian" },
  { id:"vegan",      label:"Vegan" },
  { id:"diabetic",   label:"Diabetic-friendly" },
]

const schema = z.object({
  email:     z.string().email("Enter a valid email"),
  username:  z.string().min(3, "Min 3 characters"),
  password:  z.string().min(8, "Min 8 characters"),
  password2: z.string(),
}).refine(d => d.password === d.password2, { message:"Passwords don't match", path:["password2"] })
type Form = z.infer<typeof schema>

export default function RegisterPage() {
  const router = useRouter()
  const { setUser, setProfile } = useAuthStore()
  const [step,       setStep]       = useState(0)
  const [showPw,     setShowPw]     = useState(false)
  const [loading,    setLoading]    = useState(false)
  const [goal,       setGoal]       = useState("gut_health")
  const [diet,       setDiet]       = useState("omnivore")
  const [fasting,    setFasting]    = useState(false)
  const [pregnant,   setPregnant]   = useState(false)
  const [diabetes,   setDiabetes]   = useState(false)

  const { register, handleSubmit, trigger, formState:{ errors } } = useForm<Form>({
    resolver: zodResolver(schema)
  })

  const next = async () => {
    if (step === 0) {
      const ok = await trigger(["email","username","password","password2"])
      if (!ok) return
    }
    setStep(s => Math.min(s+1, 2))
  }

  const onSubmit = async (data: Form) => {
    setLoading(true)
    try {
      await authService.register({
        email: data.email, username: data.username,
        password: data.password, password2: data.password2,
      })
      await authService.login(data.email, data.password)

      // Update profile — only fields that exist on UserProfile
      try {
        await authService.updateProfile({
          primary_goal:      goal as any,
          diet_type:         diet as any,
          is_fasting_season: fasting,
          is_pregnant:       pregnant,
          has_diabetes:      diabetes,
          display_name:      data.username,
        })
      } catch {
        // profile update is non-fatal — user can set later
      }

      const [meRes, profileRes] = await Promise.all([
        authService.getMe(),
        authService.getProfile(),
      ])
      setUser(meRes.data)
      setProfile(profileRes.data)
      toast.success("Welcome to Well-Net! 🌿")
      router.push("/dashboard")
    } catch (err: any) {
      const msg =
        err?.response?.data?.email?.[0] ||
        err?.response?.data?.username?.[0] ||
        err?.response?.data?.password?.[0] ||
        "Registration failed. Please try again."
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const Toggle = ({ label, value, onChange }: { label:string; value:boolean; onChange:(v:boolean)=>void }) => (
    <label className="flex items-center gap-3 cursor-pointer">
      <div onClick={() => onChange(!value)}
        className={cn("w-10 h-6 rounded-full relative transition-colors shrink-0",
          value ? "bg-wellnet-500" : "bg-gray-200")}>
        <div className={cn("absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-all",
          value ? "left-5" : "left-1")} />
      </div>
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-wellnet-50 via-white to-amber-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center gap-2 mb-8">
          <div className="w-9 h-9 rounded-xl bg-wellnet-500 flex items-center justify-center">
            <Leaf className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg text-gray-900">Well-Net</span>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6">
          {["Account","Your goal","Profile"].map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={cn(
                "w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center transition-all",
                i <= step ? "bg-wellnet-500 text-white" : "bg-gray-200 text-gray-400"
              )}>
                {i < step ? "✓" : i+1}
              </div>
              <span className={cn("text-xs font-medium", i===step?"text-gray-900":"text-gray-400")}>{label}</span>
              {i < 2 && <div className={cn("h-px w-4", i<step?"bg-wellnet-400":"bg-gray-200")} />}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Step 0 */}
          {step === 0 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Create your account</h2>
                <p className="text-sm text-gray-500 mt-0.5">Free forever — upgrade anytime</p>
              </div>
              {[
                { name:"email"    as const, label:"Email",    type:"email",    placeholder:"you@example.com" },
                { name:"username" as const, label:"Username", type:"text",     placeholder:"abebe" },
              ].map(f => (
                <div key={f.name}>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">{f.label}</label>
                  <input {...register(f.name)} type={f.type} placeholder={f.placeholder}
                    className={cn("input", errors[f.name] && "border-red-400")} />
                  {errors[f.name] && <p className="text-red-500 text-xs mt-1">{errors[f.name]?.message}</p>}
                </div>
              ))}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
                <div className="relative">
                  <input {...register("password")} type={showPw?"text":"password"} placeholder="Min 8 characters"
                    className={cn("input pr-10", errors.password && "border-red-400")} />
                  <button type="button" onClick={() => setShowPw(p=>!p)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Confirm password</label>
                <input {...register("password2")} type="password" placeholder="••••••••"
                  className={cn("input", errors.password2 && "border-red-400")} />
                {errors.password2 && <p className="text-red-500 text-xs mt-1">{errors.password2.message}</p>}
              </div>
            </div>
          )}

          {/* Step 1 */}
          {step === 1 && (
            <div>
              <div className="mb-5">
                <h2 className="text-xl font-bold text-gray-900">What's your main goal?</h2>
                <p className="text-sm text-gray-500 mt-0.5">Personalises your scores and tips</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {GOALS.map(g => (
                  <button key={g.id} type="button" onClick={() => setGoal(g.id)}
                    className={cn(
                      "flex items-center gap-2 p-3 rounded-xl border text-left transition-all",
                      goal === g.id
                        ? "bg-wellnet-500 border-wellnet-500 text-white"
                        : "bg-white border-gray-200 text-gray-700 hover:border-wellnet-300"
                    )}>
                    <span className="text-xl">{g.emoji}</span>
                    <span className="text-xs font-medium leading-tight">{g.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2 */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-gray-900">A little about you</h2>
                <p className="text-sm text-gray-500 mt-0.5">Tailors your wellness scores</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Diet type</label>
                <div className="flex flex-wrap gap-2">
                  {DIETS.map(d => (
                    <button key={d.id} type="button" onClick={() => setDiet(d.id)}
                      className={cn(
                        "px-3 py-1.5 rounded-xl border text-xs font-medium transition-all",
                        diet === d.id
                          ? "bg-wellnet-500 border-wellnet-500 text-white"
                          : "bg-white border-gray-200 text-gray-600"
                      )}>
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-700">Health flags</label>
                <Toggle label="Currently fasting (Ethiopian Orthodox)" value={fasting} onChange={setFasting} />
                <Toggle label="Pregnant" value={pregnant} onChange={setPregnant} />
                <Toggle label="Managing diabetes" value={diabetes} onChange={setDiabetes} />
              </div>
            </div>
          )}

          {/* Nav buttons */}
          <div className={cn("flex mt-6 gap-3", step === 0 && "justify-end")}>
            {step > 0 && (
              <button type="button" onClick={() => setStep(s=>s-1)}
                className="btn-ghost flex items-center gap-1">
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
            )}
            {step < 2 ? (
              <button type="button" onClick={next}
                className="flex-1 btn-primary py-3 flex items-center justify-center gap-1">
                Continue <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button type="submit" disabled={loading}
                className="flex-1 btn-primary py-3 flex items-center justify-center gap-2">
                {loading
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating account…</>
                  : "Start my wellness journey 🌿"
                }
              </button>
            )}
          </div>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Already have an account?{" "}
          <Link href="/auth/login" className="text-wellnet-600 font-medium hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
