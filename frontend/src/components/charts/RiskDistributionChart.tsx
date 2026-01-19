import { useState, useEffect } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, Sector } from "recharts";

interface RiskDistributionChartProps {
  data: {
    low: number;
    medium: number;
    high: number;
    critical: number;
    unknown: number;
  };
  onSegmentClick?: (risk: string) => void;
}

const COLORS = {
  low: "#10b981", // green
  medium: "#f59e0b", // amber
  high: "#ef4444", // red
  critical: "#dc2626", // dark red
  unknown: "#6b7280", // gray
};

const RiskDistributionChart = ({ data, onSegmentClick }: RiskDistributionChartProps) => {
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    // Check if dark mode is active
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

  const chartData = [
    { name: "Low", value: data.low, risk: "low" },
    { name: "Medium", value: data.medium, risk: "medium" },
    { name: "High", value: data.high, risk: "high" },
    { name: "Critical", value: data.critical, risk: "critical" },
    { name: "Unknown", value: data.unknown, risk: "unknown" },
  ].filter((item) => item.value > 0);

  const handleClick = (data: any) => {
    if (onSegmentClick && data?.risk) {
      onSegmentClick(data.risk);
    }
  };

  // Custom active shape to prevent color change on hover - just slightly expand
  const renderActiveShape = (props: any) => {
    const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
    return (
      <g>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRadius}
          outerRadius={outerRadius + 5}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
          opacity={1}
        />
      </g>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={true}
          label={({ name, value, percent }) => {
            if (!percent) return "";
            // Only show label if percentage is >= 8% to avoid overlapping
            if (percent >= 0.08) {
              return `${(percent * 100).toFixed(0)}%`;
            }
            return "";
          }}
          outerRadius={100}
          fill="#8884d8"
          dataKey="value"
          nameKey="name"
          onClick={handleClick}
          style={{ cursor: onSegmentClick ? "pointer" : "default" }}
          activeShape={renderActiveShape}
        >
          {chartData.map((entry, index) => (
            <Cell 
              key={`cell-${index}`} 
              fill={COLORS[entry.risk as keyof typeof COLORS]}
              stroke={COLORS[entry.risk as keyof typeof COLORS]}
              strokeWidth={2}
            />
          ))}
        </Pie>
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
            const percent = ((value / chartData.reduce((sum, item) => sum + item.value, 0)) * 100).toFixed(1);
            return [`${value} (${percent}%)`, props.payload.name];
          }}
        />
        <Legend 
          wrapperStyle={{
            color: isDarkMode ? "rgb(148 163 184)" : "rgb(71 85 105)",
          }}
          formatter={(value: string, entry: any) => {
            // Return the risk name (Low, Medium, High, etc.)
            return entry.payload?.name || value;
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default RiskDistributionChart;

