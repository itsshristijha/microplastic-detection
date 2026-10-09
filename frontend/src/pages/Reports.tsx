import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { FileText, Download, Calendar, MapPin, AlertCircle, Loader2, RefreshCw, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:5000").replace(/\/+$/, "");

interface AnalysisRecord {
  timestamp: string;
  original_filename: string;
  total_particles: number;
  breakdown: Record<string, number>;
  health_risk: {
    concentration_per_ml: number;
    status: string;
    risk_level: string;
    message: string;
  };
}

const MOCK_RECORDS: AnalysisRecord[] = [
  {
    timestamp: "2026-05-30T10:22:00Z",
    original_filename: "water_sample_01.jpg",
    total_particles: 340,
    breakdown: { Fragment: 180, Fiber: 100, Film: 60 },
    health_risk: { concentration_per_ml: 3.4, status: "Critical", risk_level: "High", message: "Sample contains 3.40 particles/mL." },
  },
  {
    timestamp: "2026-05-28T14:05:00Z",
    original_filename: "tap_water_june.png",
    total_particles: 185,
    breakdown: { Fragment: 90, Fiber: 70, Pellet: 25 },
    health_risk: { concentration_per_ml: 1.85, status: "Caution", risk_level: "Moderate", message: "Sample contains 1.85 particles/mL." },
  },
  {
    timestamp: "2026-05-22T08:45:00Z",
    original_filename: "filtered_sample.jpg",
    total_particles: 52,
    breakdown: { Fragment: 30, Fiber: 22 },
    health_risk: { concentration_per_ml: 0.52, status: "Safe", risk_level: "Low", message: "Sample contains 0.52 particles/mL." },
  },
];

const levelBadge: Record<string, string> = {
  safe: "text-status-safe bg-status-safe/10 border-status-safe/30",
  moderate: "text-status-moderate bg-status-moderate/10 border-status-moderate/30",
  caution: "text-status-moderate bg-status-moderate/10 border-status-moderate/30",
  danger: "text-status-danger bg-status-danger/10 border-status-danger/30",
  critical: "text-status-danger bg-status-danger/10 border-status-danger/30",
  high: "text-status-danger bg-status-danger/10 border-status-danger/30",
  low: "text-status-safe bg-status-safe/10 border-status-safe/30",
};

const getBadgeKey = (status: string) => status.toLowerCase();

const formatDate = (ts: string) => {
  const d = new Date(ts);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};
const formatTime = (ts: string) => {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
};

const downloadPDF = (record: AnalysisRecord, index: number) => {
  const breakdownRows = Object.entries(record.breakdown)
    .map(([name, count]) => `<tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;">${name}</td><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600;">${count}</td></tr>`)
    .join("");

  const statusColor =
    record.health_risk.status.toLowerCase() === "safe" ? "#22c55e"
    : record.health_risk.status.toLowerCase() === "caution" || record.health_risk.status.toLowerCase() === "moderate" ? "#eab308"
    : "#ef4444";

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <title>ELLE Analysis Report #${index + 1}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', Arial, sans-serif; color: #1f2937; padding: 40px; background: #fff; }
    .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #0d9488; padding-bottom: 20px; margin-bottom: 28px; }
    .brand { font-size: 28px; font-weight: 800; color: #0d9488; letter-spacing: -0.5px; }
    .subtitle { font-size: 12px; color: #6b7280; margin-top: 4px; }
    .meta { text-align: right; font-size: 12px; color: #6b7280; }
    .meta strong { display: block; font-size: 14px; color: #374151; }
    h2 { font-size: 16px; font-weight: 700; margin-bottom: 12px; color: #111827; }
    .badge { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; background: ${statusColor}22; color: ${statusColor}; border: 1px solid ${statusColor}44; }
    .grid { dino splay: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
    .card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; }
    .card .label { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .card .value { font-size: 22px; font-weight: 800; color: #111827; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    thead tr { background: #f3f4f6; }
    thead td { font-weight: 600; padding: 10px 12px; font-size: 12px; color: #6b7280; text-transform: uppercase; }
    .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #9ca3af; text-align: center; }
    .note { background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #92400e; margin-bottom: 24px; }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">ELLE</div>
      <div class="subtitle">Microplastic Detection System</div>
    </div>
    <div class="meta">
      <strong>Sample Report #${index + 1}</strong>
      Generated on ${new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" })}
    </div>
  </div>

  <div style="margin-bottom:24px;">
    <h2>Analysis Summary &nbsp; <span class="badge">${record.health_risk.status}</span></h2>
    <p style="font-size:13px;color:#6b7280;margin-top:6px;">File: <strong style="color:#374151;">${record.original_filename}</strong> &nbsp;|&nbsp; Date: ${formatDate(record.timestamp)}, ${formatTime(record.timestamp)}</p>
  </div>

  <div class="grid">
    <div class="card">
      <div class="label">Total Particles Detected</div>
      <div class="value">${record.total_particles}</div>
    </div>
    <div class="card">
      <div class="label">Concentration</div>
      <div class="value">${record.health_risk.concentration_per_ml.toFixed(2)} <span style="font-size:14px;font-weight:400;color:#6b7280;">p/mL</span></div>
    </div>
    <div class="card">
      <div class="label">Risk Level</div>
      <div class="value" style="color:${statusColor};">${record.health_risk.risk_level}</div>
    </div>
    <div class="card">
      <div class="label">Status</div>
      <div class="value" style="color:${statusColor};">${record.health_risk.status}</div>
    </div>
  </div>

  <div class="note">⚠️ ${record.health_risk.message}</div>

  <h2>Breakdown by Plastic Type</h2>
  <table style="margin-bottom:24px;">
    <thead><tr><td>Type</td><td style="text-align:right;">Particle Count</td></tr></thead>
    <tbody>${breakdownRows}</tbody>
  </table>

  <div class="footer">
    ELLE — Environmental Microplastic Detection System &nbsp;|&nbsp; EPICS Project &nbsp;|&nbsp; Confidential Research Report
  </div>
</body>
</html>`;

  const printWindow = window.open("", "_blank", "width=900,height=700");
  if (!printWindow) return;
  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
    printWindow.close();
  }, 600);
};

const Reports = () => {
  const [records, setRecords] = useState<AnalysisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(`${API_BASE}/api/reports`, { signal: controller.signal });
      clearTimeout(timeout);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setRecords(data.reports || []);
      setIsDemo(false);
    } catch {
      setRecords(MOCK_RECORDS);
      setIsDemo(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchReports(); }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="container pt-24 pb-12 max-w-4xl">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-start justify-between mb-1">
            <div>
              <h1 className="text-3xl font-bold">Reports</h1>
              <p className="text-muted-foreground mt-1">Download PDF reports for every analysis run</p>
            </div>
            <Button variant="outline" size="sm" className="gap-2 mt-1" onClick={fetchReports} disabled={loading}>
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Refresh
            </Button>
          </div>
          {isDemo && (
            <div className="flex items-center gap-2 text-xs text-status-moderate bg-status-moderate/10 border border-status-moderate/30 px-3 py-2 rounded-lg mt-4 mb-2">
              <Database className="w-3.5 h-3.5" />
              Demo Mode — showing sample reports. Connect MongoDB to see real data.
            </div>
          )}
        </motion.div>

        <div className="space-y-3 mt-6">
          {loading ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-10 h-10 text-primary animate-spin" />
            </div>
          ) : records.length === 0 ? (
            <div className="glass rounded-xl p-10 text-center text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
              No reports yet. Upload a water sample to generate your first report.
            </div>
          ) : (
            records.map((r, i) => {
              const badgeKey = getBadgeKey(r.health_risk.status);
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="glass rounded-xl p-5 flex flex-col sm:flex-row sm:items-center gap-4"
                >
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-primary" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{r.original_filename || `Sample Report #${i + 1}`}</div>
                    <div className="flex flex-wrap gap-3 mt-1 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{formatDate(r.timestamp)} at {formatTime(r.timestamp)}</span>
                      <span className="flex items-center gap-1"><AlertCircle className="w-3 h-3" />{r.total_particles} particles — {r.health_risk.concentration_per_ml.toFixed(2)} p/mL</span>
                    </div>
                  </div>

                  <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${levelBadge[badgeKey] || "text-muted-foreground bg-muted"}`}>
                    {r.health_risk.status}
                  </span>

                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5 shrink-0 hover:bg-primary hover:text-primary-foreground transition-colors"
                    onClick={() => downloadPDF(r, i)}
                  >
                    <Download className="w-3.5 h-3.5" /> PDF
                  </Button>
                </motion.div>
              );
            })
          )}
        </div>

        {records.length > 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="mt-6 glass rounded-xl p-4 flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{records.length} report{records.length !== 1 ? "s" : ""} found</span>
            <Button
              size="sm"
              className="gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
              onClick={() => records.forEach((r, i) => setTimeout(() => downloadPDF(r, i), i * 800))}
            >
              <Download className="w-4 h-4" /> Download All PDFs
            </Button>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default Reports;
