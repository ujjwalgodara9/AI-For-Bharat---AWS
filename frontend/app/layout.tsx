import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MandiMitra — किसान का साथी | Mandi Price Intelligence",
  description:
    "AI-powered mandi price intelligence for Indian farmers. Real-time prices, sell advisories, and negotiation support in Hindi.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#2d6a4f",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="hi">
      <body className="antialiased">{children}</body>
    </html>
  );
}
