import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
}

const StatCard = ({ title, value, subtitle, icon: Icon }: StatCardProps) => {
  return (
    <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/40 dark:bg-slate-900/40 light:bg-white p-4 shadow-lg shadow-black/20 dark:shadow-black/20 light:shadow-slate-200/20">
      <div className="flex items-center justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-500 light:text-slate-600 mb-1">{title}</p>
          <p className="text-2xl font-bold text-white dark:text-white light:text-slate-900 mb-1">{value}</p>
          {subtitle && (
            <p className="text-sm text-slate-400 dark:text-slate-400 light:text-slate-600">{subtitle}</p>
          )}
        </div>
        <div className="flex-shrink-0 rounded-xl bg-brand-500/10 dark:bg-brand-500/10 light:bg-brand-100 p-3 text-brand-400 dark:text-brand-400 light:text-brand-600">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
};

export default StatCard;
