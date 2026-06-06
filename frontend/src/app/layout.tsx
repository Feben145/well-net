// src/app/layout.tsx

import type { Metadata } from "next"
import { Toaster } from "sonner"
// @ts-ignore: side-effect import of global CSS
import "./globals.css"

export const metadata: Metadata = {
  title: "Well-Net — Ethiopian Wellness Ecosystem",
  description:
    "AI-powered personalised wellness platform rooted in Ethiopian culture",
  icons: {
    icon: "/favicon.ico",
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        {children}

        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#E1F5EE",
              color: "#085041",
              border: "1px solid #5DCAA5",
            },
          }}
        />
      </body>
    </html>
  )
}