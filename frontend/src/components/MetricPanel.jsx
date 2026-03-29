import { useMemo } from 'react'
import MetricCard from './MetricCard'
import './MetricPanel.css'

const PHASE_TYPES = [
  { key: 'attacking', label: 'ATK', color: '#5ea832' },
  { key: 'build_up', label: 'BLD', color: '#8bc575' },
  { key: 'high_press', label: 'HI P', color: '#c47a5a' },
  { key: 'mid_block', label: 'MID', color: '#9a8676' },
  { key: 'defensive_block', label: 'DEF', color: '#7c92a6' },
  { key: 'counter_attack', label: 'CTR', color: '#bfa64e' },
  { key: 'open_play', label: 'OPN', color: '#b5b0a8' },
]

function PhaseDistChart({ phases }) {
  const counts = useMemo(() => {
    if (!phases || phases.length === 0) return PHASE_TYPES.map(() => 0)
    return PHASE_TYPES.map(pt => phases.filter(p => p.type === pt.key).length)
  }, [phases])

  const max = Math.max(...counts, 1)

  return (
    <div className="phase-dist-chart">
      {PHASE_TYPES.map((pt, i) => (
        <div key={pt.key} className="phase-bar-wrapper">
          <span className="phase-bar-count">{counts[i]}</span>
          <div
            className="phase-bar"
            style={{
              backgroundColor: pt.color,
              height: `${(counts[i] / max) * 80}%`,
              opacity: counts[i] > 0 ? 0.85 : 0.2,
            }}
          />
          <span className="phase-bar-label">{pt.label}</span>
        </div>
      ))}
    </div>
  )
}

const MetricPanel = ({ phases, currentPhase, teamNameMap = {}, fullView = false }) => {
  const metrics = useMemo(() => {
    if (!phases || phases.length === 0) {
      return {
        avgDefensiveLine: '0.0', avgCompactness: '0', avgPPDA: '0.0',
        avgTeamLength: '0.0', avgTeamWidth: '0.0', avgLPWRatio: '0.00',
        avgStretchingIndex: '0.0', totalXThreatGained: '0.000', totalXThreatConceded: '0.000'
      }
    }

    const avg = (key, scale = 1) => {
      const sum = phases.reduce((s, p) => s + (p[key] || 0), 0)
      return (sum / phases.length * scale).toFixed(key === 'lpw_ratio' ? 2 : key === 'compactness' ? 0 : 1)
    }

    return {
      avgDefensiveLine: avg('defensive_line_height', 105),
      avgCompactness: avg('compactness', 400),
      avgPPDA: avg('ppda_proxy'),
      avgTeamLength: avg('team_length', 105),
      avgTeamWidth: avg('team_width', 68),
      avgLPWRatio: avg('lpw_ratio'),
      avgStretchingIndex: avg('stretching_index', 105),
      totalXThreatGained: phases.reduce((s, p) => s + (p.xthreat_gained || 0), 0).toFixed(3),
      totalXThreatConceded: phases.reduce((s, p) => s + (p.xthreat_conceded || 0), 0).toFixed(3),
    }
  }, [phases])

  if (fullView) {
    return (
      <div className="metric-panel">

        {currentPhase && (
          <div className="current-phase-info">
            <h4>Current Phase</h4>
            <div className={`phase-badge phase-${currentPhase.type}`}>
              {currentPhase.type.replace(/_/g, ' ')} - {teamNameMap[currentPhase.team] || currentPhase.team}
            </div>
          </div>
        )}

        <div className="metric-cards full-view">
          <MetricCard title="Defensive Line" value={metrics.avgDefensiveLine} unit="m" description="Avg defensive line height" />
          <MetricCard title="Compactness" value={metrics.avgCompactness} unit="m2" description="Avg convex hull area" />
          <MetricCard title="Pressure" value={metrics.avgPPDA} description="Defenders near ball" />
          <MetricCard title="Team Length" value={metrics.avgTeamLength} unit="m" description="Longitudinal spread" />
          <MetricCard title="Team Width" value={metrics.avgTeamWidth} unit="m" description="Lateral spread" />
          <MetricCard title="LPW Ratio" value={metrics.avgLPWRatio} description=">1=deep/narrow" />
          <MetricCard title="Stretch Index" value={metrics.avgStretchingIndex} unit="m" description="Avg distance from centroid" />
          <MetricCard title="xT Gained" value={metrics.totalXThreatGained} description="Total threat created" showTrend={parseFloat(metrics.totalXThreatGained) > 0} />
          <MetricCard title="xT Conceded" value={metrics.totalXThreatConceded} description="Total threat allowed" showTrend={parseFloat(metrics.totalXThreatConceded) < 0} />
        </div>

        <div className="phase-summary">
          <h4>Phase Distribution</h4>
          <PhaseDistChart phases={phases} />
        </div>
      </div>
    )
  }

  return (
    <div className="metric-panel">
      <h3>Match Metrics</h3>

      {currentPhase && (
        <div className="current-phase-info">
          <h4>Current Phase</h4>
          <div className={`phase-badge phase-${currentPhase.type}`}>
            {currentPhase.type.replace(/_/g, ' ')} - {teamNameMap[currentPhase.team] || currentPhase.team}
          </div>
        </div>
      )}

      <div className="metric-cards">
        <MetricCard title="Defensive Line" value={metrics.avgDefensiveLine} unit="m" description="Avg defensive line height" />
        <MetricCard title="Compactness" value={metrics.avgCompactness} unit="m2" description="Avg convex hull area" />
        <MetricCard title="Pressure" value={metrics.avgPPDA} description="Defenders near ball" />
        <MetricCard title="xT Gained" value={metrics.totalXThreatGained} description="Threat created" showTrend={parseFloat(metrics.totalXThreatGained) > 0} />
        <MetricCard title="xT Conceded" value={metrics.totalXThreatConceded} description="Threat allowed" showTrend={parseFloat(metrics.totalXThreatConceded) < 0} />
      </div>

      <div className="phase-summary">
        <h4>Phase Distribution</h4>
        <PhaseDistChart phases={phases} />
      </div>
    </div>
  )
}

export default MetricPanel
