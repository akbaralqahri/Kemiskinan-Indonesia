import type { Metadata } from "next";
import { headers } from "next/headers";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3001";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const base = new URL(`${protocol}://${host}`);
  const image = new URL("/og.png", base).toString();
  return {
    metadataBase: base,
    title: "Peta Kemiskinan Indonesia | Data 2015–2025 & Forecast 2026",
    description: "Dashboard interaktif kemiskinan Indonesia: tren, peringkat provinsi, faktor terkait, benchmark model, dan forecast 2026 berbasis data BPS.",
    openGraph: { title: "Peta Kemiskinan Indonesia", description: "Data 2015–2025 · Forecast 2026 eksperimental", images: [{ url: image, width: 1536, height: 1024, alt: "Peta Kemiskinan Indonesia" }] },
    twitter: { card: "summary_large_image", title: "Peta Kemiskinan Indonesia", description: "Data 2015–2025 · Forecast 2026 eksperimental", images: [image] },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="id"><body className={`${geistSans.variable} ${geistMono.variable}`}>{children}</body></html>;
}
