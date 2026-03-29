import { useMemo, useRef, useEffect } from 'react'
import * as d3 from 'd3'
import MetricCard from './MetricCard'
import './MetricPanel.css'

const PHASE_TYPES = [
  { key: 'attacking', label: 'Attacking', color: '#2d9a4e' },
  { key: 'build_up', label: 'Build-up', color: '#4a90d9' },
  { key: 'high_press', label: 'High Press', color: '#d94f4f' },
  { key: 'mid_block', label: 'Mid Block', color: '#e8a838' },
  { key: 'defensive_block', label: 'Def. Block', color: '#7b5ea7' },
  { key: 'counter_attack', label: 'Counter', color: '#e06b9a' },
  { key: 'open_play', label: 'Open Play', color: '#a8a29e' },
]

function PhaseDistChart({ phases }) {
  const svgRef = useRef(null)

  const data = useMemo(() => {
    if (!phases || phases.length === 0) return []
    return PHASE_TYPES.map(pt => ({
      ...pt,
      count: phases.filter(p => p.type === pt.key).length,
    })).filter(d => d.count > 0)
  }, [phases])

  const total = useMemo(() => data.reduce((s, d) => s + d.count, 0), [data])

  useEffect(() => {
    if (!svgRef.current || data.length === 0) return

    const size = 160
    const radius = size / 2
    const innerRadius = radius * 0.55

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const g = svg
      .attr('width', size)
      .attr('height', size)
      .append('g')
      .attr('transform', `translate(${radius},${radius})`)

    const pie = d3.pie().value(d => d.count).sort(null).padAngle(0.02)
    const arc = d3.arc().innerRadius(innerRadius).outerRadius(radius).cornerRadius(3)

    g.selectAll('path')
      .data(pie(data))
      .enter()
      .append('path')
      .attr('d', arc)
      .attr('fill', d => d.data.color)
      .attr('opacity', 0.9)

    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '-0.1em')
      .attr('font-size', '22px')
      .attr('font-weight', '700')
      .attr('fill', 'var(--text-primary)')
      .attr('font-family', "'Plus Jakarta Sans', sans-serif")
      .text(total)

    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '1.3em')
      .attr('font-size', '9px')
      .attr('font-weight', '600')
      .attr('fill', 'var(--text-muted)')
      .attr('font-family', "'Plus Jakarta Sans', sans-serif")
      .attr('text-transform', 'uppercase')
      .attr('letter-spacing', '0.06em')
      .text('PHASES')

  }, [data, total])

  if (data.length === 0) return null

  return (
    <div className="phase-pie-container">
      <svg ref={svgRef} />
      <div className="phase-pie-legend">
        {data.map(d => (
          <div key={d.key} className="phase-pie-legend-item">
            <span className="phase-pie-dot" style={{ backgroundColor: d.color }} />
            <span className="phase-pie-label">{d.label}</span>
            <span className="phase-pie-count">{d.count}</span>
            <span className="phase-pie-pct">{Math.round(d.count / total * 100)}%</span>
          </div>
        ))}
      </div>
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
