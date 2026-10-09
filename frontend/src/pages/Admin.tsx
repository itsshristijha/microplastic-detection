import { motion } from "framer-motion";
import { Users, BarChart3, Cpu, Shield } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import Navbar from "@/components/Navbar";
import MetricCard from "@/components/MetricCard";

const usageData = [
  { day: "Mon", uploads: 24 }, { day: "Tue", uploads: 31 },
  { day: "Wed", uploads: 18 }, { day: "Thu", uploads: 42 },
  { day: "Fri", uploads: 36 }, { day: "Sat", uploads: 12 },
  { day: "Sun", uploads: 8 },
];

const users = [
  { name: "Dr. Sarah Chen", role: "Lab Technician", uploads: 42, status: "Active" },
  { name: "James Wilson", role: "Admin", uploads: 15, status: "Active" },
  { name: "Priya Sharma", role: "General User", uploads: 8, status: "Active" },
  { name: "Mike Johnson", role: "Lab Technician", uploads: 31, status: "Inactive" },
];

const Admin = () => (
  <div className="min-h-screen bg-background">
    <Navbar />
    <div className="container pt-24 pb-12">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold mb-1">Admin Panel</h1>
        <p className="text-muted-foreground mb-8">Platform management & analytics</p>
      </motion.div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard title="Total Users" value={156} icon={Users} />
        <MetricCard title="Samples Today" value={42} icon={BarChart3} />
        <MetricCard title="Model Accuracy" value="96.2%" icon={Cpu} />
        <MetricCard title="Active Sessions" value={23} icon={Shield} />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Usage chart */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="glass rounded-xl p-6">
          <h3 className="font-semibold mb-4">Weekly Upload Activity</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={usageData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,16%)" />
              <XAxis dataKey="day" stroke="hsl(215,16%,52%)" fontSize={12} />
              <YAxis stroke="hsl(215,16%,52%)" fontSize={12} />
              <Tooltip contentStyle={{ background: "hsl(220,18%,8%)", border: "1px solid hsl(220,14%,16%)", borderRadius: 8, color: "#fff" }} />
              <Bar dataKey="uploads" fill="hsl(175,80%,50%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>

        {/* Users table */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="glass rounded-xl p-6">
          <h3 className="font-semibold mb-4">User Management</h3>
          <div className="space-y-2">
            {users.map((u) => (
              <div key={u.name} className="flex items-center gap-3 bg-secondary/30 rounded-lg p-3">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                  {u.name.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{u.name}</div>
                  <div className="text-xs text-muted-foreground">{u.role} · {u.uploads} uploads</div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${u.status === "Active" ? "text-status-safe bg-status-safe/10" : "text-muted-foreground bg-muted"}`}>
                  {u.status}
                </span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  </div>
);

export default Admin;
