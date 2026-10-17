import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Human Cache — Adaptive Cognitive OS",
  description: "Proactive, multi-domain educational knowledge vault with Ebbinghaus retention tracking.",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased font-sans">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
