import React, { useState, useEffect } from 'react';
import { parkingService } from '../Serivces/Data';
// DateTime Component
const DateTime = () => {
  const [currentDateTime, setCurrentDateTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentDateTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatDate = (date) => {
    const day = date.getDate();
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = monthNames[date.getMonth()];
    const year = date.getFullYear();
    const suffix = (day % 10 === 1 && day !== 11) ? "st" :
                  (day % 10 === 2 && day !== 12) ? "nd" :
                  (day % 10 === 3 && day !== 13) ? "rd" : "th";
    return `${day}${suffix} ${month} ${year}`;
  };

  const formatTime = (date) => {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;
    const formattedMinutes = minutes < 10 ? `0${minutes}` : minutes;
    return `${hours}:${formattedMinutes} ${ampm}`;
  };

  return (
    <div className="datetime-display">
      <span className="date">{formatDate(currentDateTime)}</span>
      <span className="separator"> | </span>
      <span className="time">{formatTime(currentDateTime)}</span>
    </div>
  );
};

// Main Dashboard Component
const ParkingDashboard = () => {
  const [parkingData, setParkingData] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const fetchData = async (page, search = '') => {
    setIsLoading(true);
    try {
      const result = await parkingService.getParkingData(page, 10, search);
      const sortedData = result.data.sort(
        (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
      );
      setParkingData(sortedData);
      setTotalPages(result.total_pages);
    } catch (error) {
      console.error('Error in component:', error);
      // Handle error appropriately in the UI
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchData(currentPage, searchTerm);
  }, [currentPage, searchTerm]);

  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  return (
    <div className="dashboard-container">
      {/* Header Section */}
      <header className="dashboard-header">
        <h1>Parking Dashboard</h1>
        <DateTime />
      </header>

      {/* Search Section */}
      <div className="search-section">
        <input
          type="text"
          placeholder="Search records..."
          value={searchTerm}
          onChange={handleSearch}
          className="search-input"
        />
      </div>

      {/* Data Display Section */}
      <main className="dashboard-content">
        {isLoading ? (
          <div className="loading-indicator">Loading...</div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>License Plate</th>
                  <th>Category</th>
                  <th>Color</th>
                  <th>Gate</th>
                  <th>Zone</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {parkingData.map((record, index) => (
                  <tr key={index}>
                    <td>{record.insertion_id}</td>
                    <td>{record.license_plate}</td>
                    <td>{record.category}</td>
                    <td>{record.color}</td>
                    <td>{record.gate}</td>
                    <td>{record.zone}</td>
                    <td>{record.timestamp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        <div className="pagination-controls">
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="pagination-button"
          >
            Previous
          </button>
          
          <span className="page-indicator">
            Page {currentPage} of {totalPages}
          </span>

          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="pagination-button"
          >
            Next
          </button>
        </div>
      </main>
    </div>
  );
};

export default ParkingDashboard;