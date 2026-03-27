import './MetricCard.css'

const MetricCard = ({
  title,
  value,
  unit = '',
  description,
  color = '#2563EB',
  showTrend = false
}) => {
  return (
    <div className="metric-card" style={{ borderLeftColor: color }}>
      <div className="metric-header">
        <h5>{title}</h5>
        {showTrend && (
          <span className={`trend-indicator ${value >= 0 ? 'positive' : 'negative'}`}>
            {value >= 0 ? '▲' : '▼'}
          </span>
        )}
      </div>
      <div className="metric-value">
        <span className="value" style={{ color }}>
          {value}
        </span>
        {unit && <span className="unit">{unit}</span>}
      </div>
      {description && (
        <p className="metric-description">{description}</p>
      )}
    </div>
  )
}

export default MetricCard