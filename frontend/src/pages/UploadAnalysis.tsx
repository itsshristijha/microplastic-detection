import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Image, Loader2, CheckCircle, AlertCircle, Heart, Droplets } from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import { useAnalysis } from "@/contexts/AnalysisContext";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:5000").replace(/\/+$/, "");

type FrontendLevel = "safe" | "moderate" | "danger";

const mapStatusToLevel = (status: string): FrontendLevel => {
  const s = status.toLowerCase();
  if (s === "safe") return "safe";
  if (s === "caution" || s === "moderate") return "moderate";
  return "danger";
};

const levelLabels: Record<FrontendLevel, string> = { safe: "Safe", moderate: "Moderate", danger: "Danger" };
const levelColors: Record<FrontendLevel, string> = {
  safe: "text-status-safe bg-status-safe/10 border-status-safe/30",
  moderate: "text-status-moderate bg-status-moderate/10 border-status-moderate/30",
  danger: "text-status-danger bg-status-danger/10 border-status-danger/30",
};

const UploadAnalysis = () => {
  const {
    file, setFile,
    preview, setPreview,
    analyzing, setAnalyzing,
    result, setResult,
    error, setError
  } = useAnalysis();

  const [dragActive, setDragActive] = useState(false);

  const handleFile = useCallback((f: File) => {
    if (f.size > 10 * 1024 * 1024) return;
    if (!["image/jpeg", "image/png"].includes(f.type)) return;
    setFile(f);
    setResult(null);
    setError(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(f);
  }, [setFile, setResult, setError, setPreview]);

  const analyze = async () => {
    if (!file) return;
    setAnalyzing(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("image", file);

      const response = await fetch(`${API_BASE}/api/predict`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.error || `Server error (${response.status})`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "Analysis failed");
      }

      setResult(data);
    } catch (err: any) {
      console.error("Analysis error:", err);
      if (err.message?.includes("Failed to fetch") || err.message?.includes("NetworkError")) {
        setError("Cannot connect to the ML server. Make sure the Flask backend is running on port 5000.");
      } else {
        setError(err.message || "An unexpected error occurred.");
      }
    } finally {
      setAnalyzing(false);
    }
  };

  const level: FrontendLevel = result ? mapStatusToLevel(result.health_risk.status) : "safe";
  const breakdownEntries = result ? Object.entries(result.analysis.breakdown) : [];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="container pt-24 pb-12 max-w-5xl">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold mb-1">Water Sample Analysis</h1>
          <p className="text-muted-foreground mb-8">Upload a microscope image for AI-powered microplastic detection</p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Upload area */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => { e.preventDefault(); setDragActive(false); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); }}
              className={`glass rounded-xl p-8 text-center cursor-pointer transition-all min-h-[300px] flex flex-col items-center justify-center ${
                dragActive ? "glow-border" : "hover:border-primary/30"
              }`}
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <input id="file-input" type="file" accept="image/jpeg,image/png" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />

              {preview ? (
                <div className="space-y-4 w-full">
                  <img src={preview} alt="Sample" className="w-full rounded-lg object-cover max-h-48" />
                  <p className="text-sm text-muted-foreground">{file?.name}</p>
                  <Button
                    onClick={(e) => { e.stopPropagation(); analyze(); }}
                    disabled={analyzing}
                    className="bg-primary text-primary-foreground hover:bg-primary/90 w-full"
                  >
                    {analyzing ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Analyzing...</> : "Run AI Analysis"}
                  </Button>
                </div>
              ) : (
                <>
                  <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                    <Upload className="w-8 h-8 text-primary" />
                  </div>
                  <p className="font-medium mb-1">Drop your water sample image here</p>
                  <p className="text-sm text-muted-foreground">JPG or PNG, up to 10MB</p>
                </>
              )}
            </div>
          </motion.div>

          {/* Results */}
          <AnimatePresence mode="wait">
            {analyzing && (
              <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="glass rounded-xl p-8 flex flex-col items-center justify-center min-h-[300px]">
                <Loader2 className="w-12 h-12 text-primary animate-spin mb-4" />
                <p className="font-medium">Processing with YOLOv8...</p>
                <p className="text-sm text-muted-foreground mt-1">Detecting microplastic particles</p>
              </motion.div>
            )}

            {!analyzing && error && (
              <motion.div key="error" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} className="glass rounded-xl p-6 flex flex-col items-center justify-center min-h-[300px] border border-status-danger/30">
                <AlertCircle className="w-12 h-12 text-status-danger mb-4" />
                <p className="font-medium text-status-danger mb-2">Analysis Failed</p>
                <p className="text-sm text-muted-foreground text-center">{error}</p>
              </motion.div>
            )}

            {!analyzing && !error && result && (
              <motion.div key="result" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="glass rounded-xl p-6 space-y-5">
                {/* Header */}
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-5 h-5 text-primary" />
                  <h3 className="font-semibold">Analysis Complete</h3>
                </div>

                {/* Annotated Image from Backend */}
                {result.image_url && (
                  <div className="rounded-lg overflow-hidden border border-border/50">
                    <img src={result.image_url} alt="Annotated result" className="w-full object-contain max-h-52" />
                  </div>
                )}

                {/* Particle Count & Status */}
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <div className="text-4xl font-black text-gradient">{result.analysis.total_particles}</div>
                    <div className="text-xs text-muted-foreground">particles detected</div>
                  </div>
                  <div className={`px-4 py-2 rounded-lg border text-sm font-medium ${levelColors[level]}`}>
                    <AlertCircle className="w-4 h-4 inline mr-1" />
                    {levelLabels[level]}
                  </div>
                </div>

                {/* Breakdown by Class */}
                {breakdownEntries.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                      <Droplets className="w-3.5 h-3.5" /> Detected Types
                    </h4>
                    {breakdownEntries.map(([name, count]) => (
                      <div key={name} className="flex items-center gap-3 bg-secondary/50 rounded-lg p-3">
                        <span className="text-sm font-medium w-24 capitalize">{name}</span>
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${(count / result.analysis.total_particles) * 100}%` }} />
                        </div>
                        <span className="text-xs font-mono text-primary w-8 text-right">{count}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Health Risk Panel */}
                <div className="space-y-3 pt-2 border-t border-border/50">
                  <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                    <Heart className="w-3.5 h-3.5" /> Health Risk Assessment
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-secondary/30 rounded-lg p-3">
                      <div className="text-xs text-muted-foreground mb-1">Concentration</div>
                      <div className="text-lg font-bold">{result.health_risk.concentration_per_ml.toFixed(2)} <span className="text-xs text-muted-foreground font-normal">p/mL</span></div>
                    </div>
                    <div className="bg-secondary/30 rounded-lg p-3">
                      <div className="text-xs text-muted-foreground mb-1">Risk Level</div>
                      <div className={`text-lg font-bold ${level === "safe" ? "text-status-safe" : level === "moderate" ? "text-status-moderate" : "text-status-danger"}`}>
                        {result.health_risk.risk_level}
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground italic">{result.health_risk.message}</p>
                </div>
              </motion.div>
            )}

            {!analyzing && !error && !result && (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass rounded-xl p-8 flex flex-col items-center justify-center min-h-[300px]">
                <Image className="w-12 h-12 text-muted-foreground/30 mb-4" />
                <p className="text-muted-foreground text-sm">Upload a sample to see analysis results</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default UploadAnalysis;
