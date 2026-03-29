import { useRef, useEffect, useMemo } from 'react'
import * as d3 from 'd3'
import { getTeamColor } from '../utils/matchCatalog'
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
    [homeTeam.id]: getTeamColor(homeTeam.id),
    [awayTeam.id]: getTeamColor(awayTeam.id),
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

      const startMin = Math.floor(phase.start / 60)
      const endMin = Math.floor(phase.end / 60)
      const phaseMinutes = Math.max(1, endMin - startMin + 1)
      const perMinuteGain = Math.abs(phase.xthreat_gained) / phaseMinutes

      for (let m = startMin; m <= endMin && m < totalMinutes; m++) {
        if (bins[m]) {
          bins[m][phase.team] += perMinuteGain
        }
      }
    })

    const alpha = 0.35
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

    // Half-time line
    const htX = xScale(45)
    if (htX !== undefined) {
      const htCenter = htX + xScale.bandwidth() / 2
      g.append('line')
        .attr('x1', htCenter).attr('x2', htCenter)
        .attr('y1', 0).attr('y2', height)
        .attr('stroke', '#ccc').attr('stroke-dasharray', '4,4').attr('stroke-width', 1)

      g.append('text')
        .attr('x', htCenter).attr('y', -6)
        .attr('text-anchor', 'middle')
        .attr('font-size', 9).attr('fill', '#999')
        .attr('font-family', "'Plus Jakarta Sans', sans-serif")
        .text('HT')
    }

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

    // Goal markers
    if (goals && goals.length > 0) {
      const ballRadius = 7

      goals.forEach(goal => {
        const goalMinute = goal.minute + 1
        const barX = xScale(goalMinute)
        if (barX === undefined) return

        const cx = barX + xScale.bandwidth() / 2
        const isHome = goal.team_id === homeTeam.id
        const cy = isHome ? -goalMarkerSpace / 2 : height + goalMarkerSpace / 2

        const ballG = g.append('g')
          .attr('transform', `translate(${cx}, ${cy})`)

        ballG.append('circle')
          .attr('r', ballRadius)
          .attr('fill', 'white')
          .attr('stroke', '#333')
          .attr('stroke-width', 1.5)

        const pentR = ballRadius * 0.45
        for (let i = 0; i < 5; i++) {
          const angle = (i * 72 - 90) * (Math.PI / 180)
          ballG.append('circle')
            .attr('cx', pentR * Math.cos(angle))
            .attr('cy', pentR * Math.sin(angle))
            .attr('r', 1.2)
            .attr('fill', '#333')
        }
        ballG.append('circle')
          .attr('r', 1.2)
          .attr('fill', '#333')

        g.append('line')
          .attr('x1', cx)
          .attr('y1', isHome ? -2 : height + 2)
          .attr('x2', cx)
          .attr('y2', isHome ? cy + ballRadius + 2 : cy - ballRadius - 2)
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
