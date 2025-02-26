import React, { useEffect, useState } from 'react'
import '../Styles/Dashboard.css';
import { parkingService } from '../Serivces/Data';
import Card  from '../Components/Cards';

import { IconCar,IconLogin2,IconLogout } from '@tabler/icons-react';


function DateTime(){
    const [currentDateTime,setcurrentDateTime] = useState(new Date());

    useEffect(()=>{
        const timer = setInterval(()=>{
            setcurrentDateTime(new Date());
        },1000);

        return () => clearInterval(timer);
    },[]);


  const formatDate = (date) => {
    const day = date.getDate();
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = monthNames[date.getMonth()];
    const year = date.getFullYear();

    // Add suffix to day (st, nd, rd, th)
    const suffix = (day % 10 === 1 && day !== 11) ? "st" :
                   (day % 10 === 2 && day !== 12) ? "nd" :
                   (day % 10 === 3 && day !== 13) ? "rd" : "th";

    return `${day}${suffix} ${month} ${year}`;
  };

  const formatTime = (date) => {
    let hours = date.getHours();
    const minutes = date.getMinutes();
    const ampm = hours >= 12 ? "Pm" : "Am";
    hours = hours % 12 || 12; // Convert 0 to 12 for 12-hour format
    const formattedMinutes = minutes < 10 ? `0${minutes}` : minutes;

    return `${hours}:${formattedMinutes} ${ampm}`;
  };

  return (
    <div className="date-time">
      <span>{formatDate(currentDateTime)}</span>
      <span> &nbsp;| &nbsp;</span>
      <span>{formatTime(currentDateTime)}</span>
    </div>
  );
}


function Dashboard() {
  const [parkingData, setParkingData] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [enteredCount, setEnteredCount] = useState(0);
  const [exitedCount, setExitedCount] = useState(0);

  // Updated stats
  const [stats, setStats] = useState({
    mostCommonVehicle: '',
    busiestHour: '',
    busiestGate: '',
    busiestDay: '',
    popularColor: ''
  });

  const [trends, setTrends] = useState({
    entry_trend: "0%",
    exit_trend: "0%",
    total_trend: "0%"
  });

  const fetchData = async (page, search = '') => {
    setIsLoading(true);
    try {
      const result = await parkingService.getParkingDataDashboard(page, 10, search);
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

  useEffect(() => {
    const fetchStatistics = async () => {
      try {
        const entriesRes = await parkingService.getTodayEntries();
        const exitsRes = await parkingService.getTodayExits();
        
        setEnteredCount(entriesRes.count);
        setExitedCount(exitsRes.count);
      } catch (error) {
        console.error('Error fetching statistics:', error);
      }
    };
    
    fetchStatistics();
  }, []);

  // Updated stats calculation
  const calculateStats = (data) => {
    const categories = {};
    const hourCounts = {};
    const gates = {};
    const colors = {};
    const dayCounts = {};

    data.forEach(item => {
      // Vehicle category analysis (filter pedestrians)
      if (item.category.toLowerCase() !== 'pedestrian') {
        categories[item.category] = (categories[item.category] || 0) + 1;
      }
      
      // Gate activity analysis
      gates[item.gate] = (gates[item.gate] || 0) + 1;
      
      // Color popularity
      colors[item.color] = (colors[item.color] || 0) + 1;
      
      // New: Day of week analysis
      const day = new Date(item.timestamp).getDay();
      dayCounts[day] = (dayCounts[day] || 0) + 1;

      // Hour analysis
      const hour = new Date(item.timestamp).getHours();
      hourCounts[hour] = (hourCounts[hour] || 0) + 1;
    });

    // Process most common vehicle (excluding pedestrians)
    const vehicleEntries = Object.entries(categories).sort((a,b) => b[1] - a[1]);
    const mostCommonVehicle = vehicleEntries[0]?.[0] || 'N/A';

    // New: Convert day number to name
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const busiestDay = Object.entries(dayCounts).sort((a,b) => b[1] - a[1])[0]?.[0] || 'N/A';

    setStats({
      mostCommonVehicle,
      busiestHour: Object.entries(hourCounts).sort((a,b) => b[1] - a[1])[0]?.[0] || 'N/A',
      busiestGate: Object.entries(gates).sort((a,b) => b[1] - a[1])[0]?.[0] || 'N/A',
      busiestDay: days[busiestDay] || 'N/A',
      popularColor: Object.entries(colors).sort((a,b) => b[1] - a[1])[0]?.[0] || 'N/A'
    });
  };

  useEffect(() => {
    calculateStats(parkingData);
  }, [parkingData, enteredCount, exitedCount]);

  // Add new useEffect for fetching trends
  useEffect(() => {
    const fetchTrends = async () => {
      try {
        const response = await parkingService.getTrends();
        setTrends(response);
      } catch (error) {
        console.error('Error fetching trends:', error);
      }
    };
    
    fetchTrends();
  }, []);

  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
    setCurrentPage(1);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  return (
    <div className='main'>
      <div className='heading'>
        <div className='title'>
          <h1>Dashboard</h1>
          <p className='subtitle'>Real-time parking management overview</p>
        </div>
        <DateTime/>
      </div>

      <div className='dashboard-stats'>
        <div className='cards'>
          <Card 
            title="Vehicles Entered" 
            count={enteredCount} 
            icon={<IconLogin2/>} 
            trend={trends.entry_trend}
            variant="entered"
          />
          <Card 
            title="Vehicles Exited" 
            count={exitedCount} 
            icon={<IconLogout/>} 
            trend={trends.exit_trend}
            variant="exited"
          />
        </div>

        <div className='quick-insights'>
          <h3>Operational Insights</h3>
          <div className='insights-grid'>
            <div className='insight-card'>
              <span className='insight-label'>Peak Traffic Day</span>
              <span className='insight-value'>{stats.busiestDay}</span>
            </div>
           
            <div className='insight-card'>
              <span className='insight-label'>Peak Hour</span>
              <span className='insight-value'>{stats.busiestHour}:00</span>
            </div>
            <div className='insight-card'>
              <span className='insight-label'>Common Vehicle Type</span>
              <span className='insight-value'>{stats.mostCommonVehicle}</span>
            </div>
            
          </div>
        </div>
      </div>

      <div className='data'>
        <div className="vehicle-container">
          <div className="header">
            <h2>Recent Vehicle Activity</h2>
            <div className="header-actions">
              <a href="#" className="view-all">View all vehicles</a>
            </div>
          </div>
          
          <div className="table-container">
            <table className="vehicle-table">
              <thead>
                <tr>
                  <th>Insertion Id</th>
                  <th>License Plate</th>
                  <th>Category</th>
                  <th>Colour</th>
                  <th>Timestamp</th>
                  <th>Gate</th>
                  <th>Zone</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
              {parkingData.map((row, index) => (
                  <tr
                    key={index}

                  >
                    <td>{row.insertion_id}</td>
                    <td>{row.license_plate}</td>
                    <td>{row.category}</td>
                    <td>{row.color}</td>
                    <td>{row.timestamp}</td>
                    <td>{row.gate}</td>
                    <td>{row.zone}</td>
                    <td>{row.description}</td>
                  </tr>
                ))}

              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard