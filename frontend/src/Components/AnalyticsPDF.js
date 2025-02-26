import React from "react";
import {
  Typography,
  Grid,
  Box,
} from "@mui/material";
import {
  LineChart,
  BarChart,
  PieChart,
  Line,
  Bar,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
} from "recharts";
import { format } from "date-fns";
import {
  TrendingUp,
  CalendarToday,
  LocalShipping,
  CompareArrows,
} from "@mui/icons-material";

const printStyles = {
  container: {
    padding: "30px",
    backgroundColor: "#FFFFFF",
    fontFamily: "'Arial', sans-serif",
  },
  header: {
    borderBottom: "2px solid #4F46E5",
    paddingBottom: "20px",
    marginBottom: "30px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-end",
  },
  section: {
    marginBottom: "40px",
    padding: "25px",
    backgroundColor: "#F8FAFF",
    borderRadius: "12px",
    border: "1px solid #E2E8F0",
  },
  insightBox: {
    padding: "20px",
    borderRadius: "8px",
    background: "linear-gradient(135deg, #FFFFFF 0%, #F8FAFF 100%)",
    border: "1px solid #E2E8F0",
    marginBottom: "20px",
  },
};

const AnalyticsReportPDF = React.forwardRef((props, ref) => {
  const { stats, durationStats, percentageChanges, timeRange, dateRange, exportTime } = props;

  const categoryColors = ["#8884d8", "#82ca9d", "#ffc658", "#ff8042", "#0088fe", "#00c49f"];

  if (!stats || Object.keys(stats).length === 0) {
    return <Typography>No data available for the selected period.</Typography>;
  }

  // Helper functions
  const formatDuration = (seconds) => {
    if (!seconds) return "0h";
    const hours = (seconds / 3600).toFixed(2);
    return `${hours}h`;
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

  const processEntryExitByCategory = () => {
    if (!stats.entry_exit_by_category) return [];
    return Object.entries(stats.entry_exit_by_category).map(([category, counts]) => ({
      category,
      entry: counts.entry || 0,
      exit: counts.exit || 0,
    }));
  };

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
      return { date: "Invalid Date", time: "Invalid Time" };
    }
  };

  // Section Render Functions
  const renderHeader = () => (
    <div style={printStyles.header}>
      <div>
        <Typography variant="h2" style={{ fontFamily: "'Arial', sans-serif", color: "#1E293B", marginBottom: "8px" }}>
          Facility Analytics Report
        </Typography>
        <div style={{ display: "flex", gap: "20px" }}>
          <Typography variant="body2" style={{ color: "#64748B" }}>
            Period: {timeRange === "custom"
              ? `${new Date(dateRange.startDate).toLocaleDateString()} - ${new Date(dateRange.endDate).toLocaleDateString()}`
              : timeRange.charAt(0).toUpperCase() + timeRange.slice(1)}
          </Typography>
          <Typography variant="body2" style={{ color: "#64748B" }}>
            Generated: {new Date(exportTime).toLocaleString()}
          </Typography>
        </div>
      </div>
      <div style={{ background: "linear-gradient(135deg, #4F46E5 0%, #6366F1 100%)", padding: "12px 20px", borderRadius: "8px", color: "white" }}>
        <Typography variant="h6">Total Events</Typography>
        <Typography variant="h3" style={{ fontFamily: "'Arial', sans-serif" }}>
          {stats.total_events?.toLocaleString() || 0}
        </Typography>
      </div>
    </div>
  );

  const renderQuickInsights = () => {
    const insights = {
      peakHour: Object.entries(stats.hourly_trend || {}).reduce((a, b) => (a[1] > b[1] ? a : b), ["", 0])[0],
      mostActiveDay: Object.entries(stats.daily_trend || {}).reduce((a, b) => (a[1] > b[1] ? a : b), ["", 0])[0],
      busiestCategory: Object.entries(stats.category_counts || {}).reduce((a, b) => (a[1] > b[1] ? a : b), ["", 0])[0],
      entryExitRatio: stats.entry_exit_counts ? (stats.entry_exit_counts.entry / stats.entry_exit_counts.exit).toFixed(1) : 0,
    };

    return (
      <div style={{ ...printStyles.section, backgroundColor: "#4F46E510" }}>
        <Typography variant="h4" style={{ fontFamily: "'Arial', sans-serif", color: "#1E293B", marginBottom: "25px" }}>
          Key Insights
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={6} md={3}>
            <div style={printStyles.insightBox}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ background: "#4F46E520", borderRadius: "8px", padding: "10px" }}>
                  <TrendingUp style={{ color: "#4F46E5" }} />
                </div>
                <div>
                  <Typography variant="body2" style={{ color: "#64748B" }}>Peak Hour</Typography>
                  <Typography variant="h6" style={{ color: "#1E293B" }}>{formatHour(insights.peakHour).time}</Typography>
                </div>
              </div>
            </div>
          </Grid>
          <Grid item xs={6} md={3}>
            <div style={printStyles.insightBox}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ background: "#10B98120", borderRadius: "8px", padding: "10px" }}>
                  <CalendarToday style={{ color: "#10B981" }} />
                </div>
                <div>
                  <Typography variant="body2" style={{ color: "#64748B" }}>Most Active Day</Typography>
                  <Typography variant="h6" style={{ color: "#1E293B" }}>
                    {format(new Date(insights.mostActiveDay), "EEE, MMM d")}
                  </Typography>
                </div>
              </div>
            </div>
          </Grid>
          <Grid item xs={6} md={3}>
            <div style={printStyles.insightBox}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ background: "#EF444420", borderRadius: "8px", padding: "10px" }}>
                  <LocalShipping style={{ color: "#EF4444" }} />
                </div>
                <div>
                  <Typography variant="body2" style={{ color: "#64748B" }}>Busiest Category</Typography>
                  <Typography variant="h6" style={{ color: "#1E293B" }}>{insights.busiestCategory}</Typography>
                </div>
              </div>
            </div>
          </Grid>
          <Grid item xs={6} md={3}>
            <div style={printStyles.insightBox}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ background: "#F59E0B20", borderRadius: "8px", padding: "10px" }}>
                  <CompareArrows style={{ color: "#F59E0B" }} />
                </div>
                <div>
                  <Typography variant="body2" style={{ color: "#64748B" }}>Entry/Exit Ratio</Typography>
                  <Typography variant="h6" style={{ color: "#1E293B" }}>{insights.entryExitRatio}:1</Typography>
                </div>
              </div>
            </div>
          </Grid>
        </Grid>
      </div>
    );
  };

  const renderPerformanceOverview = () => {
    const mostUsedGate = stats.gate_usage
      ? Object.entries(stats.gate_usage).reduce((prev, curr) => (curr[1] > prev[1] ? curr : prev), ["N/A", 0])[0]
      : "N/A";

    return (
      <div style={printStyles.section}>
        <Typography variant="h4" style={{ fontFamily: "'Arial', sans-serif", color: "#1E293B", marginBottom: "25px" }}>
          Performance Overview
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={4}>
            <div style={{ textAlign: "center" }}>
              <Typography variant="h6" style={{ color: "#64748B" }}>Total Events</Typography>
              <Typography variant="h3" style={{ color: "#1E293B" }}>{stats.total_events?.toLocaleString() || 0}</Typography>
            </div>
          </Grid>
          <Grid item xs={4}>
            <div style={{ textAlign: "center" }}>
              <Typography variant="h6" style={{ color: "#64748B" }}>Average Duration</Typography>
              <Typography variant="h3" style={{ color: "#1E293B" }}>{formatDuration(durationStats.average_duration)}</Typography>
            </div>
          </Grid>
          <Grid item xs={4}>
            <div style={{ textAlign: "center" }}>
              <Typography variant="h6" style={{ color: "#64748B" }}>Most Used Gate</Typography>
              <Typography variant="h3" style={{ color: "#1E293B" }}>{mostUsedGate}</Typography>
            </div>
          </Grid>
        </Grid>
      </div>
    );
  };

  const renderCharts = () => {
    const chartData = {
      hourlyTrend: Object.entries(stats.hourly_trend || {}).map(([hour, count]) => ({
        hour: `${parseInt(hour)}:00`,
        count,
      })),
      categories: Object.entries(stats.category_counts || {}).map(([name, value]) => ({
        name,
        value,
      })),
      entryExit: Object.entries(stats.entry_exit_by_category || {}).map(([category, counts]) => ({
        category,
        entry: counts.entry || 0,
        exit: counts.exit || 0,
      })),
    };

    return (
      <div style={printStyles.section}>
        <Typography variant="h4" style={{ fontFamily: "'Arial', sans-serif", color: "#1E293B", marginBottom: "25px" }}>
          Detailed Analysis
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <div style={{ padding: "10px" }}>
              <Typography variant="h5" gutterBottom>Hourly Activity Trend</Typography>
              <div style={{ width: "100%", height: "300px" }}>
                <LineChart width={500} height={300} data={chartData.hourlyTrend} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="hour" stroke="#64748B" />
                  <YAxis stroke="#64748B" />
                  <Line type="monotone" dataKey="count" stroke="#4F46E5" strokeWidth={2} dot={false} />
                </LineChart>
              </div>
            </div>
          </Grid>
          <Grid item xs={12} md={6}>
            <div style={{ padding: "10px" }}>
              <Typography variant="h5" gutterBottom>Vehicle Categories</Typography>
              <div style={{ width: "100%", height: "300px" }}>
                <PieChart width={500} height={300}>
                  <Pie
                    data={chartData.categories}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {chartData.categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={categoryColors[index % categoryColors.length]} />
                    ))}
                  </Pie>
                  <Legend layout="vertical" align="right" verticalAlign="middle" />
                </PieChart>
              </div>
            </div>
          </Grid>
          <Grid item xs={12}>
            <div style={{ padding: "10px" }}>
              <Typography variant="h5" gutterBottom>Entry/Exit by Category</Typography>
              <div style={{ width: "100%", height: "400px" }}>
                <BarChart width={700} height={400} data={chartData.entryExit} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="category" stroke="#64748B" />
                  <YAxis stroke="#64748B" />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="entry" fill="#4F46E5" name="Entry Events" />
                  <Bar dataKey="exit" fill="#10B981" name="Exit Events" />
                </BarChart>
              </div>
            </div>
          </Grid>
        </Grid>
      </div>
    );
  };

  const renderHeatmapForPDF = () => {
    const heatmapData = processHeatmapData();
    if (heatmapData.length === 0) {
      return <Typography>No heatmap data available</Typography>;
    }

    return (
      <div style={printStyles.section}>
        <Typography variant="h4" style={{ fontFamily: "'Arial', sans-serif", color: "#1E293B", marginBottom: "25px" }}>
          Peak Times Heatmap
        </Typography>
        <div style={{ display: "grid", gridTemplateColumns: "80px repeat(24, 1fr)", gap: "2px" }}>
          <div />
          {Array.from({ length: 24 }, (_, i) => (
            <Typography key={i} style={{ textAlign: "center", fontSize: "12px", color: "#666666" }}>
              {i}:00
            </Typography>
          ))}
          {heatmapData.map((dayData) => (
            <React.Fragment key={dayData.day}>
              <Typography style={{ fontSize: "13px", color: "#333333", fontWeight: 500 }}>{dayData.day}</Typography>
              {dayData.hours.map((hour, hourIndex) => (
                <div
                  key={hourIndex}
                  style={{
                    backgroundColor: hour.intensity === 0 ? "#f5f5f5" : `rgba(99, 102, 241, ${hour.intensity})`,
                    height: "32px",
                    borderRadius: "4px",
                  }}
                />
              ))}
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  };

  const renderSummaryForPDF = () => {
    const categoryData = processEntryExitByCategory();
    const totalTraffic = categoryData.reduce((acc, curr) => acc + curr.entry + curr.exit, 0);
    const peakHour = Object.entries(stats.hourly_trend || {}).reduce(
      (max, [hour, count]) => (count > max.count ? { hour, count } : max),
      { hour: "0", count: 0 }
    );
    const formattedPeakTime = formatHour(peakHour.hour);

    return (
      <div style={printStyles.section}>
        <Typography variant="h4" style={{ fontFamily: "'Arial', sans-serif", color: "#1E293B", marginBottom: "25px" }}>
          Detailed Analytics Summary
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={6}>
            <Typography variant="h6" style={{ color: "#334155", marginBottom: "20px" }}>Traffic Distribution</Typography>
            <div style={{ marginBottom: "20px" }}>
              <Typography variant="subtitle2" style={{ color: "#64748B" }}>Total Traffic</Typography>
              <Typography variant="h4" style={{ color: "#6366f1" }}>{totalTraffic.toLocaleString()}</Typography>
            </div>
            <div style={{ marginBottom: "20px" }}>
              <Typography variant="subtitle2" style={{ color: "#64748B" }}>Peak Hour</Typography>
              <Typography variant="h4" style={{ color: "#6366f1" }}>{formattedPeakTime.time}</Typography>
              <Typography variant="caption" style={{ color: "#64748B" }}>{formattedPeakTime.date} • {peakHour.count.toLocaleString()} events</Typography>
            </div>
            {categoryData.map((category) => (
              <div key={category.category} style={{ marginBottom: "15px", padding: "10px", backgroundColor: "#ffffff", borderRadius: "8px" }}>
                <Typography variant="subtitle2" style={{ color: "#334155", fontWeight: 600 }}>{category.category}</Typography>
                <Typography variant="body2" style={{ color: "#475569" }}>
                  Entry: {category.entry.toLocaleString()} • Exit: {category.exit.toLocaleString()}
                </Typography>
              </div>
            ))}
          </Grid>
          <Grid item xs={6}>
            <Typography variant="h6" style={{ color: "#334155", marginBottom: "20px" }}>Temporal Analysis</Typography>
            <div style={{ marginBottom: "20px" }}>
              <Typography variant="subtitle2" style={{ color: "#64748B" }}>Daily Average</Typography>
              <Typography variant="h4" style={{ color: "#6366f1" }}>
                {Math.round(totalTraffic / (Object.keys(stats.daily_trend || {}).length || 1)).toLocaleString()}
              </Typography>
            </div>
            {Object.entries(stats.daily_trend || {})
              .sort(([dateA], [dateB]) => new Date(dateB) - new Date(dateA))
              .slice(0, 5)
              .map(([date, count]) => (
                <div key={date} style={{ marginBottom: "15px", padding: "10px", backgroundColor: "#ffffff", borderRadius: "8px" }}>
                  <Typography variant="subtitle2" style={{ color: "#334155", fontWeight: 600 }}>
                    {format(new Date(date), "EEE, MMM d")}
                  </Typography>
                  <Typography variant="body2" style={{ color: "#475569" }}>{count.toLocaleString()} events</Typography>
                </div>
              ))}
          </Grid>
        </Grid>
      </div>
    );
  };

  return (
    <div ref={ref} style={{ ...printStyles.container, width: "794px" /* A4 width at 96dpi */ }}>
      {renderHeader()}
      {renderQuickInsights()}
      {renderPerformanceOverview()}
      {renderCharts()}
      {renderHeatmapForPDF()}
      {renderSummaryForPDF()}
      <div style={{ marginTop: "40px", paddingTop: "20px", borderTop: "1px solid #E2E8F0", textAlign: "center", color: "#64748B" }}>
        <Typography variant="body2">Generated by Facility Analytics System • {new Date().toLocaleDateString()}</Typography>
      </div>
    </div>
  );
});

export default AnalyticsReportPDF;