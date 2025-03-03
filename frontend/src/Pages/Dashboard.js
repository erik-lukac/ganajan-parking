import React, { useEffect, useState } from 'react';
import '../Styles/Dashboard.css';
import { parkingService } from '../Serivces/Data';
import Card from '../Components/Cards';
import { IconCar, IconLogin2, IconLogout } from '@tabler/icons-react';
import DateTime from '../Serivces/DateTime';
import { useNavigate } from 'react-router-dom';

function Dashboard() {
    const [parkingData, setParkingData] = useState([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [searchTerm, setSearchTerm] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [enteredCount, setEnteredCount] = useState(0);
    const [exitedCount, setExitedCount] = useState(0);

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

    const navigate = useNavigate();

    const fetchData = async (page, search = '') => {
        setIsLoading(true);
        try {
            const result = await parkingService.getParkingDataDashboard(page, 10, search);
            const dataArray = Array.isArray(result) ? result : (result.data || []);

            if (!dataArray.length) {
                console.warn('Received empty data array');
                setParkingData([]);
                setTotalPages(0);
                return;
            }

            const sortedData = dataArray.sort((a, b) => {
                const dateA = new Date(a.timestamp);
                const dateB = new Date(b.timestamp);
                return dateB - dateA;
            });
            setParkingData(sortedData);
            setTotalPages(result.total_pages || 1);
        } catch (error) {
            console.error('Error in component:', error);
            setParkingData([]);
            setTotalPages(0);
        }
        setIsLoading(false);
    };

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

    // Combined fetch function for periodic refresh
    const fetchAllData = async () => {
        await fetchData(1, ''); // Fetch recent vehicle activity (page 1, no search)
        await fetchStatistics(); // Fetch stats
    };

    // Initial fetch on mount and when currentPage/searchTerm changes
    useEffect(() => {
        fetchData(currentPage, searchTerm);
    }, [currentPage, searchTerm]);

    // Periodic refresh every 10 seconds when no search term
    useEffect(() => {
        if (searchTerm === '') {
            fetchAllData(); // Initial fetch on mount
            const interval = setInterval(() => {
                fetchAllData();
            }, 5000); // 10 seconds
            return () => clearInterval(interval);
        }
    }, [searchTerm]);

    // Initial stats fetch on mount
    useEffect(() => {
        fetchStatistics();
    }, []);

    const calculateStats = (data) => {
        const categories = {};
        const hourCounts = {};
        const gates = {};
        const colors = {};
        const dayCounts = {};

        data.forEach(item => {
            if (item.category.toLowerCase() !== 'pedestrian') {
                categories[item.category] = (categories[item.category] || 0) + 1;
            }
            gates[item.gate] = (gates[item.gate] || 0) + 1;
            colors[item.color] = (colors[item.color] || 0) + 1;
            const day = new Date(item.timestamp).getDay();
            dayCounts[day] = (dayCounts[day] || 0) + 1;
            const hour = new Date(item.timestamp).getHours();
            hourCounts[hour] = (hourCounts[hour] || 0) + 1;
        });

        const vehicleEntries = Object.entries(categories).sort((a, b) => b[1] - a[1]);
        const mostCommonVehicle = vehicleEntries[0]?.[0] || 'N/A';
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const busiestDay = Object.entries(dayCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A';

        setStats({
            mostCommonVehicle,
            busiestHour: Object.entries(hourCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A',
            busiestGate: Object.entries(gates).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A',
            busiestDay: days[busiestDay] || 'N/A',
            popularColor: Object.entries(colors).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'
        });
    };

    useEffect(() => {
        calculateStats(parkingData);
    }, [parkingData, enteredCount, exitedCount]);

    useEffect(() => {
        const fetchTrends = async () => {
            try {
                const response = await parkingService.getTrends();
                const entryTrend = calculateTrend(response.todays_entries.count, response.yesterdays_entries.count);
                const exitTrend = calculateTrend(response.todays_exits.count, response.yesterdays_exits.count);
                setTrends({
                    entry_trend: entryTrend,
                    exit_trend: exitTrend
                });
            } catch (error) {
                console.error('Error fetching trends:', error);
            }
        };

        const calculateTrend = (todayCount, yesterdayCount) => {
            if (yesterdayCount === 0) return '0%';
            const change = todayCount - yesterdayCount;
            const percentage = ((change / yesterdayCount) * 100).toFixed(0);
            return `${change >= 0 ? '+' : ''}${percentage}%`;
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

    const formatTimestamp = (timestamp) => {
        const date = new Date(timestamp);
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');
        const day = date.getDate();
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const month = monthNames[date.getMonth()];
        return `${hours}:${minutes}:${seconds} ${day} ${month}`;
    };

    const handleViewAllVehicles = (e) => {
        e.preventDefault();
        navigate('/search');
    };

    return (
        <div className='main'>
            <div className='heading'>
                <div className='title'>
                    <h1>Dashboard</h1>
                    <p className='subtitle'>Real-time parking management overview</p>
                </div>
                <DateTime />
            </div>

            <div className='dashboard-stats'>
                <div className='cards'>
                    <Card
                        title="Vehicles Entered"
                        count={enteredCount}
                        icon={<IconLogin2 />}
                        trend={trends.entry_trend}
                        variant="entered"
                    />
                    <Card
                        title="Vehicles Exited"
                        count={exitedCount}
                        icon={<IconLogout />}
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
                            <a
                                href="#"
                                className="view-all"
                                onClick={handleViewAllVehicles}
                            >
                                View all vehicles
                            </a>
                        </div>
                    </div>

                    <div className="table-container">
                        <table className="vehicle-table">
                            <thead>
                                <tr>
                                    <th>License Plate</th>
                                    <th>Category</th>
                                    <th>Colour</th>
                                    <th>Timestamp</th>
                                    <th>Gate</th>
                                </tr>
                            </thead>
                            <tbody>
                                {parkingData.map((row, index) => (
                                    <tr key={index}>
                                        <td>{row.license_plate}</td>
                                        <td>{row.category}</td>
                                        <td>{row.color}</td>
                                        <td>{formatTimestamp(row.timestamp)}</td>
                                        <td>{row.gate}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Dashboard;
