import { useState, useEffect } from 'react'

const useMatchData = (matchId) => {
  const [matchData, setMatchData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadMatchData = async () => {
      setLoading(true)
      setError(null)

      try {
        // Load all JSON files for this match
        const basePath = `/data/${matchId}`

        const [metadata, frames, phases, formations, voronoi, heatmaps] = await Promise.all([
          fetch(`${basePath}/metadata.json`).then(r => r.json()),
          fetch(`${basePath}/frames.json`).then(r => r.json()),
          fetch(`${basePath}/phases.json`).then(r => r.json()),
          fetch(`${basePath}/formations.json`).then(r => r.json()),
          fetch(`${basePath}/pitch_control.json`).then(r => r.json()).catch(() => []),
          fetch(`${basePath}/heatmaps.json`).then(r => r.json()).catch(() => [])
        ])

        setMatchData({
          matchId,
          metadata,
          frames,
          phases,
          formations,
          voronoi,
          heatmaps
        })
      } catch (err) {
        console.error('Error loading match data:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    if (matchId) {
      loadMatchData()
    }
  }, [matchId])

  return { matchData, loading, error }
}

export default useMatchData