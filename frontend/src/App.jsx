import { useState, useEffect } from 'react'
import Timeline from './components/Timeline'
import PitchCanvas from './components/PitchCanvas'
import MetricPanel from './components/MetricPanel'
import FormationComparisonPanel from './components/FormationComparisonPanel'
import PhaseFilter from './components/PhaseFilter'
import useMatchData from './hooks/useMatchData'
import './App.css'

function App() {
  const [selectedMatch] = useState('J03WN1')
  const [currentFrame, setCurrentFrame] = useState(0)
  const [phaseFilter, setPhaseFilter] = useState(new Set(['all']))
  const [selectedPhase, setSelectedPhase] = useState(null)
  const [selectedTeam, setSelectedTeam] = useState(null) // null = both, or team id
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [overlayMode, setOverlayMode] = useState('shape_graph') // 'none', 'convex_hull', 'shape_graph'

  const {
    matchData,
    loading,
    error
  } = useMatchData(selectedMatch)

  useEffect(() => {
    if (isPlaying && matchData?.frames) {
      const interval = setInterval(() => {
        setCurrentFrame(prev => {
          const next = prev + 1
          return next >= matchData.frames.length ? 0 : next
        })
      }, 250 / playbackSpeed) // 4Hz playback

      return () => clearInterval(interval)
    }
  }, [isPlaying, playbackSpeed, matchData])

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner">Loading match data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">Error: {error}</div>
      </div>
    )
  }

  if (!matchData) {
    return (
      <div className="error-container">
        <div className="error-message">No match data available</div>
      </div>
    )
  }

  const currentFrameData = matchData.frames?.[currentFrame] || null
  const currentTime = currentFrameData?.t || 0

  // Find the corresponding voronoi data by frame_id
  const currentVoronoiData = matchData.voronoi?.find(v =>
    v.frame_id === currentFrameData?.frame_id
  ) || null

  // Build team name lookup from metadata
  const teams = matchData.metadata?.teams || []
  const teamNameMap = {}
  teams.forEach(t => { teamNameMap[t.id] = t.name })
  const teamIds = teams.map(t => t.id)

  // Auto-select first team if none selected yet
  if (selectedTeam === null && teamIds.length > 0) {
    // Don't call setState during render - use effect below
  }

  // Filter phases based on phase type filter AND team filter
  const filteredByType = phaseFilter.has('all')
    ? matchData.phases
    : matchData.phases?.filter(p => phaseFilter.has(p.type))

  const visiblePhases = selectedTeam
    ? filteredByType?.filter(p => p.team === selectedTeam)
    : filteredByType

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>Soccer Phase Analytics Dashboard</h1>
        <div className="match-info">
          <span>Match: {teams.map(t => t.name).join(' vs ')}</span>
          <span>Time: {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')}</span>
        </div>
      </header>

      <div className="controls-row">
        <PhaseFilter
          phaseFilter={phaseFilter}
          setPhaseFilter={setPhaseFilter}
        />

        <div className="team-selector">
          <h3>Team View</h3>
          <div className="team-selector-buttons">
            <button
              className={`team-btn ${!selectedTeam ? 'active' : ''}`}
              onClick={() => setSelectedTeam(null)}
            >
              Both
            </button>
            {teams.map(t => (
              <button
                key={t.id}
                className={`team-btn ${selectedTeam === t.id ? 'active' : ''}`}
                onClick={() => setSelectedTeam(t.id)}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Show one timeline per team when "Both" is selected, or one for selected team */}
      {(!selectedTeam ? teamIds : [selectedTeam]).map(teamId => (
        <Timeline
          key={teamId}
          teamName={teamNameMap[teamId]}
          phases={filteredByType?.filter(p => p.team === teamId)}
          currentTime={currentTime}
          duration={matchData.frames?.[matchData.frames.length - 1]?.t || 90 * 60}
          onTimeChange={(time) => {
            const frameIndex = matchData.frames.findIndex(f => f.t >= time)
            setCurrentFrame(frameIndex >= 0 ? frameIndex : 0)
          }}
          selectedPhase={selectedPhase}
          onPhaseSelect={setSelectedPhase}
        />
      ))}

      <div className="dashboard-grid">
        <div className="visualization-panel">
          <PitchCanvas
            frame={currentFrameData}
            voronoi={currentVoronoiData}
            formations={matchData.formations}
            selectedPhase={selectedPhase}
            overlayMode={overlayMode}
          />

          <div className="playback-controls">
            <button onClick={() => setIsPlaying(!isPlaying)}>
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <label>
              Speed:
              <select value={playbackSpeed} onChange={e => setPlaybackSpeed(Number(e.target.value))}>
                <option value={0.5}>0.5x</option>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={4}>4x</option>
              </select>
            </label>
            <label>
              Overlay:
              <select value={overlayMode} onChange={e => setOverlayMode(e.target.value)}>
                <option value="none">None</option>
                <option value="shape_graph">Shape Graph</option>
                <option value="convex_hull">Pitch Control</option>
              </select>
            </label>
          </div>
        </div>

        <div className="metrics-panel">
          <MetricPanel
            phases={visiblePhases}
            currentPhase={visiblePhases?.find(p =>
              currentTime >= p.start && currentTime <= p.end
            )}
            formations={matchData.formations}
            teamNameMap={teamNameMap}
          />
          <FormationComparisonPanel
            formations={matchData.formations}
            phases={visiblePhases}
            selectedTeam={selectedTeam || teamIds[0]}
            teamNameMap={teamNameMap}
          />
        </div>
      </div>
    </div>
  )
}

export default App