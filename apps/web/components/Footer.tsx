export default function Footer() {
  return (
    <footer className="mt-16 border-t border-slate-800/80 bg-slate-950 py-8 px-6 text-xs text-slate-500">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="space-y-1 text-center sm:text-left">
          <p className="text-slate-400 font-medium">
            ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
          </p>
          <p>© 2026 Seydi Eryılmaz (@seydivakkas). Tüm Hakları Saklıdır.</p>
        </div>
        <div className="flex items-center space-x-4 font-mono text-[11px] text-slate-600">
          <span>Three Independent Axes</span>
          <span>•</span>
          <span>Truthful Museum Provenance</span>
          <span>•</span>
          <span>Next.js 15</span>
        </div>
      </div>
    </footer>
  );
}
