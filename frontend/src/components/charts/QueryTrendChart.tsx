import { useState, useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface QueryTrendChartProps {
  data: Array<{ date: string; count: number }>;
}

const QueryTrendChart = ({ data }: QueryTrendChartProps) => {
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

  // Format date for display (MM/DD)
  const formattedData = data.map((item) => ({
    ...item,
    dateLabel: new Date(item.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={formattedData}>
        <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? "rgb(148 163 184 / 0.3)" : "rgb(148 163 184 / 0.2)"} />
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
          stroke="rgb(96 165 250)" 
          strokeWidth={2}
          name="Queries"
          dot={{ fill: "rgb(96 165 250)", r: 4 }}
          activeDot={{ r: 6, fill: "rgb(96 165 250)" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default QueryTrendChart;

