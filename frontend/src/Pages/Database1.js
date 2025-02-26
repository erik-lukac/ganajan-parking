import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Select,
  MenuItem,
  TextField,
  Button,
  useTheme,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
} from "@mui/material";

import styled from "styled-components";
import { Download, FilterList } from "@mui/icons-material";
import { PieChart, BarChart, LineChart } from "@mui/x-charts";

import EnhancedPieChart from "../Components/Enhanced";

import CustomLegendIcon from "../Components/CustomLegend";

const chartColors = {
  primary: "#6366f1",
  secondary: "#3b82f6",
  success: "#22c55e",
  warning: "#f59e0b",
  danger: "#ef4444",
  info: "#06b6d4",
};

const DashboardContainer = styled(Box)(({ theme }) => ({
  backgroundColor: "#f8fafc",
  minHeight: "100vh",
}));

const StatCard = styled(Card)(({ theme }) => ({
  borderRadius: "12px",
  boxShadow: "0 1px 3px rgba(0,0,0,0.12)",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
  "&:hover": {
    transform: "translateY(-2px)",
    boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1)",
  },
}));

const ChartHeader = styled(Box)({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "24px",
  gap: "16px",
  flexWrap: "wrap",
});

const ExportButton = styled(Button)(({ theme }) => ({
  backgroundColor: chartColors.primary,
  color: "white",
  "&:hover": {
    backgroundColor: "#4f46e5",
  },
}));

const TimeRangeSelector = styled(Select)({
  minWidth: "200px",
  borderRadius: "12px",
  "& .MuiSelect-select": {
    padding: "12px 16px",
  },
});

const HeatmapContainer = styled(Box)({
  display: "grid",
  gridTemplateColumns: "repeat(24, 1fr)",
  gap: "2px",
});

const HeatmapCell = styled(Box, {
  shouldForwardProp: (prop) => prop !== "$intensity",
})(({ $intensity }) => ({
  height: "20px",
  backgroundColor: `rgba(99, 102, 241, ${$intensity})`,
  transition: "all 0.2s ease",
  "&:hover": {
    transform: "scale(1.1)",
    zIndex: 1,
  },
}));

