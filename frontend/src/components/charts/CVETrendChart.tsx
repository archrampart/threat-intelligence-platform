import { useState, useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface CVETrendData {
  date: string;
  count: number;
}

interface CVETrendChartProps {
  data: CVETrendData[];
}

const CVETrendChart = ({ data }: CVETrendChartProps) => {
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

  // Validate and format data
  if (!data || !Array.isArray(data) || data.length === 0) {
    return (
      <div className="flex h-[300px] items-center justify-center text-slate-400 dark:text-slate-400 light:text-slate-600">
        No CVE trend data available
      </div>
    );
  }

  const formattedData = data.map((item) => {
    try {
      const date = new Date(item.date);
      if (isNaN(date.getTime())) {
        console.warn(`Invalid date format: ${item.date}`);
        return {
          ...item,
          dateLabel: item.date,
        };
      }
      return {
        ...item,
        dateLabel: date.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      };
    } catch (error) {
      console.error(`Error formatting date ${item.date}:`, error);
      return {
        ...item,
        dateLabel: item.date,
      };
    }
  });

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={formattedData}>
        <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? "rgb(148 163 184 / 0.3)" : "rgb(203 213 225 / 0.5)"} />
        <XAxis 
          dataKey="dateLabel" 
          stroke={isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)"}
          style={{ fontSize: "12px" }}
          tick={{ fill: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)" }}
        />
        <YAxis 
          stroke={isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)"}
          style={{ fontSize: "12px" }}
          tick={{ fill: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)" }}
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
        />
        <Legend 
          wrapperStyle={{
            color: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)",
          }}
        />
        <Line 
          type="monotone" 
          dataKey="count" 
          stroke={isDarkMode ? "rgb(239 68 68)" : "rgb(220 38 38)"} 
          strokeWidth={2}
          name="CVEs Published"
          dot={{ fill: isDarkMode ? "rgb(239 68 68)" : "rgb(220 38 38)", r: 4 }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default CVETrendChart;






