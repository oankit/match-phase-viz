import { useMemo, useRef, useEffect } from 'react'
import * as d3 from 'd3'
import { computeRestDefenceScores, computeThreatScores } from '../utils/restDefence'
import { getTeamColor } from '../utils/matchCatalog'
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

const METRICS = [
  { key: 'defensive_line_height', label: 'Defensive Line', unit: 'm', scale: 105, decimals: 1, tooltip: 'Mean x-position of the deepest 4 outfield defenders (metres from goal line)' },
  { key: 'compactness', label: 'Compactness', unit: 'm\u00B2', scale: 400, decimals: 0, tooltip: 'Convex hull area of outfield players -- smaller = tighter shape' },
  { key: 'ppda_proxy', label: 'Pressure', unit: '', scale: 1, decimals: 1, tooltip: 'Average number of defenders within 5 m of the ball carrier' },
  { key: 'team_length', label: 'Team Length', unit: 'm', scale: 105, decimals: 1, tooltip: 'Distance between the most advanced and deepest outfield player' },
  { key: 'team_width', label: 'Team Width', unit: 'm', scale: 68, decimals: 1, tooltip: 'Distance between the widest outfield players laterally' },
  { key: 'stretching_index', label: 'Stretch Index', unit: 'm', scale: 105, decimals: 1, tooltip: 'Average distance of all outfield players from the team centroid' },
]

const SCORE_COLORS = {
  'Excellent': '#2d9a4e',
  'Good': '#4a90d9',
  'Fair': '#e8a838',
  'Poor': '#d94f4f',
  'Critical': '#c83c35',
  'Major': '#d94f4f',
  'Moderate': '#e8a838',
  'Minor': '#4a90d9',
  'Low': '#a8a29e',
}

