import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface IOCTypeDistributionChartProps {
  data: Array<{ ioc_type: string; count: number; percentage: number }>;
}

const IOCTypeDistributionChart = ({ data }: IOCTypeDistributionChartProps) => {
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
        No IOC type data available
      </div>
    );
  }

  const formattedData = data.map((item) => ({
    type: item.ioc_type.toUpperCase(),
    count: item.count,
    percentage: item.percentage,
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={formattedData}>
        <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? "rgb(148 163 184 / 0.3)" : "rgb(148 163 184 / 0.2)"} />
        <XAxis 
          dataKey="type" 
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
          formatter={(value: number, name: string, props: any) => [
            `${value} (${props.payload.percentage.toFixed(1)}%)`,
            "Count",
          ]}
        />
        <Legend 
          wrapperStyle={{
            color: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)",
          }}
        />
        <Bar 
          dataKey="count" 
          fill="rgb(96 165 250)" 
          radius={[8, 8, 0, 0]}
          name="Queries"
        />
      </BarChart>
    </ResponsiveContainer>
  );
};

export default IOCTypeDistributionChart;

