import React, { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import {
  PieChart,
  BarChart,
  LineChart,
  AreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Bar,
  Line,
  Area,
  Pie,
  ResponsiveContainer,
  Cell,
} from "recharts";
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
} from "@mui/material";
import { styled } from "@mui/system";
import {
  Download,
  FilterList,
  ArrowUpward,
  ArrowDownward,
  TrendingUp,
  TrendingDown,
  CalendarToday,
  LocalShipping,
  CompareArrows,
} from "@mui/icons-material";
import { LineChart as MuiXLineChart } from "@mui/x-charts";
import { format } from "date-fns";
import { createRoot } from 'react-dom/client';
import EnhancedPieChart from "../Components/Enhanced";

const chartColors = {
  primary: {
    main: "#4F46E5",
    light: "#818CF8",
    dark: "#3730A3",
    gradient: "linear-gradient(135deg, #4F46E5 0%, #818CF8 100%)",
  },
  secondary: {
    main: "#10B981",
    light: "#34D399",
    dark: "#059669",
  },
  accent: {
    main: "#8B5CF6",
    light: "#A78BFA",
    dark: "#6D28D9",
  },
  background: {
    default: "#F8FAFC",
    paper: "#FFFFFF",
    gradient: "linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%)",
  },
  text: {
    primary: "#1E293B",
    secondary: "#64748B",
    light: "#94A3B8",
  },
  status: {
    success: "#059669",
    warning: "#D97706",
    error: "#DC2626",
  }
};

const DashboardContainer = styled(Box)(({ theme }) => ({
  padding: theme.spacing(4),
  minHeight: "100vh",
  backgroundColor: chartColors.background.default,
  backgroundImage: `
    radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.03) 0px, transparent 50%),
    radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.03) 0px, transparent 50%),
    radial-gradient(at 0% 100%, rgba(139, 92, 246, 0.03) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(236, 72, 153, 0.03) 0px, transparent 50%)
  `,
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(2),
  },
}));

const StatCard = styled(Card)({
  background: chartColors.background.paper,
  borderRadius: "16px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  boxShadow: "0px 4px 6px -1px rgba(0, 0, 0, 0.02), 0px 2px 4px -1px rgba(0, 0, 0, 0.01)",
  backdropFilter: "blur(20px)",
  transition: "all 0.3s ease",
  overflow: "visible",
  "&:hover": {
    transform: "translateY(-4px)",
    boxShadow: "0px 12px 24px -4px rgba(0, 0, 0, 0.08)",
  },
});

const DashboardHeader = styled(Box)({
  marginBottom: "32px",
  "& .title": {
    fontSize: "28px",
    fontWeight: 700,
    background: chartColors.primary.gradient,
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
    marginBottom: "8px",
  },
  "& .subtitle": {
    color: chartColors.text.secondary,
    fontSize: "16px",
  },
});

const ControlsContainer = styled(Box)(({ theme }) => ({
  display: "flex",
  gap: "16px",
  flexWrap: "wrap",
  marginBottom: "32px",
  [theme.breakpoints.down('sm')]: {
    flexDirection: "column",
  },
}));

const StyledTimeRangeSelect = styled(Select)({
  minWidth: "160px",
  backgroundColor: chartColors.background.paper,
  borderRadius: "12px",
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(148, 163, 184, 0.2)",
  },
  "&:hover .MuiOutlinedInput-notchedOutline": {
    borderColor: chartColors.primary.light,
  },
  "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
    borderColor: chartColors.primary.main,
  },
});

const StyledDatePicker = styled(TextField)({
  backgroundColor: chartColors.background.paper,
  borderRadius: "12px",
  "& .MuiOutlinedInput-root": {
    borderRadius: "12px",
  },
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(148, 163, 184, 0.2)",
  },
  "&:hover .MuiOutlinedInput-notchedOutline": {
    borderColor: chartColors.primary.light,
  },
});

const ExportButton = styled(Button)({
  background: chartColors.primary.gradient,
  borderRadius: "12px",
  padding: "10px 24px",
  color: "#FFFFFF",
  fontWeight: 600,
  textTransform: "none",
  transition: "all 0.3s ease",
  "&:hover": {
    transform: "translateY(-2px)",
    boxShadow: "0px 8px 16px rgba(79, 70, 229, 0.2)",
  },
  "&:disabled": {
    background: "linear-gradient(135deg, #A1A1AA 0%, #D4D4D8 100%)",
    color: "#FFFFFF",
    transform: "none",
    boxShadow: "none",
  },
});

const StatValue = styled(Typography)({
  fontSize: "32px",
  fontWeight: 700,
  color: chartColors.text.primary,
  marginBottom: "8px",
});

const StatLabel = styled(Typography)({
  fontSize: "14px",
  fontWeight: 500,
  color: chartColors.text.secondary,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
});

const ChartHeader = styled(Box)({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "24px",
  "& .title": {
    fontSize: "18px",
    fontWeight: 600,
    color: chartColors.text.primary,
  },
  "& .subtitle": {
    fontSize: "14px",
    color: chartColors.text.secondary,
  },
});

const SummarySection = styled(Box)({
  backgroundColor: "#ffffff",
  borderRadius: "16px",
  padding: "24px",
  marginTop: "32px",
  boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
});

const InsightCard = styled(Box)({
  backgroundColor: "#f8fafc",
  borderRadius: "12px",
  padding: "20px",
  height: "100%",
  transition: "all 0.2s ease",
  "&:hover": {
    transform: "translateY(-2px)",
    boxShadow: "0 4px 6px rgba(0,0,0,0.05)",
  },
});