/* ── Phase Distribution Donut Chart ── */
function PhaseDistChart({ phases, currentTime, size = 130 }) {
  const svgRef = useRef(null)

  const activePhasesUpToNow = useMemo(() => {
    if (!phases || phases.length === 0) return []
    if (currentTime === undefined || currentTime === null) return phases
    return phases.filter(p => p.start <= currentTime)
  }, [phases, currentTime])

  const data = useMemo(() => {
    return PHASE_TYPES.map(pt => ({
      ...pt,
      count: activePhasesUpToNow.filter(p => p.type === pt.key).length,
    })).filter(d => d.count > 0)
  }, [activePhasesUpToNow])

  const total = useMemo(() => data.reduce((s, d) => s + d.count, 0), [data])

  useEffect(() => {
    if (!svgRef.current || data.length === 0) return

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
      .attr('font-size', `${Math.round(size * 0.14)}px`)
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

  }, [data, total, size])

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

/* ── Single-Team Metric Row ── */
function TeamMetricRow({ label, value, unit, tooltip }) {
  const labelProps = tooltip ? { 'data-tooltip': tooltip } : {}
  return (
    <div className="team-metric-row">
      <span className="team-metric-label" {...labelProps}>{label}</span>
      <span className="team-metric-value">{value}{unit ? ` ${unit}` : ''}</span>
    </div>
  )
}

/* ── Single-Team Score Row (RDS / OTI) ── */
function TeamScoreRow({ label, score, tooltip }) {
  const color = score?.label ? SCORE_COLORS[score.label] || 'var(--text-primary)' : 'var(--text-muted)'
  return (
    <div className="team-metric-row team-score-row">
      <span className="team-metric-label" {...(tooltip ? { 'data-tooltip': tooltip } : {})}>
        {label}
        <span className="beta-tag">BETA</span>
      </span>
      <span className="team-metric-value">
        <span className="score-number" style={{ color }}>{score?.score != null ? score.score : '--'}</span>
        <span className="score-label" style={{ color, marginLeft: 4 }}>{score?.label || ''}</span>
      </span>
    </div>
  )
}

/* ── TeamMetricPanel: single-team panel with metrics + phase distribution ── */
export function TeamMetricPanel({ team, teamColor, phases, currentTime, rdsScore, otiScore }) {
  const teamId = team?.id

  const currentPhase = useMemo(() => {
    if (!phases || !teamId) return null
    return phases.find(p => p.team === teamId && currentTime >= p.start && currentTime <= p.end) || null
  }, [phases, currentTime, teamId])

  const teamPhases = useMemo(() => {
    if (!phases || !teamId) return []
    return phases.filter(p => p.team === teamId)
  }, [phases, teamId])

  const liveMetrics = useMemo(() => {
    return METRICS.map(m => {
      const val = currentPhase ? (currentPhase[m.key] || 0) * m.scale : null
      return {
        ...m,
        value: val !== null ? val.toFixed(m.decimals) : '--',
      }
    })
  }, [currentPhase])

  const xtGained = useMemo(() => {
    if (!phases || !teamId) return '--'
    const upToNow = phases.filter(p => p.end <= currentTime && p.team === teamId)
    return upToNow.reduce((s, p) => s + (p.xthreat_gained || 0), 0).toFixed(3)
  }, [phases, currentTime, teamId])

  const xtConceded = useMemo(() => {
    if (!phases || !teamId) return '--'
    const upToNow = phases.filter(p => p.end <= currentTime && p.team === teamId)
    return upToNow.reduce((s, p) => s + (p.xthreat_conceded || 0), 0).toFixed(3)
  }, [phases, currentTime, teamId])

  const phaseBadge = (phase) => {
    if (!phase) return <span className="phase-badge phase-none">--</span>
    return (
      <span className={`phase-badge phase-${phase.type}`}>
        {phase.type.replace(/_/g, ' ')}
      </span>
    )
  }

  return (
    <div className="team-metric-panel">
      <div className="team-phase-current">
        <span className="team-phase-label">Current Phase</span>
        {phaseBadge(currentPhase)}
      </div>

      <div className="team-metrics-list">
        {liveMetrics.map(m => (
          <TeamMetricRow key={m.key} label={m.label} value={m.value} unit={m.unit} tooltip={m.tooltip} />
        ))}
        <TeamMetricRow label="xT Gained" value={xtGained} tooltip="Cumulative expected threat generated from passes up to this point" />
        <TeamMetricRow label="xT Conceded" value={xtConceded} tooltip="Cumulative expected threat conceded to the opponent up to this point" />
        <TeamScoreRow label="Rest Defence" score={rdsScore} tooltip="Composite score (0-100) of numerical balance, spatial compactness, and pitch control behind the ball" />
        <TeamScoreRow label="Threat Index" score={otiScore} tooltip="Composite score (0-100) of spatial threat, numerical overload, space dominance, and momentum toward goal" />
      </div>

      <div className="team-phase-dist">
        <h4>Phase Distribution</h4>
        <PhaseDistChart phases={teamPhases} currentTime={currentTime} size={120} />
      </div>
    </div>
  )
}

/* ── Legacy dual-team MetricPanel (kept for backward compat) ── */
function MetricRow({ label, homeVal, awayVal, unit, tooltip, homeColor: hc, awayColor: ac }) {
  const labelProps = tooltip ? { 'data-tooltip': tooltip } : {}
  return (
    <div className="live-metric-row">
      <span className="live-val home" style={{ color: hc || 'var(--home-color)' }}>{homeVal}{unit ? ` ${unit}` : ''}</span>
      <span className="live-label" {...labelProps}>{label}</span>
      <span className="live-val away" style={{ color: ac || 'var(--away-color)' }}>{awayVal}{unit ? ` ${unit}` : ''}</span>
    </div>
  )
}

function ScoreRow({ label, homeScore, awayScore, tooltip }) {
  const homeColor = homeScore?.label ? SCORE_COLORS[homeScore.label] || 'var(--text-primary)' : 'var(--text-muted)'
  const awayColor = awayScore?.label ? SCORE_COLORS[awayScore.label] || 'var(--text-primary)' : 'var(--text-muted)'

  return (
    <div className="live-metric-row score-row">
      <span className="live-val home">
        <span className="score-number" style={{ color: homeColor }}>
          {homeScore?.score != null ? homeScore.score : '--'}
        </span>
        <span className="score-label" style={{ color: homeColor }}>
          {homeScore?.label || ''}
        </span>
      </span>
      <span className="live-label" {...(tooltip ? { 'data-tooltip': tooltip } : {})}>
        {label}
        <span className="beta-tag">BETA</span>
      </span>
      <span className="live-val away" style={{ textAlign: 'right' }}>
        <span className="score-label" style={{ color: awayColor }}>
          {awayScore?.label || ''}
        </span>
        <span className="score-number" style={{ color: awayColor }}>
          {awayScore?.score != null ? awayScore.score : '--'}
        </span>
      </span>
    </div>
  )
}

const MetricPanel = ({ phases, currentTime, homeTeam, awayTeam, teamNameMap = {}, players, ball }) => {
  const homeId = homeTeam?.id
  const awayId = awayTeam?.id
  const teamIds = useMemo(() => [homeId, awayId].filter(Boolean), [homeId, awayId])

  const rdsScores = useMemo(() => {
    if (teamIds.length < 2) return { home: { score: null, label: '--' }, away: { score: null, label: '--' } }
    return computeRestDefenceScores(players, ball, teamIds)
  }, [players, ball, teamIds])

  const otiScores = useMemo(() => {
    if (teamIds.length < 2) return { home: { score: null, label: '--' }, away: { score: null, label: '--' } }
    return computeThreatScores(players, ball, teamIds)
  }, [players, ball, teamIds])

  const homePhase = useMemo(() => {
    if (!phases || !homeId) return null
    return phases.find(p => p.team === homeId && currentTime >= p.start && currentTime <= p.end) || null
  }, [phases, currentTime, homeId])

  const awayPhase = useMemo(() => {
    if (!phases || !awayId) return null
    return phases.find(p => p.team === awayId && currentTime >= p.start && currentTime <= p.end) || null
  }, [phases, currentTime, awayId])

  const liveMetrics = useMemo(() => {
    return METRICS.map(m => {
      const hv = homePhase ? (homePhase[m.key] || 0) * m.scale : null
      const av = awayPhase ? (awayPhase[m.key] || 0) * m.scale : null
      return {
        ...m,
        homeVal: hv !== null ? hv.toFixed(m.decimals) : '--',
        awayVal: av !== null ? av.toFixed(m.decimals) : '--',
      }
    })
  }, [homePhase, awayPhase])

  const xtGained = useMemo(() => {
    if (!phases) return { home: '--', away: '--' }
    const upToNow = phases.filter(p => p.end <= currentTime)
    const hg = upToNow.filter(p => p.team === homeId).reduce((s, p) => s + (p.xthreat_gained || 0), 0)
    const ag = upToNow.filter(p => p.team === awayId).reduce((s, p) => s + (p.xthreat_gained || 0), 0)
    return { home: hg.toFixed(3), away: ag.toFixed(3) }
  }, [phases, currentTime, homeId, awayId])

  const xtConceded = useMemo(() => {
    if (!phases) return { home: '--', away: '--' }
    const upToNow = phases.filter(p => p.end <= currentTime)
    const hc = upToNow.filter(p => p.team === homeId).reduce((s, p) => s + (p.xthreat_conceded || 0), 0)
    const ac = upToNow.filter(p => p.team === awayId).reduce((s, p) => s + (p.xthreat_conceded || 0), 0)
    return { home: hc.toFixed(3), away: ac.toFixed(3) }
  }, [phases, currentTime, homeId, awayId])

  const phaseBadge = (phase) => {
    if (!phase) return <span className="phase-badge phase-none">--</span>
    return (
      <span className={`phase-badge phase-${phase.type}`}>
        {phase.type.replace(/_/g, ' ')}
      </span>
    )
  }

  return (
    <div className="metric-panel">
      <div className="live-team-header">
        <span className="live-team-name" style={{ color: getTeamColor(homeTeam?.id) }}>
          {homeTeam?.name || 'Home'}
        </span>
        <span className="live-header-label">Live Metrics</span>
        <span className="live-team-name" style={{ color: getTeamColor(awayTeam?.id) }}>
          {awayTeam?.name || 'Away'}
        </span>
      </div>

      <div className="live-phase-row">
        <span className="live-phase-side">{phaseBadge(homePhase)}</span>
        <span className="live-label">Current Phase</span>
        <span className="live-phase-side">{phaseBadge(awayPhase)}</span>
      </div>

      <div className="live-metrics-grid">
        {liveMetrics.map(m => (
          <MetricRow key={m.key} label={m.label} homeVal={m.homeVal} awayVal={m.awayVal} unit={m.unit} tooltip={m.tooltip} />
        ))}
        <MetricRow label="xT Gained" homeVal={xtGained.home} awayVal={xtGained.away} tooltip="Cumulative expected threat generated from passes up to this point" />
        <MetricRow label="xT Conceded" homeVal={xtConceded.home} awayVal={xtConceded.away} tooltip="Cumulative expected threat conceded to the opponent up to this point" />
        <ScoreRow label="Rest Defence" homeScore={rdsScores.home} awayScore={rdsScores.away} tooltip="Composite score (0-100) of numerical balance, spatial compactness, and pitch control behind the ball" />
        <ScoreRow label="Threat Index" homeScore={otiScores.home} awayScore={otiScores.away} tooltip="Composite score (0-100) of spatial threat, numerical overload, space dominance, and momentum toward goal" />
      </div>

      <div className="phase-summary">
        <h4>Phase Distribution</h4>
        <PhaseDistChart phases={phases} currentTime={currentTime} />
      </div>
    </div>
  )
}

export default MetricPanel
