import { useRef, useEffect } from 'react'
import * as d3 from 'd3'
import './Timeline.css'

const Timeline = ({
  phases = [],
  currentTime = 0,
  duration = 90 * 60,
  onTimeChange,
  selectedPhase,
  onPhaseSelect
}) => {
  const svgRef = useRef(null)

  // Phase color mapping
  const phaseColors = {
    'high_press': '#DC2626',
    'defensive_block': '#2563EB',
    'counter_attack': '#F59E0B',
    'open_play': '#9CA3AF'
  }

  useEffect(() => {
    if (!phases || phases.length === 0) return

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const margin = { top: 20, right: 20, bottom: 40, left: 50 }
    const width = svgRef.current.clientWidth - margin.left - margin.right
    const height = 120 - margin.top - margin.bottom

    const g = svg
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // X scale - time
    const xScale = d3.scaleLinear()
      .domain([0, duration])
      .range([0, width])

    // Draw background
    g.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', '#f3f4f6')

    // Draw phase rectangles
    const phaseRects = g.selectAll('.phase-rect')
      .data(phases)
      .enter()
      .append('rect')
      .attr('class', 'phase-rect')
      .attr('x', d => xScale(d.start))
      .attr('y', 0)
      .attr('width', d => xScale(d.end) - xScale(d.start))
      .attr('height', height)
      .attr('fill', d => phaseColors[d.type] || '#999')
      .attr('opacity', d => selectedPhase && selectedPhase.id !== d.id ? 0.3 : 0.8)
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        if (onPhaseSelect) {
          onPhaseSelect(d.id === selectedPhase?.id ? null : d)
        }
      })
      .on('mouseover', function(event, d) {
        d3.select(this).attr('opacity', 1)

        // Show tooltip
        const tooltip = g.append('g')
          .attr('class', 'phase-tooltip')

        const tooltipRect = tooltip.append('rect')
          .attr('fill', 'rgba(0,0,0,0.8)')
          .attr('rx', 4)

        const tooltipText = tooltip.append('text')
          .attr('fill', 'white')
          .attr('font-size', '12px')
          .attr('x', xScale(d.start) + 5)
          .attr('y', height / 2)
          .text(`${d.type} - ${d.team} (${d.duration.toFixed(1)}s)`)

        const bbox = tooltipText.node().getBBox()
        tooltipRect
          .attr('x', bbox.x - 5)
          .attr('y', bbox.y - 2)
          .attr('width', bbox.width + 10)
          .attr('height', bbox.height + 4)
      })
      .on('mouseout', function(event, d) {
        d3.select(this).attr('opacity', selectedPhase && selectedPhase.id !== d.id ? 0.3 : 0.8)
        g.select('.phase-tooltip').remove()
      })

    // Draw current time indicator
    const timeIndicator = g.append('line')
      .attr('class', 'time-indicator')
      .attr('x1', xScale(currentTime))
      .attr('y1', 0)
      .attr('x2', xScale(currentTime))
      .attr('y2', height)
      .attr('stroke', '#ef4444')
      .attr('stroke-width', 2)
      .attr('cursor', 'ew-resize')

    // Time axis
    const xAxis = d3.axisBottom(xScale)
      .tickFormat(d => {
        const minutes = Math.floor(d / 60)
        return `${minutes}'`
      })
      .ticks(10)

    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis)

    // Drag behavior for time scrubbing
    const drag = d3.drag()
      .on('start', () => {
        g.append('rect')
          .attr('class', 'drag-overlay')
          .attr('width', width)
          .attr('height', height)
          .attr('fill', 'transparent')
          .attr('cursor', 'ew-resize')
      })
      .on('drag', (event) => {
        const newTime = Math.max(0, Math.min(duration, xScale.invert(event.x)))
        timeIndicator.attr('x1', xScale(newTime)).attr('x2', xScale(newTime))
        if (onTimeChange) onTimeChange(newTime)
      })
      .on('end', () => {
        g.select('.drag-overlay').remove()
      })

    timeIndicator.call(drag)

    // Click to jump
    g.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'transparent')
      .attr('cursor', 'pointer')
      .on('click', (event) => {
        const [x] = d3.pointer(event)
        const newTime = xScale.invert(x)
        if (onTimeChange) onTimeChange(newTime)
      })

  }, [phases, currentTime, duration, selectedPhase, onTimeChange, onPhaseSelect])

  return (
    <div className="timeline-container">
      <h3>Match Timeline</h3>
      <svg ref={svgRef} className="timeline-svg"></svg>
      <div className="timeline-legend">
        {Object.entries(phaseColors).map(([type, color]) => (
          <div key={type} className="legend-item">
            <div className="legend-color" style={{ backgroundColor: color }}></div>
            <span>{type.replace('_', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Timeline