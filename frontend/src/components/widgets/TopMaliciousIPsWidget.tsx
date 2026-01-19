import { Skull, ExternalLink } from "lucide-react";
import type { TopMaliciousIP } from "@/features/dashboard/types";

interface TopMaliciousIPsWidgetProps {
    data: TopMaliciousIP[];
}

const getRiskBadgeColor = (level: string) => {
    switch (level) {
        case "critical":
            return "bg-red-950/30 text-red-400 border-red-800 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800 light:bg-red-100 light:text-red-700 light:border-red-200";
        case "high":
            return "bg-orange-950/30 text-orange-400 border-orange-800 dark:bg-orange-950/30 dark:text-orange-400 dark:border-orange-800 light:bg-orange-100 light:text-orange-700 light:border-orange-200";
        case "medium":
            return "bg-yellow-950/30 text-yellow-400 border-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-400 dark:border-yellow-800 light:bg-yellow-100 light:text-yellow-700 light:border-yellow-200";
        case "low":
            return "bg-green-950/30 text-green-400 border-green-800 dark:bg-green-950/30 dark:text-green-400 dark:border-green-800 light:bg-green-100 light:text-green-700 light:border-green-200";
        default:
            return "bg-slate-800 text-slate-400 border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700 light:bg-slate-100 light:text-slate-600 light:border-slate-200";
    }
};

const TopMaliciousIPsWidget = ({ data }: TopMaliciousIPsWidgetProps) => {
    if (!data || data.length === 0) {
        return (
            <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-4">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">Top Malicious IPs</h2>
                    <Skull className="h-4 w-4 text-red-400" />
                </div>
                <div className="flex h-[200px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
                    No malicious IPs detected
                </div>
            </div>
        );
    }

    return (
        <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-4">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">Top Malicious IPs</h2>
                <Skull className="h-4 w-4 text-red-400" />
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {data.map((ip, index) => (
                    <div
                        key={ip.ip}
                        className="flex items-center justify-between rounded-lg bg-slate-900/60 dark:bg-slate-900/60 light:bg-slate-50 px-4 py-3 hover:bg-slate-800/60 dark:hover:bg-slate-800/60 light:hover:bg-slate-100 transition"
                    >
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                            <span className="text-xs font-bold text-slate-500 w-5">#{index + 1}</span>
                            <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-mono font-medium text-white dark:text-white light:text-slate-900 truncate">
                                        {ip.ip}
                                    </span>
                                    <a
                                        href={`/ioc?query=${ip.ip}&type=ip`}
                                        className="text-brand-400 hover:text-brand-300 transition"
                                        title="View IOC details"
                                    >
                                        <ExternalLink className="h-3 w-3" />
                                    </a>
                                </div>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="text-xs text-slate-500">
                                        {ip.detection_count} detection{ip.detection_count !== 1 ? "s" : ""}
                                    </span>
                                    {ip.sources.length > 0 && (
                                        <span className="text-xs text-slate-600">
                                            • {ip.sources.slice(0, 2).join(", ")}
                                            {ip.sources.length > 2 && ` +${ip.sources.length - 2}`}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                            <span className="text-sm font-semibold text-white dark:text-white light:text-slate-900">
                                {ip.risk_score}%
                            </span>
                            <span
                                className={`rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${getRiskBadgeColor(ip.risk_level)}`}
                            >
                                {ip.risk_level}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TopMaliciousIPsWidget;
