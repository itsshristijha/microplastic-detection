import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Droplets, Menu, X, LogOut, User as UserIcon } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";

const navLinks = [
  { to: "/", label: "Home" },
  { to: "/dashboard", label: "Dashboard" },
  { to: "/upload", label: "Analyze" },
  { to: "/map", label: "Map" },
  { to: "/reports", label: "Reports" },
];

const Navbar = () => {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error("Logout error", error);
    }
  };

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/30"
    >
      <div className="container flex items-center justify-between h-16">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center group-hover:bg-primary/30 transition-colors">
              <Droplets className="w-5 h-5 text-primary" />
            </div>
            <span className="font-bold text-lg tracking-tight">
              Project <span className="text-gradient">ELLE</span>
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === link.to
                    ? "text-primary bg-primary/10"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>

        <div className="hidden md:flex items-center gap-4">
          {user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-secondary text-sm font-medium">
                <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-primary text-[10px]">
                  {user.displayName ? user.displayName.charAt(0).toUpperCase() : <UserIcon className="w-3 h-3" />}
                </div>
                <span className="max-w-[120px] truncate">{user.displayName || user.email}</span>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground hover:text-status-danger">
                <LogOut className="w-4 h-4 mr-1.5" /> Log Out
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link to="/login">
                <Button variant="ghost" size="sm">Log In</Button>
              </Link>
              <Link to="/signup">
                <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90">
                  Sign Up
                </Button>
              </Link>
            </div>
          )}
        </div>

        <button
          className="md:hidden text-foreground"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X /> : <Menu />}
        </button>
      </div>

      {mobileOpen && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="md:hidden glass border-t border-border/30 px-4 pb-4 overflow-hidden"
        >
          <div className="flex flex-col py-2">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMobileOpen(false)}
                className="block py-3 text-sm font-medium text-muted-foreground hover:text-foreground border-b border-border/10 last:border-0"
              >
                {link.label}
              </Link>
            ))}
          </div>
          
          <div className="mt-4 pb-2">
            {user ? (
              <div className="space-y-4">
                 <div className="flex items-center gap-3 px-1">
                    <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
                      {user.displayName ? user.displayName.charAt(0).toUpperCase() : <UserIcon className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="text-sm font-bold">{user.displayName || "User"}</div>
                      <div className="text-xs text-muted-foreground">{user.email}</div>
                    </div>
                 </div>
                 <Button variant="outline" size="sm" onClick={() => { handleLogout(); setMobileOpen(false); }} className="w-full text-status-danger border-status-danger/20">
                    <LogOut className="w-4 h-4 mr-2" /> Log Out
                 </Button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Link to="/login" className="flex-1" onClick={() => setMobileOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full">Log In</Button>
                </Link>
                <Link to="/signup" className="flex-1" onClick={() => setMobileOpen(false)}>
                  <Button size="sm" className="w-full bg-primary text-primary-foreground">Sign Up</Button>
                </Link>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </motion.nav>
  );
};

export default Navbar;
