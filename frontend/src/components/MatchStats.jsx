import { useMemo } from 'react'
import './MatchStats.css'

const BASIC_STATS = [
  'possession',
  'shots',
  'shots_on_target',
  'corners',
  'fouls',
  'saves',
]

const ADVANCED_STATS = [
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

function BasicStatRow({ stat, homeColor, awayColor }) {
  const total = (stat.home || 0) + (stat.away || 0)
  const homePct = total > 0 ? stat.home / total * 100 : 50
  const isPossession = stat.key === 'possession'
  const lowerIsBetter = stat.key === 'fouls'
  const homeBetter = lowerIsBetter ? stat.home < stat.away : stat.home > stat.away

  return (
    <div className="basic-stat-row">
      <div className="basic-stat-values">
        <span className={`basic-val ${homeBetter ? 'bold' : ''}`} style={{ color: homeBetter ? homeColor : undefined }}>
          {isPossession ? `${stat.home}%` : stat.home}
        </span>
        <span className="basic-label">{stat.label}</span>
        <span className={`basic-val ${!homeBetter ? 'bold' : ''}`} style={{ color: !homeBetter ? awayColor : undefined }}>
          {isPossession ? `${stat.away}%` : stat.away}
        </span>
      </div>
      <div className="basic-bar-track">
        <div className="basic-bar home" style={{ width: `${homePct}%`, backgroundColor: homeColor }} />
        <div className="basic-bar away" style={{ width: `${100 - homePct}%`, backgroundColor: awayColor }} />
      </div>
    </div>
  )
}

export default function MatchStats({ matchStats, homeTeam, awayTeam }) {
  const homeColor = '#2b6da4'
  const awayColor = '#c83c35'

  const basicStats = useMemo(() => {
    if (!matchStats) return []
    return BASIC_STATS
      .filter(key => matchStats[key])
      .map(key => ({ key, ...matchStats[key] }))
  }, [matchStats])

  const advancedStats = useMemo(() => {
    if (!matchStats) return []
    return ADVANCED_STATS
      .filter(key => matchStats[key])
      .map(key => ({ key, ...matchStats[key] }))
  }, [matchStats])

  if (!basicStats.length && !advancedStats.length) return null

  return (
    <div>
      {basicStats.length > 0 && (
        <div className="basic-stats-section">
          {basicStats.map(stat => (
            <BasicStatRow key={stat.key} stat={stat} homeColor={homeColor} awayColor={awayColor} />
          ))}
        </div>
      )}

      {advancedStats.length > 0 && (
        <div className="match-stats-table">
          <h4 className="stats-section-title">Advanced</h4>
          {advancedStats.map(stat => {
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
      )}
    </div>
  )
}
