import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "AlphaLab",
  description: "AI-powered Financial Intelligence Platform",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
          background: "#0d0d0d",
          color: "#ffffff",
          minHeight: "100vh",
        }}
      >
        {children}
      </body>
    </html>
  );
}
