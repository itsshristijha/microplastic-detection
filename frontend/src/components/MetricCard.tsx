import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  icon: LucideIcon;
  status?: "safe" | "moderate" | "danger";
}

const statusColors = {
  safe: "text-status-safe border-status-safe/30 bg-status-safe/5",
  moderate: "text-status-moderate border-status-moderate/30 bg-status-moderate/5",
  danger: "text-status-danger border-status-danger/30 bg-status-danger/5",
};

const MetricCard = ({ title, value, change, icon: Icon, status }: MetricCardProps) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className={`glass rounded-xl p-5 ${status ? statusColors[status] : ""}`}
  >
    <div className="flex items-start justify-between mb-3">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{title}</span>
      <Icon className={`w-4 h-4 ${status ? "" : "text-primary"}`} />
    </div>
    <div className="text-2xl font-bold tracking-tight">{value}</div>
    {change && (
      <span className={`text-xs mt-1 inline-block ${change.startsWith("+") ? "text-status-danger" : "text-status-safe"}`}>
        {change} from last week
      </span>
    )}
  </motion.div>
);

export default MetricCard;
