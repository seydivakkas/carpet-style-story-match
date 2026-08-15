import "./globals.css";
import type { Metadata } from "next";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Carpet Style & Story Match",
  description: "Halıların görsel karakterini, estetik tercihlerini ve belgelenmiş hikâyelerini bir araya getir.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-amber-500/30">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