const AnalyticsDashboard1 = () => {
  const componentRef = useRef();
  const theme = useTheme();
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState("today");
  const [dateRange, setDateRange] = useState({
    startDate: new Date(),
    endDate: new Date(),
  });
  const [exportTime, setExportTime] = useState(null);
  const [percentageChanges, setPercentageChanges] = useState({});

  const fetchStats = async () => {
    setLoading(true);
    try {
      const params = {
        time_range: timeRange === "custom" ? "custom" : timeRange,
        start_date:
          timeRange === "custom"
            ? dateRange.startDate.toISOString()
            : undefined,
        end_date:
          timeRange === "custom" ? dateRange.endDate.toISOString() : undefined,
      };

      const response = await axios.get(
        "http://localhost:8000/stats/enhanced-stats",
        { params }
      );
      console.log("API Response:", response.data);
      setStats(response.data.stats);
      setPercentageChanges(response.data.percentage_changes);
      console.log(stats);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchStats();
  }, [timeRange, dateRange]);

  const mostUsedGate = stats.gate_usage
    ? Object.entries(stats.gate_usage).reduce(
        (prev, curr) => (curr[1] > prev[1] ? curr : prev),
        ["N/A", 0]
      )[0]
    : "N/A";

  const formatDate = (date) => {
    if (!date) return "";
    return new Date(date).toLocaleString();
  };

  const handleDownloadPdf = async () => {
    setExportTime(new Date());
    await new Promise((resolve) => setTimeout(resolve, 100));

    if (componentRef.current) {
      html2canvas(componentRef.current, { scale: 2 }).then((canvas) => {
        const imgData = canvas.toDataURL("image/png");
        const pdf = new jsPDF("p", "mm", "a4");
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
        pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
        pdf.save("Analytics_Report.pdf");
      });
    }
  };

  const processHeatmapData = () => {
    if (!stats.heatmap_data || stats.heatmap_data.length === 0) return [];
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const counts = stats.heatmap_data.map((d) => d.count);
    const maxCount = Math.max(...counts);
    return days.map((day, dayIndex) => ({
      day,
      hours: Array.from({ length: 24 }, (_, hour) => {
        const dataPoint = stats.heatmap_data.find(
          (d) => d.day_of_week === dayIndex && d.hour === hour
        );
        let intensity = dataPoint ? dataPoint.count / maxCount : 0;
        intensity = intensity > 0 ? Math.min(intensity + 0.1, 1) : 0;
        return { hour, intensity };
      }),
    }));
  };

  const renderHeatmap = () => {
    const heatmapData = processHeatmapData();
    if (heatmapData.length === 0) return null;
    return (
      <StatCard>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Peak Times Heatmap
          </Typography>
          <Box sx={{ overflowX: "auto" }}>
            <Box sx={{ minWidth: "800px" }}>
              {heatmapData.map((dayData, index) => (
                <Box key={index} display="flex" alignItems="center" mb={1}>
                  <Box width={80} mr={1}>
                    <Typography variant="caption">{dayData.day}</Typography>
                  </Box>
                  <Box display="flex" flexGrow={1}>
                    {dayData.hours.map((hour, hourIndex) => (
                      <HeatmapCell
                        key={hourIndex}
                        $intensity={hour.intensity}
                        title={`${dayData.day} ${
                          hour.hour
                        }:00 - Intensity: ${Math.round(hour.intensity * 100)}%`}
                      />
                    ))}
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
          <Box mt={2} display="flex" justifyContent="space-between">
            <Typography variant="caption">0:00</Typography>
            <Typography variant="caption">23:00</Typography>
          </Box>
        </CardContent>
      </StatCard>
    );
  };

  const renderStatBoxes = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} sm={4}>
        <StatCard>
          <CardContent>
            <Typography variant="h6" color="textSecondary">
              Total Events
            </Typography>
            <Typography variant="h4">{stats.total_events || 0}</Typography>
          </CardContent>
        </StatCard>
      </Grid>
      <Grid item xs={12} sm={4}>
        <StatCard>
          <CardContent>
            <Typography variant="h6" color="textSecondary">
              Busiest Hour
            </Typography>
            <Typography variant="h4">
              {stats.busiest_hour !== null ? stats.busiest_hour + ":00" : "N/A"}
            </Typography>
          </CardContent>
        </StatCard>
      </Grid>
      <Grid item xs={12} sm={4}>
        <StatCard>
          <CardContent>
            <Typography variant="h6" color="textSecondary">
              Most Used Gate
            </Typography>
            <Typography variant="h4">{mostUsedGate}</Typography>
          </CardContent>
        </StatCard>
      </Grid>
    </Grid>
  );

  const renderCharts = () => (
    <>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <StatCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Vehicle Categories
              </Typography>
              <EnhancedPieChart
                data={Object.entries(stats.category_counts || {}).map(
                  ([name, value]) => ({
                    id: name,
                    label: name,
                    value: typeof value === "number" ? value : 0,
                  })
                )}
                percentageChanges={percentageChanges}
              />
            </CardContent>
          </StatCard>
        </Grid>
        <Grid item xs={12} md={6}>
          <StatCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Hourly Trend
              </Typography>
              <LineChart
                xAxis={[
                  {
                    data: Object.keys(stats.hourly_trend || {}),
                    scaleType: "point",
                  },
                ]}
                series={[
                  { data: Object.values(stats.hourly_trend || {}), area: true },
                ]}
                width={500}
                height={300}
              />
            </CardContent>
          </StatCard>
        </Grid>
      </Grid>
      <Box mt={4}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <StatCard>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Zone Distribution
                </Typography>
                <BarChart
                  xAxis={[
                    {
                      scaleType: "band",
                      data: Object.keys(stats.zone_counts || {}),
                    },
                  ]}
                  series={[{ data: Object.values(stats.zone_counts || {}) }]}
                  width={500}
                  height={300}
                />
              </CardContent>
            </StatCard>
          </Grid>
          <Grid item xs={12} md={6}>
            <StatCard>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Color Distribution
                </Typography>
                <EnhancedPieChart
                  data={Object.entries(stats.color_distribution || {}).map(
                    ([name, value]) => ({ id: name, value, label: name })
                  )}
                  percentageChanges={percentageChanges}
                />
              </CardContent>
            </StatCard>
          </Grid>
        </Grid>
      </Box>
    </>
  );

  return (
    <DashboardContainer>
      <ChartHeader>
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          <ExportButton
            variant="contained"
            startIcon={<Download />}
            onClick={handleDownloadPdf}
          >
            Export Report
          </ExportButton>
          <TimeRangeSelector
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            startAdornment={<FilterList fontSize="small" sx={{ mr: 1 }} />}
          >
            <MenuItem value="today">Today</MenuItem>
            <MenuItem value="week">This Week</MenuItem>
            <MenuItem value="month">This Month</MenuItem>
            <MenuItem value="custom">Custom Range</MenuItem>
          </TimeRangeSelector>
        </Box>
        {timeRange === "custom" && (
          <Box sx={{ display: "flex", gap: 2, marginTop: 2 }}>
            <TextField
              type="date"
              label="Start Date"
              InputLabelProps={{ shrink: true }}
              value={dateRange.startDate.toISOString().split("T")[0]}
              onChange={(e) =>
                setDateRange({
                  ...dateRange,
                  startDate: new Date(e.target.value),
                })
              }
            />
            <TextField
              type="date"
              label="End Date"
              InputLabelProps={{ shrink: true }}
              value={dateRange.endDate.toISOString().split("T")[0]}
              onChange={(e) =>
                setDateRange({
                  ...dateRange,
                  endDate: new Date(e.target.value),
                })
              }
            />
          </Box>
        )}
      </ChartHeader>

      <div ref={componentRef}>
        {loading ? (
          <Box display="flex" justifyContent="center" mt={4}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {renderStatBoxes()}
            <Box mt={4}>
              {renderCharts()}
              <Grid container spacing={3}>
                <Grid item xs={12}>
                  {renderHeatmap()}
                </Grid>
              </Grid>
            </Box>
          </>
        )}
      </div>
    </DashboardContainer>
  );
};

export default AnalyticsDashboard1;