const StatBox = styled(Box)({
  display: "flex",
  alignItems: "center",
  gap: "8px",
  padding: "8px 12px",
  borderRadius: "8px",
  backgroundColor: "#ffffff",
});

const HeatmapWrapper = styled(Box)({
  backgroundColor: "#ffffff",
  borderRadius: "8px",
  padding: "24px",
  boxShadow: "0px 2px 4px rgba(0, 0, 0, 0.1)",
  margin: "16px",
});

const HeatmapGrid = styled(Box)({
  display: "grid",
  gridTemplateColumns: "80px repeat(24, 1fr)",
  gap: "2px",
  marginTop: "16px",
  position: "relative",
  "& .hour-label": {
    fontSize: "12px",
    color: "#666666",
    textAlign: "center",
    paddingBottom: "8px",
  },
  "& .day-label": {
    fontSize: "13px",
    color: "#333333",
    fontWeight: 500,
    display: "flex",
    alignItems: "center",
    paddingRight: "16px",
  },
});

const HeatmapCell = styled("div")(({ intensity = 0 }) => ({
  width: "100%",
  height: "32px",
  backgroundColor: intensity === 0 ? "#f5f5f5" : `rgba(99, 102, 241, ${intensity})`,
  borderRadius: "4px",
  transition: "all 0.2s ease",
  cursor: "pointer",
  position: "relative",
  "&:hover": {
    transform: "scale(1.1)",
    zIndex: 2,
    boxShadow: "0px 2px 4px rgba(0, 0, 0, 0.2)",
  },
  "@media print": {
    "&:hover": {
      transform: "none !important",
      boxShadow: "none !important"
    }
  }
}));

const HeatmapTooltip = styled("div")({
  position: "absolute",
  top: "-30px",
  left: "50%",
  transform: "translateX(-50%)",
  backgroundColor: "#ffffff",
  boxShadow: "0px 2px 4px rgba(0, 0, 0, 0.1)",
  padding: "8px",
  borderRadius: "4px",
  fontSize: "12px",
  zIndex: 3,
  pointerEvents: "none",
  display: "none",
  whiteSpace: "nowrap",
  ".cell:hover &": {
    display: "block",
  },
});

const CustomTooltip = styled(Box)({
  backgroundColor: "#FFFFFF",
  borderRadius: "8px",
  padding: "12px",
  boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
  border: "1px solid #F1F5F9",
  "& .label": {
    color: chartColors.text.secondary,
    fontSize: "12px",
    fontWeight: 500,
    marginBottom: "4px",
  },
  "& .value": {
    color: chartColors.text.primary,
    fontSize: "16px",
    fontWeight: 600,
  },
});

const renderCustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <CustomTooltip>
        <Typography variant="body2" className="label">{label}</Typography>
        <Typography variant="body2" className="value">{payload[0].value.toLocaleString()}</Typography>
      </CustomTooltip>
    );
  }
  return null;
};

const PDF_PAGE = {
  WIDTH: 210,
  HEIGHT: 297,
  MARGIN: 15,
  CONTENT_WIDTH: 180,
};

const pdfStyles = {
  container: {
    width: `${PDF_PAGE.CONTENT_WIDTH}mm`,
    margin: '0 auto',
    padding: '10mm',
    backgroundColor: "#FFFFFF",
    fontFamily: "'Helvetica Neue', Arial, sans-serif",
    color: chartColors.text.primary,
  },
  header: {
    paddingBottom: "10mm",
    marginBottom: "15mm",
    borderBottom: `2px solid ${chartColors.primary.main}`,
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-end",
  },
  section: {
    padding: "8mm",
    backgroundColor: chartColors.background.default,
    borderRadius: "8px",
    marginBottom: "10mm",
    border: "1px solid rgba(148, 163, 184, 0.1)",
    pageBreakInside: "avoid",
  },
  title: {
    fontSize: "18pt",
    fontWeight: 700,
    color: chartColors.text.primary,
    marginBottom: "5mm",
  },
  subtitle: {
    fontSize: "12pt",
    fontWeight: 600,
    color: chartColors.text.secondary,
    marginBottom: "5mm",
  },
  statBox: {
    padding: "6mm",
    borderRadius: "6px",
    backgroundColor: "#FFFFFF",
    border: "1px solid rgba(148, 163, 184, 0.1)",
    marginBottom: "5mm",
  },
  footer: {
    fontSize: "8pt",
    color: chartColors.text.secondary,
    textAlign: "center",
    padding: "5mm 0",
    borderTop: "1px solid #E5E7EB",
    position: "fixed",
    bottom: "5mm",
    width: "100%",
  },
};

