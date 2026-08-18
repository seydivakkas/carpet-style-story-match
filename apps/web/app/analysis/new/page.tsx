"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { uploadCarpetForAnalysis } from "@/lib/result-experience-api";
import { Upload, Sparkles, AlertCircle, Loader2, ArrowLeft } from "lucide-react";

export default function NewUploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Lütfen analiz etmek için bir halı görseli seçin.");
      return;
    }

    try {
      setUploading(true);
      setError(null);
      const res = await uploadCarpetForAnalysis(file);
      router.push(`/analysis/${res.analysis_id}`);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Yükleme sırasında beklenmeyen bir hata oluştu.");
      }
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans">
      <Header />

      <main className="max-w-4xl mx-auto w-full px-6 py-12 flex-1 space-y-8">
        <div className="flex items-center space-x-3">
          <Link
            href="/"
            className="p-2 bg-slate-900 hover:bg-slate-800 rounded-xl border border-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              Yüklenen Halı Görsel Analizi
            </h1>
            <p className="text-slate-400 text-sm">
              Halı fotoğrafınızı yükleyin; 9D Style DNA, motif adayları ve müze koleksiyonlarındaki tarihsel bağlantıları 5 kartlı raporda görün.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="bg-slate-900/80 border border-slate-800 rounded-3xl p-8 space-y-6 shadow-2xl">
          {/* File Upload Dropzone */}
          <div className="border-2 border-dashed border-slate-700 hover:border-amber-500/60 rounded-2xl p-8 text-center space-y-4 transition-colors cursor-pointer relative bg-slate-950/60">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileChange}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            />

            {previewUrl ? (
              <div className="space-y-4 flex flex-col items-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={previewUrl}
                  alt="Yüklenen Halı Önizleme"
                  className="max-h-64 rounded-xl border border-slate-700 object-contain shadow-lg"
                />
                <span className="text-xs font-mono text-amber-300 font-bold">
                  {file?.name} ({file ? (file.size / (1024 * 1024)).toFixed(2) : 0} MB)
                </span>
              </div>
            ) : (
              <div className="space-y-3 flex flex-col items-center">
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-amber-400">
                  <Upload className="w-8 h-8" />
                </div>
                <div>
                  <span className="text-base font-bold text-white block">
                    Fotoğraf Seçin veya Sürükleyip Bırakın
                  </span>
                  <span className="text-xs text-slate-400 block mt-1">
                    JPEG, PNG veya WEBP (Maksimum 10MB)
                  </span>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 flex items-center space-x-3 text-xs text-rose-300">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={!file || uploading}
            className="w-full py-4 bg-amber-500 hover:bg-amber-400 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 font-bold text-base rounded-2xl transition-all shadow-xl shadow-amber-500/10 flex items-center justify-center space-x-2"
          >
            {uploading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin text-slate-950" />
                <span>Analiz ve Eşleşme Hesaplanıyor...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                <span>5 Kartlı Analiz Raporunu Oluştur</span>
              </>
            )}
          </button>
        </form>
      </main>

      <Footer />
    </div>
  );
}
