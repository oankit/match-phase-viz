import MetricCard from './MetricCard'
import './MetricPanel.css'

const MetricPanel = ({ phases, currentPhase, formations }) => {
  // Calculate aggregate metrics for visible phases
  const calculateMetrics = () => {
    if (!phases || phases.length === 0) {
      return {
        avgDefensiveLine: 0,
        avgCompactness: 0,
        avgPPDA: 0,
        totalXThreatGained: 0,
        totalXThreatConceded: 0,
        avgFormationStability: 0
      }
    }

    // Calculate phase-based metrics
    const avgDefensiveLine = phases.reduce((sum, p) =>
      sum + (p.defensive_line_height || 0), 0) / phases.length * 105 // Convert to meters

    const avgCompactness = phases.reduce((sum, p) =>
      sum + (p.compactness || 0), 0) / phases.length * 400 // Convert to m²

    const avgPPDA = phases.reduce((sum, p) =>
      sum + (p.ppda_proxy || 0), 0) / phases.length

    const totalXThreatGained = phases.reduce((sum, p) =>
      sum + (p.xthreat_gained || 0), 0)

    const totalXThreatConceded = phases.reduce((sum, p) =>
      sum + (p.xthreat_conceded || 0), 0)

    // Calculate formation stability if available
    let avgFormationStability = 0
    if (formations && formations.length > 0) {
      const allStabilities = formations
        .flatMap(f => f.stability_scores || [])
        .filter(s => s !== undefined)

      if (allStabilities.length > 0) {
        avgFormationStability = allStabilities.reduce((a, b) => a + b, 0) / allStabilities.length
      }
    }

    return {
      avgDefensiveLine: avgDefensiveLine.toFixed(1),
      avgCompactness: avgCompactness.toFixed(0),
      avgPPDA: avgPPDA.toFixed(1),
      totalXThreatGained: totalXThreatGained.toFixed(2),
      totalXThreatConceded: totalXThreatConceded.toFixed(2),
      avgFormationStability: (avgFormationStability * 100).toFixed(0)
    }
  }

  const metrics = calculateMetrics()

  return (
    <div className="metric-panel">
      <h3>Match Metrics</h3>

      {currentPhase && (
        <div className="current-phase-info">
          <h4>Current Phase</h4>
          <div className={`phase-badge phase-${currentPhase.type}`}>
            {currentPhase.type.replace('_', ' ')} - {currentPhase.team}
          </div>
        </div>
      )}

      <div className="metric-cards">
        <MetricCard
          title="Defensive Line Height"
          value={metrics.avgDefensiveLine}
          unit="m"
          description="Average defensive line position"
          color="#2563EB"
        />

        <MetricCard
          title="Team Compactness"
          value={metrics.avgCompactness}
          unit="m²"
          description="Average convex hull area"
          color="#10B981"
        />

        <MetricCard
          title="Pressure Intensity"
          value={metrics.avgPPDA}
          unit=""
          description="Defenders near ball carrier"
          color="#F59E0B"
        />

        <MetricCard
          title="xThreat Gained"
          value={metrics.totalXThreatGained}
          unit=""
          description="Total threat created"
          color="#DC2626"
          showTrend={parseFloat(metrics.totalXThreatGained) > 0}
        />

        <MetricCard
          title="xThreat Conceded"
          value={metrics.totalXThreatConceded}
          unit=""
          description="Total threat allowed"
          color="#6B7280"
          showTrend={parseFloat(metrics.totalXThreatConceded) < 0}
        />

        <MetricCard
          title="Formation Stability"
          value={metrics.avgFormationStability}
          unit="%"
          description="Role assignment consistency"
          color="#8B5CF6"
        />
      </div>

      <div className="phase-summary">
        <h4>Phase Distribution</h4>
        <div className="phase-counts">
          {phases && phases.length > 0 && (
            <>
              <div>High Press: {phases.filter(p => p.type === 'high_press').length}</div>
              <div>Defensive Block: {phases.filter(p => p.type === 'defensive_block').length}</div>
              <div>Counter-attack: {phases.filter(p => p.type === 'counter_attack').length}</div>
              <div>Open Play: {phases.filter(p => p.type === 'open_play').length}</div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default MetricPanel