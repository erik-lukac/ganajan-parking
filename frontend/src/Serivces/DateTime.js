import React, { useEffect, useState } from 'react';

function DateTime() {
    const [currentDateTime, setCurrentDateTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentDateTime(new Date());
        }, 1000);

        return () => clearInterval(timer);
    }, []);

    const formatDate = (date) => {
        const day = date.getDate(); // Use local date
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const month = monthNames[date.getMonth()]; // Use local month
        const year = date.getFullYear(); // Use local year

        // Add suffix to day (st, nd, rd, th)
        const suffix = (day % 10 === 1 && day !== 11) ? "st" :
                       (day % 10 === 2 && day !== 12) ? "nd" :
                       (day % 10 === 3 && day !== 13) ? "rd" : "th";

        return `${day}${suffix} ${month} ${year}`;
    };

    const formatTime = (date) => {
        let hours = date.getHours(); // Use local hours
        const minutes = date.getMinutes(); // Use local minutes
        const ampm = hours >= 12 ? "PM" : "AM"; // Uppercase for consistency
        hours = hours % 12 || 12; // Convert 0 to 12 for 12-hour format
        const formattedMinutes = minutes < 10 ? `0${minutes}` : minutes;

        return `${hours}:${formattedMinutes} ${ampm}`; // No UTC label
    };

    return (
        <div className="date-time">
            <span>{formatDate(currentDateTime)}</span>
            <span>  |  </span>
            <span>{formatTime(currentDateTime)}</span>
        </div>
    );
}

export default DateTime;

