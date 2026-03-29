import MetricCard from './MetricCard'
import './MetricPanel.css'

const MetricPanel = ({ phases, currentPhase, teamNameMap = {} }) => {
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

    // Shape metrics (Pracxa et al. 2022)
    const avgTeamLength = phases.reduce((sum, p) =>
      sum + (p.team_length || 0), 0) / phases.length * 105 // Convert to meters

    const avgTeamWidth = phases.reduce((sum, p) =>
      sum + (p.team_width || 0), 0) / phases.length * 68 // Convert to meters

    const avgLPWRatio = phases.reduce((sum, p) =>
      sum + (p.lpw_ratio || 0), 0) / phases.length

    const avgStretchingIndex = phases.reduce((sum, p) =>
      sum + (p.stretching_index || 0), 0) / phases.length * 105 // Approximate to meters

    return {
      avgDefensiveLine: avgDefensiveLine.toFixed(1),
      avgCompactness: avgCompactness.toFixed(0),
      avgPPDA: avgPPDA.toFixed(1),
      avgTeamLength: avgTeamLength.toFixed(1),
      avgTeamWidth: avgTeamWidth.toFixed(1),
      avgLPWRatio: avgLPWRatio.toFixed(2),
      avgStretchingIndex: avgStretchingIndex.toFixed(1),
      totalXThreatGained: totalXThreatGained.toFixed(3),
      totalXThreatConceded: totalXThreatConceded.toFixed(3)
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
            {currentPhase.type.replace(/_/g, ' ')} - {teamNameMap[currentPhase.team] || currentPhase.team}
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
          title="Team Length"
          value={metrics.avgTeamLength}
          unit="m"
          description="Longitudinal spread"
          color="#0891B2"
        />

        <MetricCard
          title="Team Width"
          value={metrics.avgTeamWidth}
          unit="m"
          description="Lateral spread"
          color="#7C3AED"
        />

        <MetricCard
          title="LPW Ratio"
          value={metrics.avgLPWRatio}
          unit=""
          description=">1 = deep/narrow, <1 = wide"
          color="#DB2777"
        />

        <MetricCard
          title="Stretching Index"
          value={metrics.avgStretchingIndex}
          unit="m"
          description="Mean distance from centroid"
          color="#EA580C"
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

      </div>

      <div className="phase-summary">
        <h4>Phase Distribution</h4>
        <div className="phase-counts">
          {phases && phases.length > 0 && (
            <>
              <div style={{color: '#10B981'}}>Attacking: {phases.filter(p => p.type === 'attacking').length}</div>
              <div style={{color: '#06B6D4'}}>Build-up: {phases.filter(p => p.type === 'build_up').length}</div>
              <div style={{color: '#DC2626'}}>High Press: {phases.filter(p => p.type === 'high_press').length}</div>
              <div style={{color: '#8B5CF6'}}>Mid Block: {phases.filter(p => p.type === 'mid_block').length}</div>
              <div style={{color: '#2563EB'}}>Defensive Block: {phases.filter(p => p.type === 'defensive_block').length}</div>
              <div style={{color: '#F59E0B'}}>Counter-attack: {phases.filter(p => p.type === 'counter_attack').length}</div>
              <div style={{color: '#9CA3AF'}}>Open Play: {phases.filter(p => p.type === 'open_play').length}</div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default MetricPanel