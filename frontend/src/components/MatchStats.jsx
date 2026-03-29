import { useMemo } from 'react'
import './MatchStats.css'

const STAT_ORDER = [
  'start_distance',
  'progression',
  'circulation',
  'build_ups',
  'fast_breaks',
  'high_press',
]

function CircleRating({ rating, teamColor }) {
  const circles = []
  for (let i = 0; i < 5; i++) {
    const threshold = i + 1
    let fill = 'empty'
    if (rating >= threshold) {
      fill = 'full'
    } else if (rating >= threshold - 0.5) {
      fill = 'half'
    }
    circles.push(
      <svg key={i} width="18" height="18" viewBox="0 0 18 18" className="rating-circle">
        <circle cx="9" cy="9" r="7.5" fill="none" stroke={teamColor} strokeWidth="1.5" opacity="0.3" />
        {fill === 'full' && (
          <circle cx="9" cy="9" r="7.5" fill={teamColor} opacity="0.85" />
        )}
        {fill === 'half' && (
          <clipPath id={`half-${i}-${rating}`}>
            <rect x="0" y="0" width="9" height="18" />
          </clipPath>
        )}
        {fill === 'half' && (
          <circle cx="9" cy="9" r="7.5" fill={teamColor} opacity="0.85"
                  clipPath={`url(#half-${i}-${rating})`} />
        )}
      </svg>
    )
  }
  return <div className="circle-rating">{circles}</div>
}

function formatValue(value, unit) {
  if (typeof value === 'number') {
    if (unit === '%') return `${value}%`
    if (Number.isInteger(value)) return String(value)
    return String(value)
  }
  return String(value)
}

export default function MatchStats({ matchStats, homeTeam, awayTeam }) {
  const homeColor = '#C8102E'
  const awayColor = '#2563EB'

  const stats = useMemo(() => {
    if (!matchStats) return []
    return STAT_ORDER
      .filter(key => matchStats[key])
      .map(key => ({ key, ...matchStats[key] }))
  }, [matchStats])

  if (!stats.length) return null

  return (
    <div className="match-stats-panel">
      <div className="match-stats-header">Match Stats</div>
      <div className="match-stats-table">
        {stats.map(stat => {
          const homeBetter = stat.key === 'start_distance'
            ? stat.home < stat.away
            : stat.home > stat.away

          return (
            <div key={stat.key} className="stat-row">
              <div className="stat-side home">
                <CircleRating rating={stat.home_rating} teamColor={homeColor} />
                <span className={`stat-value ${homeBetter ? 'highlighted home' : ''}`}>
                  {formatValue(stat.home, stat.unit)}
                </span>
              </div>
              <div className="stat-label-col">
                <span className="stat-label">{stat.label}</span>
              </div>
              <div className="stat-side away">
                <span className={`stat-value ${!homeBetter ? 'highlighted away' : ''}`}>
                  {formatValue(stat.away, stat.unit)}
                </span>
                <CircleRating rating={stat.away_rating} teamColor={awayColor} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
