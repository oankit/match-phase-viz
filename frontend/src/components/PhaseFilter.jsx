import './PhaseFilter.css'

const PhaseFilter = ({ phaseFilter, setPhaseFilter }) => {
  const phaseTypes = [
    { value: 'all', label: 'All Phases', color: null },
    { value: 'attacking', label: 'Attacking', color: '#2d9a4e' },
    { value: 'build_up', label: 'Build-up', color: '#4a90d9' },
    { value: 'high_press', label: 'High Press', color: '#d94f4f' },
    { value: 'mid_block', label: 'Mid Block', color: '#e8a838' },
    { value: 'defensive_block', label: 'Def. Block', color: '#7b5ea7' },
    { value: 'counter_attack', label: 'Counter', color: '#e06b9a' },
    { value: 'open_play', label: 'Open Play', color: '#a8a29e' },
  ]

  const togglePhase = (phase) => {
    const newFilter = new Set(phaseFilter)

    if (phase === 'all') {
      if (newFilter.has('all')) {
        newFilter.clear()
      } else {
        newFilter.clear()
        newFilter.add('all')
      }
    } else {
      newFilter.delete('all')
      if (newFilter.has(phase)) {
        newFilter.delete(phase)
      } else {
        newFilter.add(phase)
      }

      if (newFilter.size === 0) {
        newFilter.add('all')
      }
    }

    setPhaseFilter(newFilter)
  }

  return (
    <div className="phase-filter-container">
      <h3>Phase Filter</h3>
      <div className="phase-filter-buttons">
        {phaseTypes.map(type => {
          const isActive = phaseFilter.has(type.value)
          return (
            <button
              key={type.value}
              className={`phase-filter-btn ${isActive ? 'active' : ''}`}
              onClick={() => togglePhase(type.value)}
            >
              {type.color && (
                <span
                  className="phase-dot"
                  style={{ backgroundColor: type.color }}
                />
              )}
              {type.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default PhaseFilter