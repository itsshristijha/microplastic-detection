import { motion } from "framer-motion";
import { User, Upload, FileText, TrendingUp } from "lucide-react";
import Navbar from "@/components/Navbar";
import MetricCard from "@/components/MetricCard";

const Profile = () => (
  <div className="min-h-screen bg-background">
    <Navbar />
    <div className="container pt-24 pb-12 max-w-4xl">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        {/* Profile header */}
        <div className="glass rounded-2xl p-8 flex flex-col sm:flex-row items-center gap-6 mb-8">
          <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center">
            <User className="w-10 h-10 text-primary" />
          </div>
          <div className="text-center sm:text-left">
            <h1 className="text-2xl font-bold">Dr. Sarah Chen</h1>
            <p className="text-muted-foreground">Lab Technician · Environmental Sciences</p>
            <p className="text-sm text-muted-foreground mt-1">Member since March 2025</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid sm:grid-cols-3 gap-4 mb-8">
          <MetricCard title="Total Uploads" value={42} icon={Upload} />
          <MetricCard title="Reports Generated" value={38} icon={FileText} />
          <MetricCard title="Avg. Particles/L" value={156} icon={TrendingUp} status="moderate" />
        </div>

        {/* Recent activity */}
        <div className="glass rounded-xl p-6">
          <h3 className="font-semibold mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {[
              { action: "Uploaded sample #42", time: "2 hours ago" },
              { action: "Generated report for Delhi site", time: "5 hours ago" },
              { action: "Uploaded sample #41", time: "1 day ago" },
              { action: "Downloaded PDF report", time: "2 days ago" },
            ].map((a, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                <span className="text-sm">{a.action}</span>
                <span className="text-xs text-muted-foreground">{a.time}</span>
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  </div>
);

export default Profile;
