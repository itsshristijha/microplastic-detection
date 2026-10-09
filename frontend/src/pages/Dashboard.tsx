import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Droplets, AlertTriangle, TrendingUp, Activity, Loader2, WifiOff } from "lucide-react";
import { PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, LineChart, Line } from "recharts";
import Navbar from "@/components/Navbar";
import MetricCard from "@/components/MetricCard";

const iotData = [
  { time: "00:00", ph: 7.2, turbidity: 12, temp: 22 },
  { time: "04:00", ph: 7.1, turbidity: 14, temp: 21 },
  { time: "08:00", ph: 7.3, turbidity: 11, temp: 23 },
  { time: "12:00", ph: 7.0, turbidity: 16, temp: 25 },
  { time: "16:00", ph: 6.9, turbidity: 18, temp: 24 },
  { time: "20:00", ph: 7.1, turbidity: 15, temp: 22 },
];

const DEMO_STATS = {
  metrics: { avg_particles_per_liter: 142, avg_contamination: "Moderate", total_samples: 12 },
  trendData: [
    { date: "2026-05-01", count: 95 },
    { date: "2026-05-08", count: 120 },
    { date: "2026-05-15", count: 88 },
    { date: "2026-05-22", count: 200 },
    { date: "2026-05-29", count: 155 },
    { date: "2026-06-05", count: 142 },
  ],
  pieData: [
    { name: "Fragment", value: 48, color: "hsl(175,80%,50%)" },
    { name: "Fiber", value: 28, color: "hsl(200,80%,60%)" },
    { name: "Film", value: 14, color: "hsl(45,93%,58%)" },
    { name: "Pellet", value: 10, color: "hsl(280,70%,60%)" },
  ],
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:5000").replace(/\/+$/, "");

interface BackendStats {
  metrics: { avg_particles_per_liter: number; avg_contamination: string; total_samples: number };
  trendData: { date: string; count: number }[];
  pieData: { name: string; value: number; color: string }[];
}

const mapStatusColor = (status: string) => {
  if (status === "Safe") return "safe" as const;
  if (status === "Moderate" || status === "Caution") return "moderate" as const;
  if (status === "Danger" || status === "Critical") return "danger" as const;
  return undefined;
};

const Dashboard = () => {
  const [stats, setStats] = useState<BackendStats>(DEMO_STATS);
  const [loading, setLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        const response = await fetch(`${API_BASE}/api/stats`, { signal: controller.signal });
        clearTimeout(timeout);
        if (!response.ok) throw new Error("Non-OK response");
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        setStats(data);
        setIsDemo(false);
      } catch {
        setStats(DEMO_STATS);
        setIsDemo(true);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="container pt-24 pb-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-start justify-between mb-1">
            <h1 className="text-3xl font-bold">Environmental Dashboard</h1>
            {isDemo && !loading && (
              <span className="flex items-center gap-1.5 text-xs text-status-moderate bg-status-moderate/10 border border-status-moderate/30 px-3 py-1.5 rounded-full mt-1">
                <WifiOff className="w-3 h-3" /> Demo Mode — Backend offline
              </span>
            )}
          </div>
          <p className="text-muted-foreground mb-8">Real-time microplastic monitoring &amp; analytics</p>
        </motion.div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-12 h-12 text-primary animate-spin mb-4" />
            <p className="text-muted-foreground">Loading historical data...</p>
          </div>
        )}

        {!loading && (
          <AnimatePresence>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              {/* Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <MetricCard
                  title="Avg Particles / Liter"
                  value={stats.metrics.avg_particles_per_liter.toString()}
                  icon={Droplets}
                  status={mapStatusColor(stats.metrics.avg_contamination)}
                />
                <MetricCard
                  title="Avg Contamination"
                  value={stats.metrics.avg_contamination}
                  icon={AlertTriangle}
                  status={mapStatusColor(stats.metrics.avg_contamination)}
                />
                <MetricCard
                  title="Total Samples Analyzed"
                  value={stats.metrics.total_samples.toString()}
                  icon={TrendingUp}
                />
              </div>

              {/* Charts row */}
              <div className="grid lg:grid-cols-2 gap-6 mb-8">
                {/* Pie */}
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="glass rounded-xl p-6">
                  <h3 className="font-semibold mb-4">Plastic Types Distribution</h3>
                  {stats.pieData.length > 0 ? (
                    <div className="flex items-center gap-6">
                      <ResponsiveContainer width="50%" height={220}>
                        <PieChart>
                          <Pie data={stats.pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4} dataKey="value">
                            {stats.pieData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color || "hsl(175, 80%, 50%)"} />
                            ))}
                          </Pie>
                          <Tooltip contentStyle={{ background: "hsl(220,18%,8%)", border: "1px solid hsl(220,14%,16%)", borderRadius: 8, color: "#fff" }} />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="space-y-3 flex-1">
                        {stats.pieData.map((d, index) => (
                          <div key={index} className="flex items-center gap-2 text-sm">
                            <div className="w-3 h-3 rounded-full shrink-0" style={{ background: d.color || "hsl(175, 80%, 50%)" }} />
                            <span className="text-muted-foreground capitalize">{d.name}</span>
                            <span className="font-semibold ml-auto">{d.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="h-[220px] flex items-center justify-center text-muted-foreground">No distribution data yet. Run your first analysis!</div>
                  )}
                </motion.div>

                {/* Trend */}
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="glass rounded-xl p-6">
                  <h3 className="font-semibold mb-4">Historical Trends</h3>
                  {stats.trendData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={220}>
                      <AreaChart data={stats.trendData}>
                        <defs>
                          <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="hsl(175,80%,50%)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="hsl(175,80%,50%)" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,16%)" />
                        <XAxis dataKey="date" stroke="hsl(215,16%,52%)" fontSize={10} tickFormatter={(v) => v.slice(5)} />
                        <YAxis stroke="hsl(215,16%,52%)" fontSize={12} />
                        <Tooltip contentStyle={{ background: "hsl(220,18%,8%)", border: "1px solid hsl(220,14%,16%)", borderRadius: 8, color: "#fff" }} />
                        <Area type="monotone" dataKey="count" stroke="hsl(175,80%,50%)" fillOpacity={1} fill="url(#colorCount)" strokeWidth={2} />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[220px] flex items-center justify-center text-muted-foreground">Upload samples to see trends.</div>
                  )}
                </motion.div>
              </div>

              {/* IoT Panel */}
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="glass rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="w-4 h-4 text-primary animate-pulse" />
                  <h3 className="font-semibold">Real-Time IoT Sensor Data (Mocked)</h3>
                  <span className="ml-auto text-xs text-primary font-mono">● LIVE</span>
                </div>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={iotData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,16%)" />
                    <XAxis dataKey="time" stroke="hsl(215,16%,52%)" fontSize={12} />
                    <YAxis stroke="hsl(215,16%,52%)" fontSize={12} />
                    <Tooltip contentStyle={{ background: "hsl(220,18%,8%)", border: "1px solid hsl(220,14%,16%)", borderRadius: 8, color: "#fff" }} />
                    <Line type="monotone" dataKey="ph" stroke="hsl(175,80%,50%)" strokeWidth={2} dot={false} name="pH" />
                    <Line type="monotone" dataKey="turbidity" stroke="hsl(45,93%,58%)" strokeWidth={2} dot={false} name="Turbidity (NTU)" />
                    <Line type="monotone" dataKey="temp" stroke="hsl(200,80%,50%)" strokeWidth={2} dot={false} name="Temp (°C)" />
                  </LineChart>
                </ResponsiveContainer>
              </motion.div>
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