const AnalyticsReportPDF = React.forwardRef((props, ref) => {
  const { stats, timeRange, dateRange, exportTime } = props;
  const categoryColors = ["#8884d8", "#82ca9d", "#ffc658", "#ff8042", "#0088fe", "#00c49f"];

  const formatHour = (timestamp) => {
    const date = new Date(timestamp);
    const hours = date.getUTCHours();
    const period = hours >= 12 ? "PM" : "AM";
    const displayHour = hours % 12 || 12;
    return {
      date: date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }),
      time: `${displayHour}:00 ${period}`,
    };
  };

  const processHeatmapData = () => {
    if (!stats.heatmap_data) return [];
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const counts = stats.heatmap_data.map(d => d.count);
    const maxCount = Math.max(...counts, 1);
    return days.map((day, dayIndex) => ({
      day,
      hours: Array.from({ length: 24 }, (_, hour) => {
        const dataPoint = stats.heatmap_data.find(d => d.day_of_week === dayIndex && d.hour === hour);
        return dataPoint ? Math.min(dataPoint.count / maxCount + 0.1, 1) : 0;
      })
    }));
  };

  const processEntryExitByCategory = () => {
    if (!stats.entry_exit_by_category) return [];
    return Object.entries(stats.entry_exit_by_category).map(([category, counts]) => ({
      category,
      entry: counts.entry || 0,
      exit: counts.exit || 0,
    }));
  };

  const renderHeader = () => (
    <div style={pdfStyles.header}>
      <Box>
        <Typography style={pdfStyles.title}>Analytics Report</Typography>
        <Typography style={{ fontSize: "10pt", color: chartColors.text.secondary }}>
          Period: {timeRange === "custom"
            ? `${new Date(dateRange.startDate).toLocaleDateString()} - ${new Date(dateRange.endDate).toLocaleDateString()}`
            : timeRange.charAt(0).toUpperCase() + timeRange.slice(1)}
        </Typography>
        <Typography style={{ fontSize: "10pt", color: chartColors.text.secondary }}>
          Generated: {new Date(exportTime).toLocaleString()}
        </Typography>
      </Box>
      <Box style={{ background: chartColors.primary.main, padding: "8px 12px", borderRadius: "6px", color: "white" }}>
        <Typography style={{ fontSize: "10pt" }}>Total Events</Typography>
        <Typography style={{ fontSize: "14pt", fontWeight: 700 }}>{stats.total_events?.toLocaleString() || 0}</Typography>
      </Box>
    </div>
  );

  const renderStatBoxes = () => {
    const peakHour = Object.entries(stats.hourly_trend || {}).reduce((max, [hour, count]) =>
      count > max[1] ? [hour, count] : max, ["N/A", 0]);
    const formattedPeakTime = peakHour[0] !== "N/A" ? formatHour(parseInt(peakHour[0]) * 3600000).time : "N/A";

    return (
      <div style={pdfStyles.section}>
        <Typography style={pdfStyles.subtitle}>Key Statistics</Typography>
        <Grid container spacing={2}>
          <Grid item xs={4}>
            <Box style={pdfStyles.statBox}>
              <Typography style={{ fontSize: "10pt", color: chartColors.text.secondary }}>Total Events</Typography>
              <Typography style={{ fontSize: "18pt", fontWeight: 700 }}>{stats.total_events?.toLocaleString() || 0}</Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box style={pdfStyles.statBox}>
              <Typography style={{ fontSize: "10pt", color: chartColors.text.secondary }}>Peak Traffic Hour</Typography>
              <Typography style={{ fontSize: "18pt", fontWeight: 700 }}>{formattedPeakTime}</Typography>
            </Box>
          </Grid>
          <Grid item xs={4}>
            <Box style={pdfStyles.statBox}>
              <Typography style={{ fontSize: "10pt", color: chartColors.text.secondary }}>Most Used Gate</Typography>
              <Typography style={{ fontSize: "18pt", fontWeight: 700 }}>
                {stats.gate_usage ? Object.entries(stats.gate_usage).reduce((prev, curr) => (curr[1] > prev[1] ? curr : prev), ["N/A", 0])[0] : "N/A"}
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </div>
    );
  };

  const renderVehicleCategories = () => (
    <div style={pdfStyles.section}>
      <Typography style={pdfStyles.subtitle}>Vehicle Categories</Typography>
      <ResponsiveContainer width="100%" height={300}>
        <EnhancedPieChart
          data={Object.entries(stats.category_counts || {}).map(([name, value]) => ({
            id: name,
            label: name,
            value: typeof value === "number" ? value : 0,
          }))}
        />
      </ResponsiveContainer>
    </div>
  );

  const renderHourlyTrend = () => (
    <div style={pdfStyles.section}>
      <Typography style={pdfStyles.subtitle}>Hourly Trend</Typography>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={Object.entries(stats.hourly_trend || {}).map(([hour, count]) => ({ hour, count }))}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
          <XAxis dataKey="hour" tick={{ fontSize: "8pt", fill: chartColors.text.secondary }} />
          <YAxis tick={{ fontSize: "8pt", fill: chartColors.text.secondary }} />
          <Line type="monotone" dataKey="count" stroke={chartColors.primary.main} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );

  const renderZoneDistribution = () => (
    <div style={pdfStyles.section}>
      <Typography style={pdfStyles.subtitle}>Zone Distribution</Typography>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={Object.entries(stats.zone_counts || {}).map(([zone, count]) => ({ zone, count }))}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="zone" tick={{ fontSize: "8pt" }} />
          <YAxis tick={{ fontSize: "8pt" }} />
          <Bar dataKey="count" fill="#8884d8" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  const renderEntryExitDistribution = () => (
    <div style={pdfStyles.section}>
      <Typography style={pdfStyles.subtitle}>Entry/Exit Distribution</Typography>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={Object.entries(stats.entry_exit_counts || {}).map(([type, count]) => ({ name: type, value: count }))}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
            label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
            labelLine={false}
          >
            {categoryColors.map((color, index) => <Cell key={index} fill={color} />)}
          </Pie>
          <Legend wrapperStyle={{ fontSize: "8pt" }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );

  const renderEntryExitByCategory = () => (
    <div style={pdfStyles.section}>
      <Typography style={pdfStyles.subtitle}>Entry/Exit by Category</Typography>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={processEntryExitByCategory()}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="category" tick={{ fontSize: "8pt" }} angle={-45} textAnchor="end" />
          <YAxis tick={{ fontSize: "8pt" }} />
          <Legend wrapperStyle={{ fontSize: "8pt" }} />
          <Bar dataKey="entry" fill={chartColors.primary.main} />
          <Bar dataKey="exit" fill={chartColors.secondary.main} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  const renderDailyTrend = () => {
    const chartData = stats.daily_trend
      ? Object.entries(stats.daily_trend).map(([date, count]) => ({ date: new Date(date), count })).sort((a, b) => a.date - b.date)
      : [];
    return (
      <div style={pdfStyles.section}>
        <Typography style={pdfStyles.subtitle}>Daily Activity Trend</Typography>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={(date) => format(date, 'MMM d')} tick={{ fontSize: "8pt" }} angle={-45} textAnchor="end" />
            <YAxis tick={{ fontSize: "8pt" }} />
            <Area type="monotone" dataKey="count" stroke={chartColors.primary.main} fill={chartColors.primary.main} fillOpacity={0.3} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const renderHeatmap = () => {
    const heatmapData = processHeatmapData();
    const hours = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, "0")}:00`);
    return (
      <div style={pdfStyles.section}>
        <Typography style={pdfStyles.subtitle}>Peak Times Heatmap</Typography>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '1px', fontSize: '8pt' }}>
          {heatmapData.map((dayData) => (
            <div key={dayData.day} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <Typography style={{ paddingBottom: '2mm' }}>{dayData.day}</Typography>
              {dayData.hours.map((intensity, hourIndex) => (
                <div key={hourIndex} style={{ height: '8mm', width: '100%', backgroundColor: intensity === 0 ? '#f5f5f5' : `rgba(99, 102, 241, ${intensity})`, borderRadius: '2px', marginBottom: '1px' }}>
                  {hourIndex === 0 && <Typography style={{ fontSize: '6pt', color: '#666', textAlign: 'center' }}>{hours[hourIndex]}</Typography>}
                </div>
              ))}
            </div>
          ))}
        </div>
        <Typography style={{ fontSize: '6pt', color: chartColors.text.secondary, textAlign: 'center', marginTop: '5mm' }}>
          Hours 00:00 to 23:00 (top to bottom)
        </Typography>
      </div>
    );
  };

  const renderDetailedSummary = () => {
    const categoryData = processEntryExitByCategory();
    const totalTraffic = categoryData.reduce((acc, curr) => acc + curr.entry + curr.exit, 0);
    const peakHour = Object.entries(stats.hourly_trend || {}).reduce((max, [hour, count]) => (count > max.count ? { hour, count } : max), { hour: "0", count: 0 });
    const formattedPeakTime = formatHour(peakHour.hour);

    return (
      <div style={pdfStyles.section}>
        <Typography style={pdfStyles.subtitle}>Detailed Analytics Summary</Typography>
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Box style={pdfStyles.statBox}>
              <Typography style={{ fontSize: "10pt", color: chartColors.text.secondary, marginBottom: "4mm" }}>Total Traffic</Typography>
              <Typography style={{ fontSize: "14pt", fontWeight: 700 }}>{totalTraffic.toLocaleString()}</Typography>
            </Box>
            <Box style={pdfStyles.statBox}>
              <Typography style={{ fontSize: "10pt", color: chartColors.text.secondary, marginBottom: "4mm" }}>Peak Hour</Typography>
              <Typography style={{ fontSize: "14pt", fontWeight: 700 }}>{formattedPeakTime.time}</Typography>
              <Typography style={{ fontSize: "8pt", color: chartColors.text.secondary }}>{peakHour.count.toLocaleString()} events</Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box style={pdfStyles.statBox}>
              <Typography style={{ fontSize: "10pt", color: chartColors.text.secondary, marginBottom: "4mm" }}>Category Breakdown</Typography>
              {categoryData.map((category) => (
                <Box key={category.category} style={{ marginBottom: "4mm" }}>
                  <Typography style={{ fontSize: "10pt", fontWeight: 600 }}>{category.category}</Typography>
                  <Typography style={{ fontSize: "8pt" }}>Entry: {category.entry.toLocaleString()}</Typography>
                  <Typography style={{ fontSize: "8pt" }}>Exit: {category.exit.toLocaleString()}</Typography>
                </Box>
              ))}
            </Box>
          </Grid>
        </Grid>
      </div>
    );
  };

  return (
    <div ref={ref} style={pdfStyles.container}>
      {renderHeader()}
      {renderStatBoxes()}
      {renderVehicleCategories()}
      {renderHourlyTrend()}
      {renderZoneDistribution()}
      {renderEntryExitDistribution()}
      {renderEntryExitByCategory()}
      {renderDailyTrend()}
      {renderHeatmap()}
      {renderDetailedSummary()}
      <div style={pdfStyles.footer}>
        Generated by Parking Dashboard System • © {new Date().getFullYear()}
      </div>
    </div>
  );
});

const formatHour = (timestamp) => {
  try {
    const date = new Date(timestamp);
    const hours = date.getUTCHours();
    const period = hours >= 12 ? "PM" : "AM";
    const displayHour = hours % 12 || 12;
    return {
      date: date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }),
      time: `${displayHour}:00 ${period}`,
    };
  } catch (error) {
    console.error("Error formatting timestamp:", error);
    return { date: "Invalid Date", time: "Invalid Time" };
  }
};

const DatePickerContainer = styled(Box)({
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '8px 16px',
  backgroundColor: '#ffffff',
  borderRadius: '10px',
  border: '1px solid #E2E8F0',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  '&:hover': {
    borderColor: chartColors.primary.main,
    boxShadow: '0 0 0 3px rgba(79, 70, 229, 0.1)'
  },
  '&:focus-within': {
    borderColor: chartColors.primary.main,
    boxShadow: '0 0 0 3px rgba(79, 70, 229, 0.1)'
  }
});

const DateInput = styled(TextField)({
  '& .MuiInputBase-input': {
    padding: '12px',
    fontSize: '14px',
    fontWeight: 500,
    color: chartColors.text.primary,
    borderRadius: '8px',
    '&::-webkit-calendar-picker-indicator': {
      filter: 'invert(0.5)'
    }
  },
  '& .MuiOutlinedInput-root': {
    '& fieldset': { border: 'none' },
    '&:hover fieldset': { border: 'none' },
    '&.Mui-focused fieldset': { border: 'none', boxShadow: 'none' }
  }
});

const AnalyticsDashboard = () => {
  const categoryColors = ["#8884d8", "#82ca9d", "#ffc658", "#ff8042", "#0088fe", "#00c49f"];
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
  const [isExporting, setIsExporting] = useState(false);

  const handleDownloadPdf = async () => {
    if (!stats || Object.keys(stats).length === 0) {
      alert("No data available to generate the PDF.");
      return;
    }

    setIsExporting(true);
    setExportTime(new Date());
    const tempDiv = document.createElement("div");
    tempDiv.style.position = "absolute";
    tempDiv.style.left = "-9999px";
    tempDiv.style.width = `${PDF_PAGE.CONTENT_WIDTH}mm`;
    document.body.appendChild(tempDiv);

    const root = createRoot(tempDiv);
    root.render(
      <AnalyticsReportPDF
        stats={stats}
        timeRange={timeRange}
        dateRange={dateRange}
        exportTime={new Date()}
      />
    );

    await new Promise(resolve => setTimeout(resolve, 3000));
    const pdf = new jsPDF("p", "mm", "a4");
    let currentY = PDF_PAGE.MARGIN;
    let pageNumber = 1;

    const addNewPage = () => {
      pdf.addPage();
      currentY = PDF_PAGE.MARGIN;
      pageNumber++;
    };

    const checkPageBreak = (elementHeight) => {
      if (currentY + elementHeight > PDF_PAGE.HEIGHT - PDF_PAGE.MARGIN) {
        addNewPage();
      }
    };

    const sections = Array.from(tempDiv.children[0].children);
    for (const section of sections) {
      const canvas = await html2canvas(section, {
        scale: 2,
        useCORS: true,
        logging: true,
        width: PDF_PAGE.CONTENT_WIDTH * 3.78,
        windowWidth: PDF_PAGE.CONTENT_WIDTH * 3.78,
      });

      const imgWidth = PDF_PAGE.CONTENT_WIDTH;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      checkPageBreak(imgHeight);

      pdf.addImage(canvas, "PNG", PDF_PAGE.MARGIN, currentY, imgWidth, imgHeight);
      currentY += imgHeight + 10;

      pdf.setFontSize(10);
      pdf.text(`Page ${pageNumber}`, PDF_PAGE.WIDTH - 20, PDF_PAGE.HEIGHT - 10);
    }

    pdf.save(`Analytics_Report_${new Date().toISOString().split('T')[0]}.pdf`);
    document.body.removeChild(tempDiv);
    root.unmount();
    setIsExporting(false);
  };

  const fetchStats = async () => {
    setLoading(true);
    try {
      const params = {
        time_range: timeRange,
      };

      const now = new Date();
      let startDateObj, endDateObj;

      if (timeRange === "custom") {
        startDateObj = new Date(dateRange.startDate);
        endDateObj = new Date(dateRange.endDate);
        startDateObj.setUTCHours(0, 0, 0, 0);
        endDateObj.setUTCHours(23, 59, 59, 999);
      } else if (timeRange === "today") {
        startDateObj = new Date(now);
        startDateObj.setUTCHours(0, 0, 0, 0);  // Today midnight UTC
        endDateObj = new Date(now);            // Current time UTC
      } else if (timeRange === "week") {
        startDateObj = new Date(now);
        startDateObj.setUTCDate(now.getUTCDate() - now.getUTCDay());
        startDateObj.setUTCHours(0, 0, 0, 0);
        endDateObj = new Date(now);
        endDateObj.setUTCHours(23, 59, 59, 999);
      } else if (timeRange === "month") {
        startDateObj = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
        endDateObj = new Date(now);
        endDateObj.setUTCHours(23, 59, 59, 999);
      }

      if (startDateObj && endDateObj) {
        params.start_date = startDateObj.toUTCString();
        params.end_date = endDateObj.toUTCString();
      }

      console.log("Sending params to backend:", params);
      const response = await axios.get("/api/stats/enhanced-stats", { params });
      setStats(response.data.stats);
      setPercentageChanges(response.data.percentage_changes);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchStats();
  }, [timeRange, dateRange]);

  const mostUsedGate = stats.gate_usage ? Object.entries(stats.gate_usage).reduce((prev, curr) => (curr[1] > prev[1] ? curr : prev), ["N/A", 0])[0] : "N/A";

  const renderStatBoxes = () => {
    const peakHour = Object.entries(stats.hourly_trend || {}).reduce((max, [hour, count]) =>
      count > max[1] ? [hour, count] : max, ["N/A", 0]);
    const formattedPeakTime = peakHour[0] !== "N/A" ? formatHour(parseInt(peakHour[0]) * 3600000).time : "N/A";

    return (
      <Grid container spacing={3}>
        <Grid item xs={12} sm={4}>
          <StatCard>
            <CardContent>
              <StatLabel>Total Vehicles</StatLabel>
              <StatValue>{stats.total_events?.toLocaleString() || 0}</StatValue>
            </CardContent>
          </StatCard>
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard>
            <CardContent>
              <StatLabel>Peak Traffic Hour</StatLabel>
              <StatValue>{formattedPeakTime}</StatValue>
            </CardContent>
          </StatCard>
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard>
            <CardContent>
              <StatLabel>Most Used Gate</StatLabel>
              <StatValue>{mostUsedGate}</StatValue>
            </CardContent>
          </StatCard>
        </Grid>
      </Grid>
    );
  };

  const renderCharts = () => (
    <>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <StatCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>Vehicle Categories</Typography>
              <ResponsiveContainer width="100%" height={400}>
                <EnhancedPieChart
                  data={Object.entries(stats.category_counts || {}).map(([name, value]) => ({
                    id: name,
                    label: name,
                    value: typeof value === "number" ? value : 0,
                  }))}
                  percentageChanges={percentageChanges}
                />
              </ResponsiveContainer>
            </CardContent>
          </StatCard>
        </Grid>
        <Grid item xs={12} md={6}>
          <StatCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>Hourly Trend</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={Object.entries(stats.hourly_trend || {}).map(([hour, count]) => ({ hour, count }))} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="hour" tick={{ fill: chartColors.text.secondary }} axisLine={{ stroke: "#E2E8F0" }} />
                  <YAxis tick={{ fill: chartColors.text.secondary }} axisLine={{ stroke: "#E2E8F0" }} />
                  <Tooltip content={renderCustomTooltip} />
                  <Line type="monotone" dataKey="count" stroke={chartColors.primary.main} strokeWidth={2} dot={{ fill: chartColors.primary.main, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </StatCard>
        </Grid>
      </Grid>
      <Box mt={4}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <StatCard>
              <CardContent>
                <Typography variant="h6" gutterBottom>Zone Distribution</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={Object.entries(stats.zone_counts || {}).map(([zone, count]) => ({ zone, count }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="zone" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </StatCard>
          </Grid>
          <Grid item xs={12} md={4}>
            <StatCard>
              <CardContent>
                <Typography variant="h6" gutterBottom>Entry/Exit Distribution</Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={Object.entries(stats.entry_exit_counts || {}).map(([type, count]) => ({ name: type, value: count }))}
                      innerRadius={70}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {Object.entries(stats.entry_exit_counts || {}).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index % 2 === 0 ? chartColors.primary.main : chartColors.secondary.main} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </StatCard>
          </Grid>
        </Grid>
      </Box>
    </>
  );

  const processHeatmapData = () => {
    if (!stats.heatmap_data || stats.heatmap_data.length === 0) {
      console.warn("No heatmap data available");
      return [];
    }
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const counts = stats.heatmap_data.map((d) => d.count);
    const maxCount = Math.max(...counts);
    return days.map((day, dayIndex) => ({
      day,
      hours: Array.from({ length: 24 }, (_, hour) => {
        const dataPoint = stats.heatmap_data.find((d) => d.day_of_week === dayIndex && d.hour === hour);
        let intensity = dataPoint ? dataPoint.count / maxCount : 0;
        intensity = intensity > 0 ? Math.min(intensity + 0.1, 1) : 0;
        return { hour, intensity };
      }),
    }));
  };

  const renderHeatmap = () => {
    const heatmapData = processHeatmapData();
    if (heatmapData.length === 0) {
      return (
        <HeatmapWrapper>
          <Typography variant="h6" gutterBottom>Peak Times Heatmap</Typography>
          <Typography variant="body1" sx={{ color: "#666666" }}>No heatmap data available.</Typography>
        </HeatmapWrapper>
      );
    }
    const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, "0") + ":00");
    return (
      <HeatmapWrapper>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h6">Peak Times Heatmap</Typography>
          <Box display="flex" alignItems="center" gap={2}>
            <Box sx={{ width: 16, height: 16, background: "linear-gradient(to right, #f5f5f5, rgb(99, 102, 241))", marginRight: 1, borderRadius: 1 }} />
            <Typography variant="caption" sx={{ color: "#666666" }}>Activity Level</Typography>
          </Box>
        </Box>
        <HeatmapGrid>
          <Box />
          {hours.map((hour) => <Typography key={hour} className="hour-label">{hour}</Typography>)}
          {heatmapData.map((dayData, dayIndex) => (
            <React.Fragment key={dayData.day}>
              <Typography className="day-label">{dayData.day}</Typography>
              {dayData.hours.map((hour, hourIndex) => (
                <Box key={hourIndex} className="cell" sx={{ position: "relative" }}>
                  <HeatmapCell intensity={hour.intensity}>
                    <HeatmapTooltip>{`${dayData.day} ${hours[hourIndex]}<br/>Activity: ${Math.round(hour.intensity * 100)}%`}</HeatmapTooltip>
                  </HeatmapCell>
                </Box>
              ))}
            </React.Fragment>
          ))}
        </HeatmapGrid>
        <Box mt={2} display="flex" justifyContent="flex-end">
          <Typography variant="caption" sx={{ color: "#666666" }}>Hover over cells to see detailed information</Typography>
        </Box>
      </HeatmapWrapper>
    );
  };

  const renderDailyTrend = () => {
    const chartData = stats.daily_trend ? Object.entries(stats.daily_trend).map(([date, count]) => ({ date: new Date(date), count })).sort((a, b) => a.date - b.date) : [];
    return (
      <StatCard>
        <CardContent>
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Daily Activity Trend</Typography>
            {chartData.length > 0 ? (
              <Box sx={{ width: "100%", height: 300 }}>
                <MuiXLineChart
                  dataset={chartData}
                  series={[{ data: chartData.map((item) => item.count), area: true, showMark: false, color: "rgb(99, 102, 241)", areaOpacity: 0.2, valueFormatter: (value) => value.toString(), curve: "monotone" }]}
                  xAxis={[{ data: chartData.map((item) => item.date), scaleType: "time", valueFormatter: (date) => format(new Date(date), "MMM d"), tickLabelStyle: { angle: 45, textAnchor: "start", fontSize: 12 } }]}
                  yAxis={[{ valueFormatter: (value) => Math.round(value).toString() }]}
                  sx={{ ".MuiLineElement-root": { strokeWidth: 2 }, ".MuiAreaElement-root": { fill: "rgb(99, 102, 241)", opacity: 0.2 } }}
                  height={300}
                  margin={{ left: 60, right: 20, top: 20, bottom: 50 }}
                  slotProps={{ legend: { hidden: true } }}
                />
              </Box>
            ) : (
              <Box sx={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Typography color="text.secondary">No trend data available</Typography>
              </Box>
            )}
            {chartData.length > 0 && (
              <Box sx={{ mt: 2, display: "flex", gap: 4, borderTop: "1px solid #eee", pt: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Total Events</Typography>
                  <Typography variant="h6">{chartData.reduce((sum, item) => sum + item.count, 0)}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Daily Average</Typography>
                  <Typography variant="h6">{Math.round(chartData.reduce((sum, item) => sum + item.count, 0) / chartData.length)}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">Peak Day</Typography>
                  <Typography variant="h6">{format(chartData.reduce((max, item) => item.count > max.count ? item : max).date, "MMM d")}</Typography>
                </Box>
              </Box>
            )}
          </Box>
        </CardContent>
      </StatCard>
    );
  };

  const processEntryExitByCategory = () => {
    if (!stats.entry_exit_by_category) return [];
    return Object.entries(stats.entry_exit_by_category).map(([category, counts]) => ({
      category,
      entry: counts.entry || 0,
      exit: counts.exit || 0,
    }));
  };

  const renderEntryExitByCategory = () => (
    <StatCard>
      <CardContent>
        <Typography variant="h6" gutterBottom>Entry/Exit by Category</Typography>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={processEntryExitByCategory()}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="category" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="entry" fill={chartColors.primary.main} />
            <Bar dataKey="exit" fill={chartColors.secondary.main} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </StatCard>
  );

  const PrintSummary = () => {
    const categoryData = processEntryExitByCategory();
    const totalTraffic = categoryData.reduce((acc, curr) => acc + curr.entry + curr.exit, 0);
    const peakHour = Object.entries(stats.hourly_trend || {}).reduce((max, [hour, count]) => (count > max.count ? { hour, count } : max), { hour: "0", count: 0 });
    const formattedPeakTime = formatHour(peakHour.hour);

    return (
      <SummarySection>
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" sx={{ mb: 1, fontWeight: 600, color: "#1e293b" }}>Detailed Analytics Summary</Typography>
          <Typography variant="body2" sx={{ color: "#64748b" }}>Comprehensive breakdown of traffic patterns and category distribution</Typography>
        </Box>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <InsightCard>
              <Typography variant="h6" sx={{ mb: 3, color: "#334155" }}>Traffic Distribution</Typography>
              <Box sx={{ display: "flex", gap: 2, mb: 3 }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>Total Traffic</Typography>
                  <Typography variant="h4" color="primary" sx={{ mb: 1 }}>{totalTraffic.toLocaleString()}</Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>Peak Hour</Typography>
                  <Typography variant="h4" color="primary" sx={{ mb: 1 }}>{formattedPeakTime.time}</Typography>
                  <Typography variant="caption" sx={{ color: "#64748b", display: "block" }}>{formattedPeakTime.date}</Typography>
                  <Typography variant="caption" sx={{ color: "#64748b" }}>{peakHour.count.toLocaleString()} events</Typography>
                </Box>
              </Box>
              <Typography variant="subtitle2" sx={{ mb: 2, color: "#475569" }}>Category Breakdown</Typography>
              {categoryData.map((category) => {
                const percentage = ((category.entry + category.exit) / totalTraffic * 100).toFixed(1);
                return (
                  <Box key={category.category} sx={{ mb: 2, p: 2, borderRadius: "8px", backgroundColor: "#ffffff" }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                      <Typography variant="subtitle2" sx={{ color: "#334155", fontWeight: 600 }}>{category.category}</Typography>
                      <Typography variant="subtitle2" sx={{ color: "#6366f1" }}>{percentage}%</Typography>
                    </Box>
                    <Box sx={{ display: "flex", gap: 3 }}>
                      <StatBox>
                        <ArrowUpward sx={{ color: "#10b981", fontSize: 16 }} />
                        <Typography variant="body2" sx={{ color: "#475569" }}>{category.entry.toLocaleString()} in</Typography>
                      </StatBox>
                      <StatBox>
                        <ArrowDownward sx={{ color: "#ef4444", fontSize: 16 }} />
                        <Typography variant="body2" sx={{ color: "#475569" }}>{category.exit.toLocaleString()} out</Typography>
                      </StatBox>
                    </Box>
                  </Box>
                );
              })}
            </InsightCard>
          </Grid>
          <Grid item xs={12} md={6}>
            <InsightCard>
              <Typography variant="h6" sx={{ mb: 3, color: "#334155" }}>Temporal Analysis</Typography>
              <Box sx={{ display: "flex", gap: 2, mb: 4 }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>Daily Average</Typography>
                  <Typography variant="h4" color="primary" sx={{ mb: 1 }}>{Math.round(totalTraffic / (Object.keys(stats.daily_trend || {}).length || 1)).toLocaleString()}</Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>Weekly Trend</Typography>
                  <Box sx={{ display: "flex", alignItems: "flex-end", gap: 1 }}>
                    <Typography variant="h4" color="primary" sx={{ mb: 1 }}>{((totalTraffic / (Object.keys(stats.daily_trend || {}).length || 1)) * 7).toLocaleString()}</Typography>
                    <Typography variant="caption" sx={{ mb: 1.5, color: "#64748b" }}>/week</Typography>
                  </Box>
                </Box>
              </Box>
              <Typography variant="subtitle2" sx={{ mb: 2, color: "#475569" }}>Daily Distribution</Typography>
              {Object.entries(stats.daily_trend || {}).sort(([dateA], [dateB]) => new Date(dateB) - new Date(dateA)).slice(0, 5).map(([date, count]) => (
                <Box key={date} sx={{ mb: 2, p: 2, borderRadius: "8px", backgroundColor: "#ffffff", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Box>
                    <Typography variant="subtitle2" sx={{ color: "#334155", fontWeight: 600 }}>{format(new Date(date), "EEE, MMM d")}</Typography>
                    <Typography variant="caption" sx={{ color: "#64748b" }}>{count > totalTraffic / Object.keys(stats.daily_trend || {}).length ? "Above average" : "Below average"}</Typography>
                  </Box>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                    <Typography variant="subtitle2" sx={{ color: "#6366f1" }}>{count.toLocaleString()} events</Typography>
                    {count > totalTraffic / Object.keys(stats.daily_trend || {}).length ? <TrendingUp sx={{ color: "#10b981", fontSize: 18 }} /> : <TrendingDown sx={{ color: "#ef4444", fontSize: 18 }} />}
                  </Box>
                </Box>
              ))}
            </InsightCard>
          </Grid>
        </Grid>
      </SummarySection>
    );
  };

  const getPeriodLabel = useCallback((selectedTimeRange) => {
    switch (selectedTimeRange) {
      case "today": return "Yesterday";
      case "week": return "Last Week";
      case "month": return "Last Month";
      case "custom": return "Previous Period";
      default: return "Previous Period";
    }
  }, []);

  return (
    <DashboardContainer>
      <DashboardHeader>
        <Typography className="title">Analytics Dashboard</Typography>
        <Typography className="subtitle">
          Comprehensive overview of your facility's performance metrics
        </Typography>
      </DashboardHeader>

      <ControlsContainer>
        <StyledTimeRangeSelect
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          startAdornment={<CalendarToday sx={{ color: chartColors.text.secondary, mr: 1 }} />}
        >
          <MenuItem value="today">Today</MenuItem>
          <MenuItem value="week">This Week</MenuItem>
          <MenuItem value="month">This Month</MenuItem>
          <MenuItem value="custom">Custom Range</MenuItem>
        </StyledTimeRangeSelect>

        {timeRange === "custom" && (
          <Box display="flex" gap={2}>
            <StyledDatePicker
              type="date"
              value={dateRange.startDate.toISOString().split("T")[0]}
              onChange={(e) => setDateRange({ ...dateRange, startDate: new Date(e.target.value) })}
            />
            <StyledDatePicker
              type="date"
              value={dateRange.endDate.toISOString().split("T")[0]}
              onChange={(e) => setDateRange({ ...dateRange, endDate: new Date(e.target.value) })}
            />
          </Box>
        )}

        <ExportButton
          startIcon={isExporting ? <CircularProgress size={20} sx={{ color: "#FFFFFF" }} /> : <Download />}
          onClick={handleDownloadPdf}
          disabled={isExporting}
        >
          {isExporting ? "Exporting..." : "Export Report"}
        </ExportButton>
      </ControlsContainer>

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress sx={{ color: chartColors.primary.main }} />
        </Box>
      ) : (
        <>
          {renderStatBoxes()}
          <Box mt={4}>
            {renderCharts()}
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>{renderEntryExitByCategory()}</Grid>
              <Grid item xs={12} md={6}>{renderDailyTrend()}</Grid>
              <Grid item xs={12}>{renderHeatmap()}</Grid>
            </Grid>
            <PrintSummary />
          </Box>
        </>
      )}
    </DashboardContainer>
  );
};

export default AnalyticsDashboard;
