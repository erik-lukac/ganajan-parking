import React from 'react';
import '../Styles/Cards.css';
import { IconTrendingUp, IconTrendingDown } from '@tabler/icons-react';

function Card({title, count, icon, trend, variant}) {
  const cardClass = `vehicle-card ${variant || ''}`;
  
  const renderTrend = () => {
    if (!trend) return null;
    
    const isPositive = trend.includes('+');
    return (
      <div className={`trend-indicator ${isPositive ? 'trend-up' : 'trend-down'}`}>
        {isPositive ? <IconTrendingUp size={16} /> : <IconTrendingDown size={16} />}
        <span>{trend}</span>
      </div>
    );
  };

  return (
    <div className={cardClass}>
      <div className="card-content">
        <div className="card-info">
          <span className="card-title">{title}</span>
          <span className="card-count">{count}</span>
          {renderTrend()}
        </div>
        <div className="card-icon-wrapper">
          <div className="card-icon-container">
            {icon}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Card;