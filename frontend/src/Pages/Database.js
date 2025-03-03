import React, { useState, useEffect } from "react";
import "../Styles/Database.css";
import DateTime from "../Serivces/DateTime";
import { parkingService } from "../Serivces/Data";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import "../Styles/datepicker.css";

import {
  IconRefresh,
  IconDownload,
  IconFilter,
  IconCalendarWeek,
  IconSearch,
  IconChevronRight,
  IconChevronLeft,
  IconX,
} from "@tabler/icons-react";
import Pagination from "../Components/Pagination";

function Database() {
  const [data, setData] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);

  const [showFiltersPopup, setShowFiltersPopup] = useState(false);
  const [licensePrefix, setLicensePrefix] = useState([]);
  const [categoryFilter, setCategoryFilter] = useState([]);
  const [colorFilter, setColorFilter] = useState([]);
  const [gateFilter, setGateFilter] = useState([]);

  const licenses = ["MH", "GJ", "AP", "TS", "NL", "TN", "KL", "KA"];
  const [categories, setCategories] = useState([]);
  const [colors, setColors] = useState([]);
  const [gates, setGates] = useState([]);

  // Function to format date to UTC format: "Sat, 01 Mar 2025 13:02:55 UTC"
  const formatToUTC = (date) => {
    if (!date) return null;
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const day = days[date.getUTCDay()];
    const dateNum = String(date.getUTCDate()).padStart(2, "0");
    const month = months[date.getUTCMonth()];
    const year = date.getUTCFullYear();
    const hours = String(date.getUTCHours()).padStart(2, "0");
    const minutes = String(date.getUTCMinutes()).padStart(2, "0");
    const seconds = String(date.getUTCSeconds()).padStart(2, "0");
    return `${day}, ${dateNum} ${month} ${year} ${hours}:${minutes}:${seconds} UTC`;
  };

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const formattedStartDate = formatToUTC(startDate);
      const formattedEndDate = formatToUTC(endDate);

      // Log the formatted timestamps being sent to the backend
      console.log("Sending start_date:", formattedStartDate);
      console.log("Sending end_date:", formattedEndDate);

      const result = await parkingService.getParkingData(
        currentPage,
        itemsPerPage,
        searchTerm,
        formattedStartDate,
        formattedEndDate,
        licensePrefix.join(","),
        categoryFilter.join(","),
        colorFilter.join(","),
        gateFilter.join(",")
      );
      setData(result.data);
      setTotalPages(result.total_pages);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, [
    currentPage,
    itemsPerPage,
    searchTerm,
    startDate,
    endDate,
    licensePrefix,
    categoryFilter,
    colorFilter,
    gateFilter,
  ]);

  const handleResetFilters = () => {
    setLicensePrefix([]);
    setCategoryFilter([]);
    setColorFilter([]);
    setGateFilter([]);
  };

  const handleDateReset = () => {
    setStartDate(null);
    setEndDate(null);
  };

  const handleCalendarClick = (e) => {
    e.preventDefault();
    setIsCalendarOpen(!isCalendarOpen);
  };

  const handleDateChange = (dates) => {
    const [start, end] = dates;
    setStartDate(start);
    setEndDate(end);
    if (end) {
      setIsCalendarOpen(false);
    }
  };

  useEffect(() => {
    const fetchFilterOptions = async () => {
      try {
        const [cats, cols, gts] = await Promise.all([
          parkingService.getCategories(),
          parkingService.getColors(),
          parkingService.getGates(),
        ]);
        setCategories(cats);
        setColors(cols);
        setGates(gts);
      } catch (error) {
        console.error("Error fetching filter options:", error);
      }
    };

    fetchFilterOptions();
  }, []);

  const handleRefresh = () => {
    fetchData();
  };

  const formatDuration = (seconds) => {
    if (!seconds || seconds < 0) return "N/A";

    const days = Math.floor(seconds / (24 * 60 * 60));
    const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60));
    const minutes = Math.floor((seconds % (60 * 60)) / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    const parts = [];
    if (days > 0) parts.push(`${days}d`);
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (remainingSeconds > 0 || parts.length === 0) parts.push(`${remainingSeconds}s`);
    return parts.join(" ");
  };

  return (
    <div className="main">
      <div className="heading">
        <div className="title">
          <h1>Search Vehicle by License Plate</h1>
        </div>
        <DateTime />
      </div>

      <div className="search-container">
        <div className="search-input-wrapper">
          <IconSearch className="search-icon" />
          <input
            type="text"
            placeholder="Search vehicles..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <button className="action-button refresh-button">
          <IconRefresh
            className="button-icon"
            onClick={handleRefresh}
            disabled={isLoading}
          />
        </button>


        <div className="calendar-wrapper">
          <button
            className="action-button calendar-button"
            onClick={handleCalendarClick}
          >
            <IconCalendarWeek className="button-icon" />
            <span className="date-range-text">
              {startDate && endDate
                ? `${startDate.toLocaleDateString()} ${startDate.toLocaleTimeString()} - ${endDate.toLocaleDateString()} ${endDate.toLocaleTimeString()}`
                : ""}
            </span>
          </button>

          {isCalendarOpen && (
            <div className="calendar-popup">
              <div className="quick-select-container">
                <button
                  className="quick-select-button"
                  onClick={() => {
                    const end = new Date();
                    const start = new Date();
                    start.setHours(0, 0, 0, 0);
                    setStartDate(start);
                    setEndDate(end);
                  }}
                >
                  Today
                </button>
                <button
                  className="quick-select-button"
                  onClick={() => {
                    const end = new Date();
                    const start = new Date();
                    start.setDate(start.getDate() - 1);
                    start.setHours(0, 0, 0, 0);
                    setStartDate(start);
                    setEndDate(end);
                  }}
                >
                  Last 24 Hours
                </button>
                <button
                  className="quick-select-button"
                  onClick={() => {
                    const end = new Date();
                    const start = new Date();
                    start.setDate(start.getDate() - 7);
                    setStartDate(start);
                    setEndDate(end);
                  }}
                >
                  Last 7 Days
                </button>
                <button
                  className="quick-select-button"
                  onClick={() => {
                    const end = new Date();
                    const start = new Date();
                    start.setDate(start.getDate() - 30);
                    setStartDate(start);
                    setEndDate(end);
                  }}
                >
                  Last 30 Days
                </button>
              </div>

              <div className="datepickers-container">
                <div className="datepicker-wrapper">
                  <label className="datepicker-label">Start Date & Time</label>
                  <DatePicker
                    selected={startDate}
                    onChange={(date) => setStartDate(date)}
                    showTimeSelect
                    timeIntervals={1}
                    timeFormat="HH:mm:ss"
                    dateFormat="MMM d, yyyy HH:mm:ss"
                    maxDate={new Date()}
                    placeholderText="Select start date & time"
                    calendarClassName="custom-calendar"
                    timeCaption="Time"
                    showSeconds
                  />
                </div>
                <div className="datepicker-wrapper">
                  <label className="datepicker-label">End Date & Time</label>
                  <DatePicker
                    selected={endDate}
                    onChange={(date) => setEndDate(date)}
                    showTimeSelect
                    timeIntervals={1}
                    timeFormat="HH:mm:ss"
                    dateFormat="MMM d, yyyy HH:mm:ss"
                    maxDate={new Date()}
                    placeholderText="Select end date & time"
                    calendarClassName="custom-calendar"
                    timeCaption="Time"
                    showSeconds
                    minDate={startDate}
                  />
                </div>
              </div>

              <div className="datepicker-buttons">
                <button
                  className="datepicker-button button-clear"
                  onClick={() => {
                    setStartDate(null);
                    setEndDate(null);
                    setIsCalendarOpen(false);
                  }}
                >
                  Clear
                </button>
                <button
                  className="datepicker-button button-apply"
                  onClick={() => {
                    if (startDate && endDate && startDate > endDate) {
                      alert("Start date cannot be after end date");
                      return;
                    }
                    setIsCalendarOpen(false);
                  }}
                >
                  Apply
                </button>
              </div>
            </div>
          )}
        </div>

        <button
          className="action-button filters-button"
          onClick={() => setShowFiltersPopup(true)}
        >
          <IconFilter className="button-icon" />
          <span className="button-text">Filters</span>
        </button>
      </div>

      {showFiltersPopup && (
        <div className="filters-popup">
          <div className="filters-content">
            <div className="filter-sections">
              <div className="filter-group">
                <label>License Plate</label>
                <div className="checkbox-group">
                  {licenses.map((license) => (
                    <label key={license} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={licensePrefix.includes(license)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setLicensePrefix([...licensePrefix, license]);
                          } else {
                            setLicensePrefix(
                              licensePrefix.filter((l) => l !== license)
                            );
                          }
                        }}
                      />
                      <span>{license}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="filter-group">
                <label>Category</label>
                <div className="checkbox-group">
                  {categories.map((category) => (
                    <label key={category} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={categoryFilter.includes(category)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setCategoryFilter([...categoryFilter, category]);
                          } else {
                            setCategoryFilter(
                              categoryFilter.filter((c) => c !== category)
                            );
                          }
                        }}
                      />
                      <span>{category}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="filter-group">
                <label>Color</label>
                <div className="checkbox-group">
                  {colors.map((color) => (
                    <label key={color} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={colorFilter.includes(color)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setColorFilter([...colorFilter, color]);
                          } else {
                            setColorFilter(
                              colorFilter.filter((c) => c !== color)
                            );
                          }
                        }}
                      />
                      <span>{color}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="filter-group">
                <label>Gate</label>
                <div className="checkbox-group">
                  {gates.map((gate) => (
                    <label key={gate} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={gateFilter.includes(gate)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setGateFilter([...gateFilter, gate]);
                          } else {
                            setGateFilter(gateFilter.filter((g) => g !== gate));
                          }
                        }}
                      />
                      <span>{gate}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="filter-buttons">
              <button
                className="apply-button"
                onClick={() => setShowFiltersPopup(false)}
              >
                Apply Filters
              </button>
              <button
                className="clear-button"
                onClick={() => {
                  handleResetFilters();
                  setShowFiltersPopup(false);
                }}
              >
                Clear All
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="options">
        <div className="page-size">
          Results Per Page
          <select
            value={itemsPerPage}
            onChange={(e) => setItemsPerPage(Number(e.target.value))}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
        />
      </div>

      <div className="table-container">
        <table className="vehicle-table">
          <thead>
            <tr>
              <th>License Plate</th>
              <th>Category</th>
              <th>Colour</th>
              <th>Entry</th>
              <th>Entry Gate</th>
              <th>Exit</th>
              <th>Exit Gate</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan="10">Loading...</td>
              </tr>
            ) : (
              data.map((item) => (
                <tr key={item.insertion_id}>
                  <td>{item.license_plate}</td>
                  <td>{item.category}</td>
                  <td>{item.color}</td>
                  <td>{item.entry_time || "N/A"}</td>
                  <td>{item.entry_gate || "N/A"}</td>
                  <td>
                    {item.exit_time && item.exit_time !== "Not Exited"
                      ? item.exit_time
                      : "Not exited"}
                  </td>
                  <td>{item.exit_gate || "N/A"}</td>
                  <td>{formatDuration(item.duration)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Database;
