import { useState } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Tabs from '@mui/material/Tabs'
import Tab from '@mui/material/Tab'
import Organizer from './pages/Organizer'
import Analyzer from './pages/Analyzer'
import Sequence from './pages/Sequence'
import Shots from './pages/Shots'

const navItems = [
  { path: '/', label: 'Organizer' },
  { path: '/analyzer', label: 'Analyzer' },
  { path: '/sequence', label: 'Sequence' },
  { path: '/shots', label: 'Shots' },
]

function pathToTab(p: string) {
  const i = navItems.findIndex(n => n.path === p)
  return i >= 0 ? i : 0
}

export default function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const [tab, setTab] = useState(pathToTab(location.pathname))

  const handleTab = (_: React.SyntheticEvent, v: number) => {
    setTab(v)
    navigate(navItems[v].path)
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#0D0D0D' }}>
      {/* Title bar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', px: 2, py: 0.8,
        bgcolor: '#0D0D0D', borderBottom: '1px solid #1A1A1A',
      }}>
        <Typography sx={{ fontWeight: 800, letterSpacing: 2.5, fontSize: 13, color: '#E8E8E8', mr: 1.5 }}>
          EXR ANALYZER
        </Typography>
        <Typography sx={{ color: '#555', fontSize: 10, letterSpacing: 0.5 }}>
          — Cinema VFX Diagnostic Tool v1.0.0
        </Typography>
      </Box>

      {/* Tab bar */}
      <Tabs value={tab} onChange={handleTab} variant="standard" sx={{
        minHeight: 32, borderBottom: '1px solid #2A2A2A', px: 1, bgcolor: '#0D0D0D',
        '& .MuiTab-root': {
          minHeight: 32, py: 0.5, px: 2, fontWeight: 600, fontSize: 12,
          textTransform: 'none', color: '#666',
          '&.Mui-selected': { color: '#E8E8E8' },
        },
        '& .MuiTabs-indicator': { backgroundColor: '#00FF88', height: 2 },
      }}>
        {navItems.map(n => <Tab key={n.path} label={n.label} />)}
      </Tabs>

      {/* Content */}
      <Box sx={{ p: { xs: 1, sm: 1.5 } }}>
        <Routes>
          <Route path="/" element={<Organizer />} />
          <Route path="/analyzer" element={<Analyzer />} />
          <Route path="/sequence" element={<Sequence />} />
          <Route path="/shots" element={<Shots />} />
        </Routes>
      </Box>
    </Box>
  )
}
