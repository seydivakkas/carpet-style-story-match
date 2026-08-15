"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Sparkles, Layers, BookOpen, Compass, ShieldCheck, Activity } from "lucide-react";

interface HeaderProps {
  assessmentId?: string | null;
}

export default function Header({ assessmentId }: HeaderProps) {
  const pathname = usePathname();

  const isNavActive = (path: string) => {
    if (path === "/" && pathname === "/") return true;
    if (path !== "/" && pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-8 py-4">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Brand */}
        <Link href="/" className="flex items-center space-x-3 group">
          <div className="p-2 bg-amber-500/10 border border-amber-500/30 rounded-xl group-hover:border-amber-500/60 transition-colors">
            <Sparkles className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-white group-hover:text-amber-300 transition-colors">
              Carpet Style & Story Match
            </span>
            <span className="block text-[10px] font-mono text-slate-400 tracking-wider">
              frontend-experience-v1
            </span>
          </div>
        </Link>

        {/* Navigation links */}
        <nav className="flex items-center space-x-1 sm:space-x-2 text-xs sm:text-sm font-medium">
          <Link
            href="/"
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              isNavActive("/") && pathname === "/"
                ? "bg-slate-800 text-white font-semibold"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            Ana Sayfa
          </Link>

          <Link
            href={assessmentId ? `/assessment/${assessmentId}/profile` : "/assessment/new"}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center space-x-1.5 ${
              pathname.startsWith("/assessment")
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Estetik Değerlendirme</span>
          </Link>

          <Link
            href={assessmentId ? `/catalog?assessment=${assessmentId}` : "/catalog"}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center space-x-1.5 ${
              pathname.startsWith("/catalog")
                ? "bg-slate-800 text-white font-semibold"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Katalog</span>
          </Link>

          <Link
            href={assessmentId ? `/historical-references?assessment=${assessmentId}` : "/historical-references"}
            className={`px-3 py-1.5 rounded-lg transition-colors flex items-center space-x-1.5 ${
              pathname.startsWith("/historical")
                ? "bg-slate-800 text-white font-semibold"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Tarihsel Referanslar</span>
          </Link>
        </nav>

        {/* Assessment Status Badge if active */}
        {assessmentId && (
          <div className="hidden lg:flex items-center space-x-2 text-[11px] font-mono bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-full text-slate-400">
            <Activity className="w-3 h-3 text-amber-400 animate-pulse" />
            <span>Aktif Değerlendirme:</span>
            <span className="text-amber-300">{assessmentId.slice(0, 8)}...</span>
          </div>
        )}
      </div>
    </header>
  );
}
