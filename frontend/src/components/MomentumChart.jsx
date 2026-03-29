import { useRef, useEffect, useMemo, createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import * as d3 from 'd3'
import { IoFootball } from 'react-icons/io5'
import { getTeamColor } from '../utils/matchCatalog'
import './MomentumChart.css'

let _ballIconCache = null
function getBallIcon() {
  if (!_ballIconCache) {
    const markup = renderToStaticMarkup(createElement(IoFootball))
    const vbMatch = markup.match(/viewBox="([^"]*)"/)
    const innerMatch = markup.match(/<svg[^>]*>([\s\S]*)<\/svg>/)
    _ballIconCache = {
      viewBox: vbMatch ? vbMatch[1] : '0 0 512 512',
      inner: innerMatch ? innerMatch[1] : ''
    }
  }
  return _ballIconCache
}

const MomentumChart = ({
  eventXt,
  shotXg,
  metadata = {},
  goals = [],
  currentTime = 0,
  duration = 90 * 60,
  onTimeChange,
}) => {
  const svgRef = useRef(null)

  const teams = metadata?.teams || []
  const homeTeam = teams[0] || { id: '', name: 'Home' }
  const awayTeam = teams[1] || { id: '', name: 'Away' }

  const teamColors = {
    [homeTeam.id]: getTeamColor(homeTeam.id),
    [awayTeam.id]: getTeamColor(awayTeam.id),
  }

  const momentumData = useMemo(() => {
    if (!eventXt?.xt_events) return []

    const homeId = eventXt.home_team_id
    const awayId = eventXt.away_team_id
    const totalMinutes = Math.ceil(duration / 60)

    // Per-minute threat: max(sum of positive xT, shot xG) per team, capped.
    // Approach inspired by The Athletic: use ball-location-based possession
    // value (xT) and shot-based xG, cap to prevent lone skyscrapers,
    // then smooth with bidirectional EMA so spikes become pyramids.
    const CAP = 0.20

    // Build shot xG lookup by minute and team
    const shotXgByMinute = {}
    if (shotXg?.shots) {
      shotXg.shots.forEach(s => {
        const min = Math.floor(s.minute)
        const key = `${min}_${s.team_id}`
        shotXgByMinute[key] = Math.max(shotXgByMinute[key] || 0, s.xg)
      })
    }

    // Raw per-minute threat per team
    const rawHome = new Array(totalMinutes).fill(0)
    const rawAway = new Array(totalMinutes).fill(0)

    eventXt.xt_events.forEach(e => {
      if (e.xt <= 0) return
      const m = Math.min(Math.floor(e.minute), totalMinutes - 1)
      if (m < 0) return
      if (e.team_id === homeId) rawHome[m] += e.xt
      else if (e.team_id === awayId) rawAway[m] += e.xt
    })

    // Blend in shot xG (take max of xT sum and shot xG for that minute)
    for (let m = 0; m < totalMinutes; m++) {
      const homeXg = shotXgByMinute[`${m}_${homeId}`] || 0
      const awayXg = shotXgByMinute[`${m}_${awayId}`] || 0
      rawHome[m] = Math.min(Math.max(rawHome[m], homeXg), CAP)
      rawAway[m] = Math.min(Math.max(rawAway[m], awayXg), CAP)
    }

    // Momentum = home threat - away threat
    const rawMomentum = rawHome.map((h, i) => h - rawAway[i])

    // Bidirectional EMA: forward pass then backward pass, averaged.
    // This creates pyramid shapes around spikes (leading + lagging).
    const alpha = 0.35
    const forward = new Array(totalMinutes)
    const backward = new Array(totalMinutes)

    forward[0] = rawMomentum[0]
    for (let i = 1; i < totalMinutes; i++) {
      forward[i] = alpha * rawMomentum[i] + (1 - alpha) * forward[i - 1]
    }

    backward[totalMinutes - 1] = rawMomentum[totalMinutes - 1]
    for (let i = totalMinutes - 2; i >= 0; i--) {
      backward[i] = alpha * rawMomentum[i] + (1 - alpha) * backward[i + 1]
    }

    const smoothed = rawMomentum.map((_, i) => ({
      minute: i + 1,
      momentum: (forward[i] + backward[i]) / 2,
    }))

    return smoothed
  }, [eventXt, shotXg, duration])

  useEffect(() => {
    if (!svgRef.current || momentumData.length === 0) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const containerWidth = svgRef.current.parentElement?.clientWidth || 900
    const goalMarkerSpace = 20
    const margin = { top: goalMarkerSpace + 4, right: 20, bottom: 24, left: 20 }
    const width = containerWidth - margin.left - margin.right
    const barAreaHeight = 110
    const height = barAreaHeight

    svg
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom + goalMarkerSpace)

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const homeId = eventXt?.home_team_id || homeTeam.id
    const awayId = eventXt?.away_team_id || awayTeam.id

    const xScale = d3.scaleBand()
      .domain(momentumData.map(d => d.minute))
      .range([0, width])
      .padding(0.15)

    const maxAbsVal = d3.max(momentumData, d => Math.abs(d.momentum)) || 0.01

    const yScale = d3.scaleLinear()
      .domain([-maxAbsVal, maxAbsVal])
      .range([height, 0])

    // Center line
    g.append('line')
      .attr('x1', 0).attr('y1', height / 2)
      .attr('x2', width).attr('y2', height / 2)
      .attr('stroke', '#ddd9d3').attr('stroke-width', 1)

    // Half-time line
    const htMinute = 46
    if (htMinute <= momentumData.length) {
      const htX = xScale(htMinute)
      if (htX !== undefined) {
        g.append('line')
          .attr('x1', htX).attr('x2', htX)
          .attr('y1', 0).attr('y2', height)
          .attr('stroke', '#ccc').attr('stroke-dasharray', '4,4').attr('stroke-width', 1)

        g.append('text')
          .attr('x', htX).attr('y', -6)
          .attr('text-anchor', 'middle')
          .attr('font-size', 9).attr('fill', '#999')
          .attr('font-family', "'Plus Jakarta Sans', sans-serif")
          .text('HT')
      }
    }

    // Bars - colored by which team dominates
    g.selectAll('.momentum-bar')
      .data(momentumData)
      .enter()
      .append('rect')
      .attr('class', 'momentum-bar')
      .attr('x', d => xScale(d.minute))
      .attr('y', d => d.momentum >= 0 ? yScale(d.momentum) : height / 2)
      .attr('width', xScale.bandwidth())
      .attr('height', d => Math.abs(yScale(d.momentum) - height / 2))
      .attr('fill', d => d.momentum >= 0 ? teamColors[homeId] : teamColors[awayId])
      .attr('opacity', 0.85)

    // Goal markers
    if (goals && goals.length > 0) {
      const R = 8

      goals.forEach(goal => {
        const goalMinute = goal.minute + 1
        const barX = xScale(goalMinute)
        if (barX === undefined) return

        const cx = barX + xScale.bandwidth() / 2
        const isHome = goal.team_id === homeId
        const cy = isHome ? -goalMarkerSpace / 2 : height + goalMarkerSpace / 2

        const { viewBox, inner } = getBallIcon()
        const size = R * 2
        const ballSvg = g.append('svg')
          .attr('x', cx - R).attr('y', cy - R)
          .attr('width', size).attr('height', size)
          .attr('viewBox', viewBox).attr('fill', '#333')
        ballSvg.html(inner)

        g.append('line')
          .attr('x1', cx)
          .attr('y1', isHome ? -2 : height + 2)
          .attr('x2', cx)
          .attr('y2', isHome ? cy + R + 2 : cy - R - 2)
          .attr('stroke', '#bbb').attr('stroke-width', 1).attr('stroke-dasharray', '2,2')
      })
    }

    // Time axis labels
    const tickInterval = 15
    const tickMinutes = momentumData
      .filter(d => d.minute % tickInterval === 0 || d.minute === 1)
      .map(d => d.minute)

    g.selectAll('.tick-label')
      .data(tickMinutes)
      .enter()
      .append('text')
      .attr('class', 'tick-label')
      .attr('x', d => xScale(d) + xScale.bandwidth() / 2)
      .attr('y', height + goalMarkerSpace + 16)
      .attr('text-anchor', 'middle')
      .attr('fill', '#999')
      .attr('font-size', '10px')
      .attr('font-family', "'Plus Jakarta Sans', sans-serif")
      .text(d => `${d}'`)

    // Current time indicator
    const currentMinute = Math.floor(currentTime / 60) + 1
    const currentX = xScale(currentMinute)
    if (currentX !== undefined) {
      g.append('line')
        .attr('x1', currentX + xScale.bandwidth() / 2)
        .attr('y1', -goalMarkerSpace)
        .attr('x2', currentX + xScale.bandwidth() / 2)
        .attr('y2', height + goalMarkerSpace)
        .attr('stroke', '#1a1a1a')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '4,3')
        .attr('opacity', 0.4)
    }

    // Click interaction
    g.append('rect')
      .attr('width', width).attr('height', height)
      .attr('fill', 'transparent').attr('cursor', 'pointer')
      .on('click', (event) => {
        const [x] = d3.pointer(event)
        const minuteWidth = width / momentumData.length
        const clickedMinute = Math.floor(x / minuteWidth)
        const newTime = clickedMinute * 60
        if (onTimeChange) onTimeChange(Math.max(0, Math.min(duration, newTime)))
      })

  }, [momentumData, goals, currentTime, duration, homeTeam.id, awayTeam.id, eventXt])

  if (!eventXt?.all_events) return null

  return (
    <div>
      <div className="momentum-chart-header">
        <span className="momentum-team-label home" style={{ color: teamColors[homeTeam.id] }}>
          {homeTeam.name}
        </span>
        <span className="momentum-title">Game Momentum</span>
        <span className="momentum-team-label away" style={{ color: teamColors[awayTeam.id] }}>
          {awayTeam.name}
        </span>
      </div>
      <svg ref={svgRef} className="momentum-chart-svg" />
    </div>
  )
}

export default MomentumChart
