import './PhaseFilter.css'

const PhaseFilter = ({ phaseFilter, setPhaseFilter }) => {
  const phaseTypes = [
    { value: 'all', label: 'All Phases', color: '#6B7280' },
    { value: 'high_press', label: 'High Press', color: '#DC2626' },
    { value: 'defensive_block', label: 'Defensive Block', color: '#2563EB' },
    { value: 'counter_attack', label: 'Counter-attack', color: '#F59E0B' },
    { value: 'open_play', label: 'Open Play', color: '#9CA3AF' }
  ]

  const togglePhase = (phase) => {
    const newFilter = new Set(phaseFilter)

    if (phase === 'all') {
      // Toggle all on/off
      if (newFilter.has('all')) {
        newFilter.clear()
      } else {
        newFilter.clear()
        newFilter.add('all')
      }
    } else {
      // Toggle individual phase
      newFilter.delete('all')
      if (newFilter.has(phase)) {
        newFilter.delete(phase)
      } else {
        newFilter.add(phase)
      }

      // If nothing selected, select all
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
        {phaseTypes.map(type => (
          <button
            key={type.value}
            className={`phase-filter-btn ${phaseFilter.has(type.value) ? 'active' : ''}`}
            style={{
              backgroundColor: phaseFilter.has(type.value) ? type.color : 'transparent',
              borderColor: type.color,
              color: phaseFilter.has(type.value) ? 'white' : type.color
            }}
            onClick={() => togglePhase(type.value)}
          >
            {type.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default PhaseFilter