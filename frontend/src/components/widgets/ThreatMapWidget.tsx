import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { MapPin, Globe } from "lucide-react";
import type { TopMaliciousIP } from "@/features/dashboard/types";

interface ThreatMapWidgetProps {
    data: TopMaliciousIP[];
}

// Fix for default marker icon issue with Webpack
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
    iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
    shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

const getRiskColor = (level: string): string => {
    switch (level) {
        case "critical":
            return "#ef4444"; // red-500
        case "high":
            return "#fb923c"; // orange-400
        case "medium":
            return "#facc15"; // yellow-400
        case "low":
            return "#4ade80"; // green-400
        default:
            return "#94a3b8"; // slate-400
    }
};

const ThreatMapWidget = ({ data }: ThreatMapWidgetProps) => {
    const mapRef = useRef<L.Map | null>(null);
    const mapContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!mapContainerRef.current) return;

        // Initialize map
        if (!mapRef.current) {
            mapRef.current = L.map(mapContainerRef.current, {
                center: [20, 0],
                zoom: 2,
                zoomControl: true,
                scrollWheelZoom: true,
            });

            // Add dark tile layer
            L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
                maxZoom: 19,
            }).addTo(mapRef.current);
        }

        // Clear existing markers
        const map = mapRef.current;
        map.eachLayer((layer) => {
            if (layer instanceof L.Marker) {
                map.removeLayer(layer);
            }
        });

        // Add markers for IPs with geolocation
        data.forEach((ip) => {
            if (ip.latitude && ip.longitude) {
                const color = getRiskColor(ip.risk_level);

                // Create custom icon
                const icon = L.divIcon({
                    className: "custom-marker",
                    html: `<div style="
                        background-color: ${color};
                        width: 20px;
                        height: 20px;
                        border-radius: 50%;
                        border: 3px solid white;
                        box-shadow: 0 0 10px rgba(0,0,0,0.5);
                    "></div>`,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10],
                });

                const marker = L.marker([ip.latitude, ip.longitude], { icon })
                    .addTo(map)
                    .bindPopup(`
                        <div style="color: #1e293b; padding: 8px;">
                            <div style="font-weight: 600; margin-bottom: 4px;">${ip.ip}</div>
                            <div style="font-size: 12px; color: #64748b; margin-bottom: 8px;">
                                ${ip.city ? `${ip.city}, ` : ""}${ip.country_name || ip.country || "Unknown"}
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                <span style="
                                    background-color: ${color};
                                    color: white;
                                    padding: 2px 8px;
                                    border-radius: 9999px;
                                    font-size: 11px;
                                    font-weight: 600;
                                    text-transform: uppercase;
                                ">${ip.risk_level}</span>
                                <span style="font-size: 12px; font-weight: 600;">${ip.risk_score}%</span>
                            </div>
                            <div style="font-size: 11px; color: #64748b;">
                                ${ip.detection_count} detection${ip.detection_count !== 1 ? "s" : ""}
                            </div>
                        </div>
                    `);
            }
        });

        // Cleanup
        return () => {
            if (mapRef.current) {
                mapRef.current.remove();
                mapRef.current = null;
            }
        };
    }, [data]);

    const ipsWithLocation = data.filter((ip) => ip.latitude && ip.longitude);
    const ipsWithoutLocation = data.length - ipsWithLocation.length;

    return (
        <div className="rounded-2xl border border-slate-800 dark:border-slate-800 light:border-slate-200 bg-slate-900/30 dark:bg-slate-900/30 light:bg-white p-4">
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <h2 className="text-lg font-semibold text-white dark:text-white light:text-slate-900">
                        Threat Map
                    </h2>
                    {ipsWithLocation.length > 0 && (
                        <span className="text-xs text-slate-400 dark:text-slate-400 light:text-slate-600">
                            {ipsWithLocation.length} location{ipsWithLocation.length !== 1 ? "s" : ""}
                        </span>
                    )}
                </div>
                <Globe className="h-4 w-4 text-brand-400 dark:text-brand-400 light:text-brand-600" />
            </div>

            {data.length === 0 ? (
                <div className="flex h-[400px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
                    <div className="text-center">
                        <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p>No threat data available</p>
                    </div>
                </div>
            ) : ipsWithLocation.length === 0 ? (
                <div className="flex h-[400px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
                    <div className="text-center">
                        <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p>No geolocation data available</p>
                        <p className="text-xs mt-1">IP addresses found but location data is missing</p>
                    </div>
                </div>
            ) : (
                <>
                    <div
                        ref={mapContainerRef}
                        className="w-full h-[400px] rounded-lg overflow-hidden border border-slate-700 dark:border-slate-700 light:border-slate-300"
                    />
                    {ipsWithoutLocation > 0 && (
                        <div className="mt-2 text-xs text-slate-500 dark:text-slate-500 light:text-slate-600">
                            {ipsWithoutLocation} IP{ipsWithoutLocation !== 1 ? "s" : ""} without location data
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default ThreatMapWidget;
