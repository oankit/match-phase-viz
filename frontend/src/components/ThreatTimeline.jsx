import { useRef, useEffect, useMemo, createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import * as d3 from 'd3'
import { IoFootball } from 'react-icons/io5'
import './ThreatTimeline.css'

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

const ThreatTimeline = ({
  phases = [],
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
    [homeTeam.id]: '#2b6da4',
    [awayTeam.id]: '#c83c35',
  }

  const minuteData = useMemo(() => {
    if (!phases || phases.length === 0) return []

    const totalMinutes = Math.ceil(duration / 60)
    const bins = Array.from({ length: totalMinutes }, (_, i) => ({
      minute: i + 1,
      [homeTeam.id]: 0,
      [awayTeam.id]: 0,
    }))

    phases.forEach(phase => {
      if (!phase.team || phase.xthreat_gained === undefined) return
      if (phase.xthreat_gained <= 0) return

      const endMin = Math.floor(phase.end / 60)
      if (endMin >= 0 && endMin < totalMinutes && bins[endMin]) {
        bins[endMin][phase.team] += phase.xthreat_gained
      }
    })

    const alpha = 0.82
    const smoothed = []
    bins.forEach((bin, i) => {
      const result = { ...bin }
      if (i > 0) {
        ;[homeTeam.id, awayTeam.id].forEach(teamId => {
          result[teamId] = alpha * bin[teamId] + (1 - alpha) * (smoothed[i - 1][teamId] || 0)
        })
      }
      smoothed.push(result)
    })

    return smoothed
  }, [phases, duration, homeTeam.id, awayTeam.id])

  useEffect(() => {
    if (!svgRef.current || minuteData.length === 0) return

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
      .attr('viewBox', `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom + goalMarkerSpace}`)

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const xScale = d3.scaleBand()
      .domain(minuteData.map(d => d.minute))
      .range([0, width])
      .padding(0.15)

    const maxVal = d3.max(minuteData, d =>
      Math.max(d[homeTeam.id] || 0, d[awayTeam.id] || 0)
    ) || 0.01

    const yScaleHome = d3.scaleLinear()
      .domain([0, maxVal])
      .range([height / 2, 0])

    const yScaleAway = d3.scaleLinear()
      .domain([0, maxVal])
      .range([height / 2, height])

    // Center line
    g.append('line')
      .attr('x1', 0)
      .attr('y1', height / 2)
      .attr('x2', width)
      .attr('y2', height / 2)
      .attr('stroke', '#ddd9d3')
      .attr('stroke-width', 1)

    // Home team bars (up)
    g.selectAll('.bar-home')
      .data(minuteData)
      .enter()
      .append('rect')
      .attr('class', 'bar-home')
      .attr('x', d => xScale(d.minute))
      .attr('y', d => yScaleHome(d[homeTeam.id] || 0))
      .attr('width', xScale.bandwidth())
      .attr('height', d => height / 2 - yScaleHome(d[homeTeam.id] || 0))
      .attr('fill', teamColors[homeTeam.id])
      .attr('opacity', 0.85)

    // Away team bars (down)
    g.selectAll('.bar-away')
      .data(minuteData)
      .enter()
      .append('rect')
      .attr('class', 'bar-away')
      .attr('x', d => xScale(d.minute))
      .attr('y', height / 2)
      .attr('width', xScale.bandwidth())
      .attr('height', d => yScaleAway(d[awayTeam.id] || 0) - height / 2)
      .attr('fill', teamColors[awayTeam.id])
      .attr('opacity', 0.85)

    // Goal markers (soccer ball icons above/below the chart)
    if (goals && goals.length > 0) {
      const R = 8

      goals.forEach(goal => {
        // Convert 0-indexed goal minute to 1-indexed for display (minute 0 = 1st minute)
        const goalMinute = goal.minute + 1
        const barX = xScale(goalMinute)
        if (barX === undefined) return

        const cx = barX + xScale.bandwidth() / 2
        const isHome = goal.team_id === homeTeam.id
        const cy = isHome ? -goalMarkerSpace / 2 : height + goalMarkerSpace / 2

        const { viewBox, inner } = getBallIcon()
        const size = R * 2
        const ballSvg = g.append('svg')
          .attr('x', cx - R)
          .attr('y', cy - R)
          .attr('width', size)
          .attr('height', size)
          .attr('viewBox', viewBox)
          .attr('fill', '#333')
        ballSvg.html(inner)

        // Vertical tick connecting ball to bar area
        g.append('line')
          .attr('x1', cx)
          .attr('y1', isHome ? -2 : height + 2)
          .attr('x2', cx)
          .attr('y2', isHome ? cy + R + 2 : cy - R - 2)
          .attr('stroke', '#bbb')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '2,2')
      })
    }

    // Time axis labels
    const tickInterval = 15
    const tickMinutes = minuteData
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
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'transparent')
      .attr('cursor', 'pointer')
      .on('click', (event) => {
        const [x] = d3.pointer(event)
        const minuteWidth = width / minuteData.length
        const clickedMinute = Math.floor(x / minuteWidth)
        const newTime = clickedMinute * 60
        if (onTimeChange) onTimeChange(Math.max(0, Math.min(duration, newTime)))
      })

  }, [minuteData, goals, currentTime, duration, homeTeam.id, awayTeam.id])

  return (
    <div>
      <div className="threat-timeline-header">
        <span className="threat-team-label home" style={{ color: teamColors[homeTeam.id] }}>
          {homeTeam.name}
        </span>
        <span className="threat-title">Threat Timeline</span>
        <span className="threat-team-label away" style={{ color: teamColors[awayTeam.id] }}>
          {awayTeam.name}
        </span>
      </div>
      <svg ref={svgRef} className="threat-timeline-svg" />
    </div>
  )
}

export default ThreatTimeline
