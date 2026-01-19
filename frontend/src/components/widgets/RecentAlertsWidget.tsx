import { Bell, AlertTriangle, AlertOctagon, AlertCircle, Info, Eye } from "lucide-react";
import type { RecentAlertItem } from "@/features/dashboard/types";

interface RecentAlertsWidgetProps {
    data: RecentAlertItem[];
    onViewAll?: () => void;
}

const getSeverityIcon = (severity: string) => {
    switch (severity) {
        case "critical":
            return <AlertOctagon className="h-4 w-4 text-red-400" />;
        case "high":
            return <AlertTriangle className="h-4 w-4 text-orange-400" />;
        case "medium":
            return <AlertCircle className="h-4 w-4 text-yellow-400" />;
        case "low":
            return <Info className="h-4 w-4 text-blue-400" />;
        default:
            return <Bell className="h-4 w-4 text-slate-400" />;
    }
};

const getSeverityBadgeColor = (severity: string) => {
    switch (severity) {
        case "critical":
            return "bg-red-950/30 text-red-400 border-red-800 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800 light:bg-red-100 light:text-red-700 light:border-red-200";
        case "high":
            return "bg-orange-950/30 text-orange-400 border-orange-800 dark:bg-orange-950/30 dark:text-orange-400 dark:border-orange-800 light:bg-orange-100 light:text-orange-700 light:border-orange-200";
        case "medium":
            return "bg-yellow-950/30 text-yellow-400 border-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-400 dark:border-yellow-800 light:bg-yellow-100 light:text-yellow-700 light:border-yellow-200";
        case "low":
            return "bg-blue-950/30 text-blue-400 border-blue-800 dark:bg-blue-950/30 dark:text-blue-400 dark:border-blue-800 light:bg-blue-100 light:text-blue-700 light:border-blue-200";
        default:
            return "bg-slate-800 text-slate-400 border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700 light:bg-slate-100 light:text-slate-600 light:border-slate-200";
    }
};

const getAlertTypeBadge = (alertType: string) => {
    switch (alertType) {
        case "watchlist":
            return "🔍";
        case "ioc_query":
            return "🎯";
        case "cve":
            return "🛡️";
        case "system":
            return "⚙️";
        default:
            return "📌";
    }
};

const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return "Just now";
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
};

const RecentAlertsWidget = ({ data, onViewAll }: RecentAlertsWidgetProps) => {
    const unreadCount = data.filter((alert) => !alert.is_read).length;

    if (!data || data.length === 0) {
        return (
            <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-4">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">Recent Alerts</h2>
                    <Bell className="h-4 w-4 text-brand-400" />
                </div>
                <div className="flex h-[200px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
                    No alerts
                </div>
            </div>
        );
    }

    return (
        <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-4">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">Recent Alerts</h2>
                    {unreadCount > 0 && (
                        <span className="rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white">
                            {unreadCount}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    {onViewAll && (
                        <button
                            onClick={onViewAll}
                            className="text-xs text-brand-400 hover:text-brand-300 transition flex items-center gap-1"
                        >
                            <Eye className="h-3 w-3" />
                            View All
                        </button>
                    )}
                    <Bell className="h-4 w-4 text-brand-400" />
                </div>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {data.map((alert) => (
                    <div
                        key={alert.id}
                        className={`flex items-start gap-3 rounded-lg px-4 py-3 transition ${alert.is_read
                            ? "bg-slate-900/40 dark:bg-slate-900/40 light:bg-slate-50"
                            : "bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-100 border-l-2 border-brand-500"
                            }`}
                    >
                        <div className="flex-shrink-0 mt-0.5">
                            {getSeverityIcon(alert.severity)}
                        </div>
                        <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-2">
                                <p className={`text-sm font-medium truncate ${alert.is_read
                                    ? "text-slate-300 dark:text-slate-300 light:text-slate-700"
                                    : "text-white dark:text-white light:text-slate-900"
                                    }`}>
                                    {getAlertTypeBadge(alert.alert_type)} {alert.title}
                                </p>
                                <span
                                    className={`rounded-full border px-2 py-0.5 text-xs font-medium capitalize flex-shrink-0 ${getSeverityBadgeColor(alert.severity)}`}
                                >
                                    {alert.severity}
                                </span>
                            </div>
                            <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                                <span>{formatTimeAgo(alert.created_at)}</span>
                                {alert.watchlist_name && (
                                    <span className="truncate">• {alert.watchlist_name}</span>
                                )}
                                {alert.asset_value && (
                                    <span className="font-mono truncate">• {alert.asset_value}</span>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default RecentAlertsWidget;
