import { useState, useEffect } from 'react'
import Timeline from './components/Timeline'
import PitchCanvas from './components/PitchCanvas'
import MetricPanel from './components/MetricPanel'
import PhaseFilter from './components/PhaseFilter'
import useMatchData from './hooks/useMatchData'
import './App.css'

function App() {
  const [selectedMatch] = useState('J03WN1')
  const [currentFrame, setCurrentFrame] = useState(0)
  const [phaseFilter, setPhaseFilter] = useState(new Set(['all']))
  const [selectedPhase, setSelectedPhase] = useState(null)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [isPlaying, setIsPlaying] = useState(false)

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

  // Filter phases based on selection
  const visiblePhases = phaseFilter.has('all')
    ? matchData.phases
    : matchData.phases?.filter(p => phaseFilter.has(p.type))

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>Soccer Phase Analytics Dashboard</h1>
        <div className="match-info">
          <span>Match: {selectedMatch}</span>
          <span>Time: {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')}</span>
        </div>
      </header>

      <PhaseFilter
        phaseFilter={phaseFilter}
        setPhaseFilter={setPhaseFilter}
      />

      <Timeline
        phases={visiblePhases}
        currentTime={currentTime}
        duration={matchData.frames?.[matchData.frames.length - 1]?.t || 90 * 60}
        onTimeChange={(time) => {
          const frameIndex = matchData.frames.findIndex(f => f.t >= time)
          setCurrentFrame(frameIndex >= 0 ? frameIndex : 0)
        }}
        selectedPhase={selectedPhase}
        onPhaseSelect={setSelectedPhase}
      />

      <div className="dashboard-grid">
        <div className="visualization-panel">
          <PitchCanvas
            frame={currentFrameData}
            voronoi={currentVoronoiData}
            formations={matchData.formations}
            selectedPhase={selectedPhase}
            showVoronoi={true}
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
          </div>
        </div>

        <div className="metrics-panel">
          <MetricPanel
            phases={visiblePhases}
            currentPhase={visiblePhases?.find(p =>
              currentTime >= p.start && currentTime <= p.end
            )}
            formations={matchData.formations}
          />
        </div>
      </div>
    </div>
  )
}

export default App