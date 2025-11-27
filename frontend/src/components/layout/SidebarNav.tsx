import { NavLink } from "react-router-dom";
import { LucideIcon, Activity, Shield, ShieldCheck, FileText, Database, Key, Users, Bell } from "lucide-react";
import clsx from "clsx";

import { useAuth } from "@/hooks/useAuth";

interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  allowedRoles?: ("admin" | "analyst" | "viewer")[];
}

const navItems: NavItem[] = [
  { label: "Dashboard", to: "/", icon: Activity, allowedRoles: ["admin", "analyst", "viewer"] },
  { label: "IOC Search", to: "/ioc", icon: Shield, allowedRoles: ["admin", "analyst", "viewer"] },
  { label: "CVE DB", to: "/cves", icon: Database, allowedRoles: ["admin", "analyst", "viewer"] },
  { label: "Watchlist", to: "/watchlist", icon: ShieldCheck, allowedRoles: ["admin", "analyst", "viewer"] },
  { label: "Reports", to: "/reports", icon: FileText, allowedRoles: ["admin", "analyst"] },
  { label: "API Keys", to: "/api-keys", icon: Key, allowedRoles: ["admin", "analyst"] },
  { label: "User Management", to: "/users", icon: Users, allowedRoles: ["admin"] },
  { label: "Alerts", to: "/alerts", icon: Bell, allowedRoles: ["admin", "analyst", "viewer"] }
];

const SidebarNav = () => {
  const { user } = useAuth();

  // Filter nav items based on user role
  const visibleNavItems = navItems.filter((item) => {
    if (!item.allowedRoles) return true; // If no role restriction, show to all
    if (!user) return false;
    return item.allowedRoles.includes(user.role as "admin" | "analyst" | "viewer");
  });

  return (
    <nav className="space-y-1">
      {visibleNavItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
              isActive
                ? "bg-brand-500/20 dark:bg-brand-500/20 light:bg-brand-100 text-white dark:text-white light:text-brand-700"
                : "text-slate-400 dark:text-slate-400 light:text-slate-600 hover:bg-slate-800 dark:hover:bg-slate-800 light:hover:bg-slate-100 hover:text-white dark:hover:text-white light:hover:text-slate-900"
            )
          }
        >
          <item.icon className="h-4 w-4" />
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
};

export default SidebarNav;
