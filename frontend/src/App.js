import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './Components/SideBar';
import Login from './Pages/Login';
import './App.css';
import { Helmet } from 'react-helmet';
function App() {
  const [auth, setAuth] = useState(null);

  useEffect(() => {
    const storedAuth = localStorage.getItem('auth');
    if (storedAuth) {
      setAuth(JSON.parse(storedAuth));
    }
  }, []);

  const PrivateRoute = ({ children }) => {
    if (!auth) return <Navigate to="/login" />;
    return children;
  };

  return (
    <Router>
      <Helmet>
        <title>Parking Dashboard</title>
        <link rel="icon" href="/path/to/your/favicon.ico" />
      </Helmet>
      <Routes>
        <Route path="/login" element={!auth ? <Login setAuth={setAuth} /> : <Navigate to="/" />} />
        
        <Route path="/*" element={
          <PrivateRoute>
            <Sidebar auth={auth} setAuth={setAuth} />
          </PrivateRoute>
        } />
      </Routes>
    </Router>
  );
}

export default App;