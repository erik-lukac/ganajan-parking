import React, { useState, useEffect } from 'react';
import { Link, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { IconChartDonut, IconDatabaseSearch, IconFile, IconLayoutDashboard, IconLogout, IconSearch } from '@tabler/icons-react';
import Dashboard from '../Pages/Dashboard';
import Database from '../Pages/Database';
import AnalyticsDashboard from '../Pages/Analytics';
import Export from '../Pages/Export';
import '../Styles/SideNavbar.css';
import '../Styles/Dashboard.css';
import AnalyticsDashboard1 from '../Pages/Database1';

const Sidebar = ({ auth, setAuth }) => {
  const [isOpen, setIsOpen] = useState(true);
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem('auth');
    setAuth(null);
    window.location = '/login';
  };

  const menuItems = [
    { id: 'home', path: '/', icon: <IconLayoutDashboard size={24} />, label: 'Dashboard' },
    { id: 'search', path: '/search', icon: <IconSearch size={24}/>, label: 'Search' },
    { id: 'messages', path: '/analytics', icon: <IconChartDonut size={24}/>, label: 'Analytics' },
    { id: 'settings', path: '/export', icon: <IconFile size={24}/>, label: 'Export' },
    { 
      id: 'logout', 
      path: '#', 
      icon: <IconLogout size={24} />, 
      label: 'Logout',
      action: handleLogout
    }
  ];

  return (
    <div className="app-container">
      <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
        <button onClick={() => setIsOpen(!isOpen)} className="toggle-button">
          {isOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            item.action ? (
              <div
                key={item.id}
                className="nav-item"
                onClick={item.action}
              >
                <span className="icon">{item.icon}</span>
                <span className="label">{item.label}</span>
              </div>
            ) : (
              <Link
                key={item.id}
                to={item.path}
                className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
              >
                <span className="icon">{item.icon}</span>
                <span className="label">{item.label}</span>
              </Link>
            )
          ))}
        </nav>
      </div>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/search" element={<Database />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/export" element={<Export />} />
          <Route path="/test" element={<AnalyticsDashboard1/>}/>
        </Routes>
      </main>
    </div>
  );
};

export default Sidebar;