import React from "react";
import { PieChart } from "@mui/x-charts";
import { Box, Typography } from "@mui/material";

import CustomLegendIcon from "./CustomLegend";

const EnhancedPieChart = ({ data = [], percentageChanges = {} }) => {
  if (!data || data.length === 0) {
    return (
      <Box
        sx={{
          width: "100%",
          height: 400,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Typography>No data available</Typography>
      </Box>
    );
  }

  // Calculate total for percentages
  const total = data.reduce((sum, item) => sum + item.value, 0);

  // Custom colors for different categories
  const colors = [
    "#FF6B4A", // Red-Orange
    "#4254ED", // Blue
    "#68C183", // Green
    "#FF934A", // Orange
    "#45B6D9", // Light Blue
    "#9B6EF3", // Purple
    "#F7C244", // Yellow
    "#E774C3", // Pink
  ];

  // Add percentage and color to each data point
  const enhancedData = data.map((item, index) => ({
    ...item,
    percentage: ((item.value / total) * 100).toFixed(0),
    color: colors[index % colors.length],
  }));

  return (
    <Box sx={{ position: "relative", width: "100%", height: 400, pl: 4 }}>
      <PieChart
        series={[
          {
            data: enhancedData.map((item) => ({
              ...item,
              value: item.value,
              color: item.color,
            })),
            innerRadius: 55,
            outerRadius: 100,
            paddingAngle: 4,
            cornerRadius: 12,
            startAngle:-90,
            endAngle: 270,
            cx: 150,
            cy: 150,
          },
        ]}
        slotProps={{
          legend: { hidden: true },
        }}
        width={500}
        height={400}
      />

      {/* Legend Items */}
      <Box
        sx={{
          position: "absolute",
          top: 20,
          right: 20,
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
          bgcolor: "white",
          p: 2,
          borderRadius: 1,
        }}
      >
        {enhancedData.map((item) => (
          <Box
            key={item.id}
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            {/* Use your custom SVG icon and pass the dynamic color */}
            <CustomLegendIcon color={item.color} size={16} />
            <Typography variant="body2" sx={{ minWidth: 80 }}>
              {item.label}
            </Typography>
            <Typography variant="body2" sx={{ ml: 1, minWidth: 40 }}>
              {item.value}
            </Typography>
            <Typography
              variant="body2"
              sx={{
                ml: 1,
                color: percentageChanges[item.label] >= 0 ? "green" : "red",
              }}
            >
              {percentageChanges[item.label]
                ? `${Number(percentageChanges[item.label]) > 0 ? "+" : ""}${
                    percentageChanges[item.label]
                  }%`
                : "N/A"}
            </Typography>
          </Box>
        ))}
      </Box>

      {/* Percentage Labels */}
      {enhancedData.map((item, index) => {
        // Adjusted angle calculation to match legend position
        const angle = -90 + (360 * (index + 0.5)) / enhancedData.length;
        const rad = angle * (Math.PI / 180);
        const distance = 180; // Distance from center
        const x = 200 + Math.cos(rad) * distance;
        const y = 200 + Math.sin(rad) * distance;

        return (
          <Typography
            key={`label-${item.id}`}
            sx={{
              position: "absolute",
              left: `${x}px`,
              top: `${y}px`,
              transform: "translate(-50%, -50%)",
              color: item.color,
              fontWeight: "bold",
              fontSize: "14px",
            }}
          >
            {`${item.percentage}%`}
          </Typography>
        );
      })}
    </Box>
  );
};

export default EnhancedPieChart;
