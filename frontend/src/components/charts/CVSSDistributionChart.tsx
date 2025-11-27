import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from "recharts";

interface CVSSDistributionData {
  score_range: string;
  count: number;
}

interface CVSSDistributionChartProps {
  data: CVSSDistributionData[];
}

const CVSSDistributionChart = ({ data }: CVSSDistributionChartProps) => {
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
        No CVSS distribution data available
      </div>
    );
  }

  // Color mapping based on score range
  const getColor = (range: string) => {
    if (range.startsWith("8.1")) return isDarkMode ? "rgb(239 68 68)" : "rgb(220 38 38)"; // Red for critical
    if (range.startsWith("6.1")) return isDarkMode ? "rgb(249 115 22)" : "rgb(234 88 12)"; // Orange for high
    if (range.startsWith("4.1")) return isDarkMode ? "rgb(234 179 8)" : "rgb(202 138 4)"; // Yellow for medium
    if (range.startsWith("2.1")) return isDarkMode ? "rgb(34 197 94)" : "rgb(22 163 74)"; // Green for low
    return isDarkMode ? "rgb(148 163 184)" : "rgb(100 116 139)"; // Gray for very low
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? "rgb(148 163 184 / 0.3)" : "rgb(203 213 225 / 0.5)"} />
        <XAxis 
          dataKey="score_range" 
          stroke={isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)"}
          style={{ fontSize: "12px" }}
        />
        <YAxis 
          stroke={isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)"}
          style={{ fontSize: "12px" }}
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
          formatter={(value: number, name: string, props: any) => {
            const total = data.reduce((sum, item) => sum + item.count, 0);
            const percent = total > 0 ? ((value / total) * 100).toFixed(1) : "0";
            return [`${value} (${percent}%)`, props.payload?.score_range || name];
          }}
        />
        <Legend 
          wrapperStyle={{
            color: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)",
          }}
        />
        <Bar 
          dataKey="count" 
          name="CVEs"
          radius={[8, 8, 0, 0]}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getColor(entry.score_range)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default CVSSDistributionChart;
