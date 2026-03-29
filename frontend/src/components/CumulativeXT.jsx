import { useRef, useEffect, useMemo } from 'react'
import * as d3 from 'd3'
import { getTeamColor } from '../utils/matchCatalog'
import './CumulativeXT.css'

const CumulativeXT = ({
  eventXt,
  metadata = {},
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

  const { homeData, awayData, maxXt } = useMemo(() => {
    if (!eventXt?.xt_events) return { homeData: [], awayData: [], maxXt: 0.5 }

    const homeId = eventXt.home_team_id
    const awayId = eventXt.away_team_id
    const maxMin = duration / 60

    // Only count positive xT (threat gained) for cumulative chart
    const homeEvents = eventXt.xt_events
      .filter(e => e.team_id === homeId && e.xt > 0)
      .sort((a, b) => a.minute - b.minute)

    const awayEvents = eventXt.xt_events
      .filter(e => e.team_id === awayId && e.xt > 0)
      .sort((a, b) => a.minute - b.minute)

    const buildCumulative = (events) => {
      const pts = [{ minute: 0, cumXt: 0 }]
      let cum = 0
      for (const e of events) {
        pts.push({ minute: e.minute, cumXt: cum })
        cum += e.xt
        pts.push({ minute: e.minute, cumXt: cum })
      }
      pts.push({ minute: maxMin, cumXt: cum })
      return pts
    }

    const hd = buildCumulative(homeEvents)
    const ad = buildCumulative(awayEvents)
    const mx = Math.max(
      hd[hd.length - 1]?.cumXt || 0,
      ad[ad.length - 1]?.cumXt || 0,
      0.3
    )

    return { homeData: hd, awayData: ad, maxXt: mx }
  }, [eventXt, duration])

  useEffect(() => {
    if (!svgRef.current || !eventXt?.xt_events) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const margin = { top: 20, right: 24, bottom: 32, left: 40 }
    const containerWidth = svgRef.current.parentElement?.clientWidth || 900
    const width = containerWidth - margin.left - margin.right
    const height = 200 - margin.top - margin.bottom

    svg.attr('width', containerWidth).attr('height', 200)

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    const maxMin = duration / 60
    const xScale = d3.scaleLinear().domain([0, maxMin]).range([0, width])
    const yScale = d3.scaleLinear().domain([0, maxXt * 1.15]).range([height, 0]).nice()

    // Grid lines
    g.append('g')
      .attr('class', 'grid-lines')
      .selectAll('line')
      .data(yScale.ticks(4))
      .enter()
      .append('line')
      .attr('x1', 0).attr('x2', width)
      .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
      .attr('stroke', '#ddd9d3').attr('stroke-dasharray', '3,3')

    // Half-time line
    g.append('line')
      .attr('x1', xScale(45)).attr('x2', xScale(45))
      .attr('y1', 0).attr('y2', height)
      .attr('stroke', '#ccc').attr('stroke-dasharray', '4,4').attr('stroke-width', 1)

    g.append('text')
      .attr('x', xScale(45)).attr('y', -6)
      .attr('text-anchor', 'middle')
      .attr('font-size', 9).attr('fill', '#999')
      .attr('font-family', "'Plus Jakarta Sans', sans-serif")
      .text('HT')

    // Area fills
    const areaGen = d3.area()
      .x(d => xScale(d.minute))
      .y0(height)
      .y1(d => yScale(d.cumXt))
      .curve(d3.curveStepAfter)

    g.append('path')
      .datum(homeData)
      .attr('d', areaGen)
      .attr('fill', teamColors[homeTeam.id])
      .attr('opacity', 0.08)

    g.append('path')
      .datum(awayData)
      .attr('d', areaGen)
      .attr('fill', teamColors[awayTeam.id])
      .attr('opacity', 0.08)

    // Step lines
    const lineGen = d3.line()
      .x(d => xScale(d.minute))
      .y(d => yScale(d.cumXt))
      .curve(d3.curveStepAfter)

    g.append('path')
      .datum(homeData)
      .attr('d', lineGen)
      .attr('fill', 'none')
      .attr('stroke', teamColors[homeTeam.id])
      .attr('stroke-width', 2.5)

    g.append('path')
      .datum(awayData)
      .attr('d', lineGen)
      .attr('fill', 'none')
      .attr('stroke', teamColors[awayTeam.id])
      .attr('stroke-width', 2.5)

    // X axis
    const xAxis = d3.axisBottom(xScale)
      .tickValues(d3.range(0, maxMin + 1, 15))
      .tickFormat(d => `${d}'`)
      .tickSize(4)

    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis)
      .call(g => g.select('.domain').attr('stroke', '#ccc'))
      .call(g => g.selectAll('.tick text')
        .attr('font-size', 10)
        .attr('fill', '#999')
        .attr('font-family', "'Plus Jakarta Sans', sans-serif"))
      .call(g => g.selectAll('.tick line').attr('stroke', '#ccc'))

    // Y axis
    const yAxis = d3.axisLeft(yScale)
      .ticks(4)
      .tickFormat(d => d.toFixed(1))
      .tickSize(4)

    g.append('g')
      .call(yAxis)
      .call(g => g.select('.domain').remove())
      .call(g => g.selectAll('.tick text')
        .attr('font-size', 10)
        .attr('fill', '#999')
        .attr('font-family', "'Plus Jakarta Sans', sans-serif"))
      .call(g => g.selectAll('.tick line').attr('stroke', '#ccc'))

    // Current time indicator
    const currentMin = currentTime / 60
    g.append('line')
      .attr('class', 'xt-time-indicator')
      .attr('x1', xScale(currentMin)).attr('x2', xScale(currentMin))
      .attr('y1', 0).attr('y2', height)
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 2)
      .attr('filter', 'drop-shadow(0 0 2px rgba(0,0,0,0.5))')

    // Final xT labels at end of lines
    const homeFinal = homeData[homeData.length - 1]?.cumXt || 0
    const awayFinal = awayData[awayData.length - 1]?.cumXt || 0

    g.append('text')
      .attr('x', width + 4)
      .attr('y', yScale(homeFinal))
      .attr('dy', '0.35em')
      .attr('font-size', 11).attr('font-weight', 700)
      .attr('fill', teamColors[homeTeam.id])
      .attr('font-family', "'Plus Jakarta Sans', sans-serif")
      .text(homeFinal.toFixed(2))

    g.append('text')
      .attr('x', width + 4)
      .attr('y', yScale(awayFinal))
      .attr('dy', '0.35em')
      .attr('font-size', 11).attr('font-weight', 700)
      .attr('fill', teamColors[awayTeam.id])
      .attr('font-family', "'Plus Jakarta Sans', sans-serif")
      .text(awayFinal.toFixed(2))

    // Click to seek
    g.append('rect')
      .attr('width', width).attr('height', height)
      .attr('fill', 'transparent').attr('cursor', 'pointer')
      .on('click', (event) => {
        const [mx] = d3.pointer(event)
        const newTime = xScale.invert(mx) * 60
        if (onTimeChange) onTimeChange(Math.max(0, Math.min(newTime, duration)))
      })

  }, [eventXt, homeData, awayData, maxXt, currentTime, duration, metadata, onTimeChange])

  if (!eventXt?.xt_events) return null

  return (
    <div>
      <div className="xt-chart-header">
        <span className="xt-team-label home" style={{ color: teamColors[homeTeam.id] }}>
          {homeTeam.name}
        </span>
        <span className="xt-chart-title">Cumulative xT</span>
        <span className="xt-team-label away" style={{ color: teamColors[awayTeam.id] }}>
          {awayTeam.name}
        </span>
      </div>
      <svg ref={svgRef} className="xt-chart-svg" />
    </div>
  )
}

export default CumulativeXT
