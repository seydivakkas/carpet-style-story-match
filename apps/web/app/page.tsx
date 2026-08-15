import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { Sparkles, Layers, BookOpen, Compass, ArrowRight, ShieldCheck } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />

      <main className="max-w-6xl mx-auto w-full px-6 py-12 flex-1 space-y-16">
        {/* Hero Section */}
        <section className="text-center space-y-6 max-w-3xl mx-auto pt-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-full text-xs font-mono text-amber-400">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Açıklanabilir Halı Stil &amp; Anlatı Eşleşme Platformu v1</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Halı Estetiği, Motif Anlatısı &amp; Müze Geçmişi
          </h1>

          <p className="text-slate-400 text-base sm:text-lg leading-relaxed">
            Kişisel görsel tercihlerinizi 9 boyutlu Style DNA ile çıkarın; belgelenmiş kültürel motif hikâyeleri ve müze koleksiyonlarındaki doğrulanmış dokumalarla üç ayrı eksende açık ve dürüstçe karşılaştırın.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link
              href="/assessment/new"
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-3 px-8 py-4 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-base rounded-2xl transition-all shadow-xl shadow-amber-500/20 hover:scale-[1.02]"
            >
              <span>Estetik Profilinizi Oluşturun</span>
              <ArrowRight className="w-5 h-5" />
            </Link>

            <Link
              href="/catalog"
              className="w-full sm:w-auto inline-flex items-center justify-center space-x-3 px-8 py-4 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-semibold text-base rounded-2xl transition-all"
            >
              <BookOpen className="w-5 h-5 text-amber-400" />
              <span>Halı Kataloğunu İnceleyin</span>
            </Link>
          </div>
        </section>

        {/* Three Independent Axes Overview */}
        <section className="space-y-6">
          <div className="text-center space-y-2 max-w-2xl mx-auto">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Üç Bağımsız Ürün Değerlendirme Ekseni
            </h2>
            <p className="text-slate-400 text-xs sm:text-sm">
              Sistemimiz asla tek bir yapay &quot;uyum yüzdesi&quot; üretmez. Her ürün üç ayrı bilimsel eksende açıklanır.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Axis 1 Card */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 space-y-4 hover:border-slate-700 transition-colors flex flex-col justify-between">
              <div className="space-y-3">
                <div className="p-3 bg-amber-500/10 text-amber-400 rounded-xl w-max">
                  <Layers className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-mono text-amber-400 font-bold uppercase tracking-wider">Eksen 1</span>
                <h3 className="text-lg font-bold text-slate-100">Görsel Stil Uyumu</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Renk, kontrast, görsel karmaşıklık, ritim, form dili gibi 9 matematiksel Style DNA boyutuyla kişisel estetik eşleşmeniz.
                </p>
              </div>
              <div className="pt-3 border-t border-slate-800/60 text-xs font-mono text-amber-400">
                Açıklanabilir 9D Vektör Mesafesi
              </div>
            </div>

            {/* Axis 2 Card */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 space-y-4 hover:border-slate-700 transition-colors flex flex-col justify-between">
              <div className="space-y-3">
                <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl w-max">
                  <BookOpen className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-mono text-emerald-400 font-bold uppercase tracking-wider">Eksen 2</span>
                <h3 className="text-lg font-bold text-slate-100">Anlatı Yakınlığı</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Seçtiğiniz 8 kültürel motif temasının (Doğa, Yuva, Zanaat vb.) halının belgelenmiş iddialarıyla kategorik uyumu.
                </p>
              </div>
              <div className="pt-3 border-t border-slate-800/60 text-xs font-mono text-emerald-400">
                Kategorik Seviye &amp; Tartışma Bildirimi
              </div>
            </div>

            {/* Axis 3 Card */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 space-y-4 hover:border-slate-700 transition-colors flex flex-col justify-between">
              <div className="space-y-3">
                <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl w-max">
                  <Compass className="w-6 h-6" />
                </div>
                <span className="text-[10px] font-mono text-blue-400 font-bold uppercase tracking-wider">Eksen 3</span>
                <h3 className="text-lg font-bold text-slate-100">Tarihsel Referans Bağlantısı</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Met, V&amp;A, TİEM müzelerinde sergilenen doğrulanmış tarihi dokumalarla Style DNA boyut boyut yakınlık karşılaştırması.
                </p>
              </div>
              <div className="pt-3 border-t border-slate-800/60 text-xs font-mono text-blue-400">
                Müze Envanteri Style DNA Bağlantısı
              </div>
            </div>
          </div>
        </section>

        {/* System Principles */}
        <section className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-8 space-y-6">
          <div className="flex items-center space-x-3">
            <ShieldCheck className="w-6 h-6 text-amber-400" />
            <h2 className="text-xl font-bold text-white">Sistem ve Veri İlkelerimiz</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs text-slate-300">
            <div className="space-y-1">
              <span className="font-bold text-slate-100 block">Dürüst Veri</span>
              <p className="text-slate-400">Sahte frontend verisi veya uydurma skorlar kullanılmaz.</p>
            </div>
            <div className="space-y-1">
              <span className="font-bold text-slate-100 block">Açıklanabilirlik</span>
              <p className="text-slate-400">Her skorun hangi 9D alt boyutundan kaynaklandığı açıktır.</p>
            </div>
            <div className="space-y-1">
              <span className="font-bold text-slate-100 block">Kişilik Dili Yok</span>
              <p className="text-slate-400">&quot;Kişilik analizi&quot; değil, &quot;görsel estetik tercih&quot; tanımı yapılır.</p>
            </div>
            <div className="space-y-1">
              <span className="font-bold text-slate-100 block">Sorumluluk Reddi</span>
              <p className="text-slate-400">Tarihsel yakınlık halının orijinalliğini veya atölyesini kanıtlamaz.</p>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
