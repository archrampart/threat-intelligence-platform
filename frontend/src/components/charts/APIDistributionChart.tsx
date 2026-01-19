import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface APIDistributionChartProps {
  data: Array<{ source: string; count: number; percentage: number }>;
}

const COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#f59e0b", // amber
  "#ef4444", // red
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
  "#14b8a6", // teal
  "#a855f7", // purple
  "#f43f5e", // rose
  "#6366f1", // indigo
];

const APIDistributionChart = ({ data }: APIDistributionChartProps) => {
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    const checkDarkMode = () => {
      const isDark = document.documentElement.classList.contains("dark");
      setIsDarkMode(isDark);
    };
    
    checkDarkMode();
    const observer = new MutationObserver(checkDarkMode);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    
    return () => observer.disconnect();
  }, []);

  if (!data || data.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
        No API usage data available
      </div>
    );
  }

  // Sort data by count descending and format for horizontal bar chart
  const sortedData = [...data]
    .sort((a, b) => b.count - a.count)
    .map((item) => ({
      source: item.source,
      count: item.count,
      percentage: item.percentage,
    }));

  // Calculate dynamic height based on number of items (min 300px, max 600px)
  const chartHeight = Math.min(600, Math.max(300, sortedData.length * 40));

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart 
        data={sortedData} 
        layout="vertical"
        margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? "rgb(148 163 184 / 0.3)" : "rgb(148 163 184 / 0.2)"} />
        <XAxis 
          type="number"
          stroke={isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)"}
          style={{ fontSize: "12px" }}
          tick={{ fill: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)" }}
        />
        <YAxis 
          type="category"
          dataKey="source"
          stroke={isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)"}
          style={{ fontSize: "12px" }}
          tick={{ fill: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)" }}
          width={90}
        />
        <Tooltip 
          contentStyle={{
            backgroundColor: isDarkMode ? "rgb(15 23 42)" : "rgb(255 255 255)",
            border: `1px solid ${isDarkMode ? "rgb(30 41 59)" : "rgb(226 232 240)"}`,
            borderRadius: "8px",
            color: isDarkMode ? "rgb(248 250 252)" : "rgb(15 23 42)",
          }}
          labelStyle={{ 
            color: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)",
            fontWeight: "600"
          }}
          itemStyle={{
            color: isDarkMode ? "rgb(248 250 252)" : "rgb(15 23 42)",
          }}
          formatter={(value: number, name: string, props: any) => [
            `${value} queries (${props.payload.percentage.toFixed(1)}%)`,
            "Count",
          ]}
        />
        <Bar 
          dataKey="count" 
          radius={[0, 8, 8, 0]}
          name="Queries"
        >
          {sortedData.map((entry, index) => (
            <Cell 
              key={`cell-${index}`} 
              fill={COLORS[index % COLORS.length]}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default APIDistributionChart;

