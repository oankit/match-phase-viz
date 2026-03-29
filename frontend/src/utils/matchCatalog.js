const TEAM_COLORS = {
  'DFL-CLU-00000S': '#1560A4', // VfL Bochum 1848
  'DFL-CLU-00000B': '#E32221', // Bayer 04 Leverkusen
  'DFL-CLU-000008': '#ED1C24', // 1. FC Koln
  'DFL-CLU-00000G': '#DC052D', // FC Bayern Munchen
  'DFL-CLU-00000P': '#E30613', // Fortuna Dusseldorf
  'DFL-CLU-000011': '#D32F2F', // SSV Jahn Regensburg
  'DFL-CLU-00000Q': '#003F87', // F.C. Hansa Rostock
  'DFL-CLU-000005': '#8B1A2B', // 1. FC Nurnberg
  'DFL-CLU-00000H': '#5D4037', // FC St. Pauli
  'DFL-CLU-00000I': '#E30613', // 1. FC Kaiserslautern
}

const TEAM_BADGES = {
  'DFL-CLU-00000S': '/assets/VfL Bochum 1848.png',
  'DFL-CLU-00000B': '/assets/Bayer_04_Leverkusen.png',
  'DFL-CLU-000008': '/assets/FC Koln.png',
  'DFL-CLU-00000G': '/assets/Bayern Munich.png',
  'DFL-CLU-00000P': '/assets/Fortuna D\u00fcsseldorf.png',
  'DFL-CLU-000011': '/assets/Jahn_Regensburg FC.png',
  'DFL-CLU-00000Q': '/assets/FC Hansa Rostock.png',
  'DFL-CLU-000005': '/assets/FC N\u00fcrnberg.png',
  'DFL-CLU-00000H': '/assets/FC St. Pauli.png',
  'DFL-CLU-00000I': '/assets/FC Kaiserslautern.png',
}

const MATCH_CATALOG = [
  {
    matchId: 'J03WN1',
    competition: 'Bundesliga',
    matchDay: 34,
    season: '2022/2023',
    date: '2023-05-27',
    kickoff: '13:31',
    stadium: 'Vonovia Ruhrstadion',
    result: '3:0',
    homeTeam: {
      id: 'DFL-CLU-00000S',
      name: 'VfL Bochum 1848',
    },
    awayTeam: {
      id: 'DFL-CLU-00000B',
      name: 'Bayer 04 Leverkusen',
    },
    hasData: true,
  },
  {
    matchId: 'J03WMX',
    competition: 'Bundesliga',
    matchDay: 34,
    season: '2022/2023',
    date: '2023-05-27',
    kickoff: '13:30',
    stadium: 'RheinEnergieSTADION',
    result: '1:2',
    homeTeam: {
      id: 'DFL-CLU-000008',
      name: '1. FC Koln',
    },
    awayTeam: {
      id: 'DFL-CLU-00000G',
      name: 'FC Bayern Munchen',
    },
    hasData: false,
  },
  {
    matchId: 'J03WOH',
    competition: '2. Bundesliga',
    matchDay: 6,
    season: '2022/2023',
    date: '2022-08-26',
    kickoff: '16:32',
    stadium: 'Merkur Spielarena',
    result: '4:0',
    homeTeam: {
      id: 'DFL-CLU-00000P',
      name: 'Fortuna Dusseldorf',
    },
    awayTeam: {
      id: 'DFL-CLU-000011',
      name: 'SSV Jahn Regensburg',
    },
    hasData: false,
  },
  {
    matchId: 'J03WOY',
    competition: '2. Bundesliga',
    matchDay: 8,
    season: '2022/2023',
    date: '2022-09-10',
    kickoff: '18:31',
    stadium: 'Merkur Spielarena',
    result: '3:1',
    homeTeam: {
      id: 'DFL-CLU-00000P',
      name: 'Fortuna Dusseldorf',
    },
    awayTeam: {
      id: 'DFL-CLU-00000Q',
      name: 'F.C. Hansa Rostock',
    },
    hasData: false,
  },
  {
    matchId: 'J03WPY',
    competition: '2. Bundesliga',
    matchDay: 12,
    season: '2022/2023',
    date: '2022-10-15',
    kickoff: '11:01',
    stadium: 'Merkur Spielarena',
    result: '0:1',
    homeTeam: {
      id: 'DFL-CLU-00000P',
      name: 'Fortuna Dusseldorf',
    },
    awayTeam: {
      id: 'DFL-CLU-000005',
      name: '1. FC Nurnberg',
    },
    hasData: false,
  },
  {
    matchId: 'J03WQQ',
    competition: '2. Bundesliga',
    matchDay: 15,
    season: '2022/2023',
    date: '2022-11-05',
    kickoff: '12:01',
    stadium: 'Merkur Spielarena',
    result: '1:0',
    homeTeam: {
      id: 'DFL-CLU-00000P',
      name: 'Fortuna Dusseldorf',
    },
    awayTeam: {
      id: 'DFL-CLU-00000H',
      name: 'FC St. Pauli',
    },
    hasData: false,
  },
  {
    matchId: 'J03WR9',
    competition: '2. Bundesliga',
    matchDay: 17,
    season: '2022/2023',
    date: '2022-11-11',
    kickoff: '17:31',
    stadium: 'Merkur Spielarena',
    result: '1:2',
    homeTeam: {
      id: 'DFL-CLU-00000P',
      name: 'Fortuna Dusseldorf',
    },
    awayTeam: {
      id: 'DFL-CLU-00000I',
      name: '1. FC Kaiserslautern',
    },
    hasData: false,
  },
]

export function getMatchInfo(matchId) {
  return MATCH_CATALOG.find(m => m.matchId === matchId) || null
}

export function getTeamColor(teamId) {
  return TEAM_COLORS[teamId] || '#666666'
}

export function getTeamBadge(teamId) {
  return TEAM_BADGES[teamId] || null
}

export function formatMatchDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export { MATCH_CATALOG, TEAM_COLORS, TEAM_BADGES }
