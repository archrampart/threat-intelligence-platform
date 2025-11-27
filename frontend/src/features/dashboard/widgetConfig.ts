export interface WidgetConfig {
  id: string;
  title: string;
  category: 'stats' | 'charts' | 'widgets' | 'cve_charts';
  defaultVisible: boolean;
}

export const WIDGET_CONFIGS: WidgetConfig[] = [
  // Stat Cards
  { id: 'stat_total_queries', title: 'Total Queries', category: 'stats', defaultVisible: true },
  { id: 'stat_active_apis', title: 'Active APIs', category: 'stats', defaultVisible: true },
  { id: 'stat_watchlist_assets', title: 'Watchlist Assets', category: 'stats', defaultVisible: true },
  { id: 'stat_reports', title: 'Reports', category: 'stats', defaultVisible: true },
  { id: 'stat_risk_critical', title: 'Critical Risks', category: 'stats', defaultVisible: true },
  { id: 'stat_risk_high', title: 'High Risks', category: 'stats', defaultVisible: true },
  { id: 'stat_risk_medium', title: 'Medium Risks', category: 'stats', defaultVisible: true },
  { id: 'stat_risk_low', title: 'Low Risks', category: 'stats', defaultVisible: true },
  
  // Charts
  { id: 'chart_query_trend', title: 'Query Trend', category: 'charts', defaultVisible: true },
  { id: 'chart_risk_distribution', title: 'Risk Distribution', category: 'charts', defaultVisible: true },
  { id: 'chart_api_distribution', title: 'API Usage Distribution', category: 'charts', defaultVisible: true },
  { id: 'chart_ioc_type_distribution', title: 'IOC Type Distribution', category: 'charts', defaultVisible: true },
  
  // Widgets
  { id: 'widget_recent_activity', title: 'Recent Activity', category: 'widgets', defaultVisible: true },
  { id: 'widget_watchlist_summary', title: 'Watchlist Summary', category: 'widgets', defaultVisible: true },
  { id: 'widget_api_status', title: 'API Status', category: 'widgets', defaultVisible: true },
  { id: 'widget_cve_summary', title: 'CVE Summary', category: 'widgets', defaultVisible: true },
  
  // CVE Charts
  { id: 'cve_chart_trend', title: 'CVE Publication Trend', category: 'cve_charts', defaultVisible: true },
  { id: 'cve_chart_cvss_distribution', title: 'CVSS Score Distribution', category: 'cve_charts', defaultVisible: true },
];

export const STORAGE_KEY = 'dashboard_widget_visibility';

export function getWidgetVisibility(): Record<string, boolean> {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Error loading widget visibility:', error);
  }
  
  // Return default visibility
  const defaultVisibility: Record<string, boolean> = {};
  WIDGET_CONFIGS.forEach(widget => {
    defaultVisibility[widget.id] = widget.defaultVisible;
  });
  return defaultVisibility;
}

export function saveWidgetVisibility(visibility: Record<string, boolean>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(visibility));
  } catch (error) {
    console.error('Error saving widget visibility:', error);
  }
}

export function isWidgetVisible(widgetId: string, visibility: Record<string, boolean>): boolean {
  if (visibility[widgetId] !== undefined) {
    return visibility[widgetId];
  }
  const config = WIDGET_CONFIGS.find(w => w.id === widgetId);
  return config?.defaultVisible ?? true;
}


