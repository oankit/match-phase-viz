import { useRef, useEffect, useMemo } from 'react'
import * as d3 from 'd3'
import './ThreatTimeline.css'

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
    [homeTeam.id]: '#C8102E',
    [awayTeam.id]: '#6CABDD',
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

    const alpha = 0.55
    const smoothed = bins.map((bin, i) => {
      const result = { ...bin }
      if (i > 0) {
        ;[homeTeam.id, awayTeam.id].forEach(teamId => {
          result[teamId] = alpha * bin[teamId] + (1 - alpha) * (bins[i - 1][teamId] || 0)
        })
      }
      return result
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
      .attr('stroke', '#e5e1d8')
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

        const ballG = g.append('g')
          .attr('transform', `translate(${cx}, ${cy})`)

        // Outer circle
        ballG.append('circle')
          .attr('r', R)
          .attr('fill', '#fff')
          .attr('stroke', '#222')
          .attr('stroke-width', 1.2)

        // Central pentagon
        const pR = R * 0.38
        const pentPts = Array.from({ length: 5 }, (_, i) => {
          const a = (i * 72 - 90) * Math.PI / 180
          return [pR * Math.cos(a), pR * Math.sin(a)]
        })
        ballG.append('polygon')
          .attr('points', pentPts.map(p => p.join(',')).join(' '))
          .attr('fill', '#222')

        // Seam lines from each pentagon vertex outward to the edge
        const outerR = R * 0.88
        pentPts.forEach(([px, py]) => {
          const len = Math.sqrt(px * px + py * py)
          const ex = (px / len) * outerR
          const ey = (py / len) * outerR
          ballG.append('line')
            .attr('x1', px).attr('y1', py)
            .attr('x2', ex).attr('y2', ey)
            .attr('stroke', '#222')
            .attr('stroke-width', 0.9)
        })

        // Short arc segments at each outer point (the hex edges)
        pentPts.forEach(([px, py], i) => {
          const next = pentPts[(i + 1) % 5]
          const len = Math.sqrt(px * px + py * py)
          const nlen = Math.sqrt(next[0] * next[0] + next[1] * next[1])
          const ex = (px / len) * outerR
          const ey = (py / len) * outerR
          const nx = (next[0] / nlen) * outerR
          const ny = (next[1] / nlen) * outerR
          const mx = (ex + nx) / 2
          const my = (ey + ny) / 2
          ballG.append('line')
            .attr('x1', ex).attr('y1', ey)
            .attr('x2', mx).attr('y2', my)
            .attr('stroke', '#222')
            .attr('stroke-width', 0.9)
          ballG.append('line')
            .attr('x1', nx).attr('y1', ny)
            .attr('x2', mx).attr('y2', my)
            .attr('stroke', '#222')
            .attr('stroke-width', 0.9)
        })

        // Vertical tick connecting ball to bar area
        g.append('line')
          .attr('x1', cx)
          .attr('y1', isHome ? -2 : height + 2)
          .attr('x2', cx)
          .attr('y2', isHome ? cy + R + 2 : cy - R - 2)
          .attr('stroke', '#aaa')
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
      .attr('fill', '#333')
      .attr('font-size', '11px')
      .attr('font-family', "'Noto Sans', sans-serif")
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
        .attr('stroke', '#333')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '4,3')
        .attr('opacity', 0.5)
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
    <div className="threat-timeline">
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
