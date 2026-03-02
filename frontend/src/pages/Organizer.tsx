import { useState, useRef } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Alert from '@mui/material/Alert'
import LinearProgress from '@mui/material/LinearProgress'
import FormControlLabel from '@mui/material/FormControlLabel'
import Checkbox from '@mui/material/Checkbox'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import InputLabel from '@mui/material/InputLabel'
import FormControl from '@mui/material/FormControl'
import Chip from '@mui/material/Chip'
import Stack from '@mui/material/Stack'
import VideoFileIcon from '@mui/icons-material/VideoFile'
import DownloadIcon from '@mui/icons-material/Download'
import { API_BASE } from '../api'

const C = { border: '#2A2A2A', dim: '#777', green: '#00FF88', panel: '#111111', text: '#E8E8E8' }

function SectionHeader({ title }: { title: string }) {
  return (
    <Box sx={{ px: 1.5, py: 0.5, borderBottom: `1px solid ${C.border}`, bgcolor: '#0A0A0A' }}>
      <Typography sx={{ fontWeight: 700, letterSpacing: 1.5, color: C.dim, fontSize: 10 }}>{title}</Typography>
    </Box>
  )
}

export default function Organizer() {
  const [file, setFile] = useState<File | null>(null)
  const [format, setFormat] = useState('png')
  const [organize, setOrganize] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const linkRef = useRef<HTMLAnchorElement>(null)

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) { setFile(f); setError(null); setSuccess(null) }
  }

  const handleExtract = async () => {
    if (!file) return
    setLoading(true); setError(null); setSuccess(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('format', format)
      if (organize) form.append('organize', '1')
      const res = await fetch(`${API_BASE}/extract-frames`, { method: 'POST', body: form })
      if (!res.ok) { const err = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(err.detail || res.statusText) }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      if (linkRef.current) { linkRef.current.href = url; linkRef.current.download = `${file.name.replace(/\.[^.]+$/, '')}_frames.zip`; linkRef.current.click() }
      setSuccess('Frames extracted! Download started.')
    } catch (e) { setError(e instanceof Error ? e.message : 'Extraction failed') }
    finally { setLoading(false) }
  }

  return (
    <Box>
      <a ref={linkRef} style={{ display: 'none' }} />
      <Box sx={{ border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', bgcolor: C.panel }}>
        <SectionHeader title="EXTRACT FRAMES FROM VIDEO" />
        <Box sx={{ p: 2 }}>
          <Typography sx={{ fontSize: 12, color: C.dim, mb: 2 }}>
            Select a video file to extract individual frames as PNG or EXR images.
          </Typography>

          {/* Row: Video selection */}
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}>
            <Typography sx={{ color: C.dim, fontWeight: 700, fontSize: 11, minWidth: 60 }}>Video(s):</Typography>
            <Button variant="outlined" size="small" component="label" startIcon={<VideoFileIcon />} sx={{ fontWeight: 600, fontSize: 11 }}>
              Select video…
              <input type="file" hidden accept=".mov,.mp4,.avi,.mkv,.mxf,.webm,.m4v,.mpg,.mpeg" onChange={handleFile} />
            </Button>
            {file && <Chip label={file.name} size="small" onDelete={() => { setFile(null); setSuccess(null) }} />}
          </Stack>

          {/* Row: Options */}
          <Stack direction="row" spacing={3} alignItems="center" sx={{ mb: 2 }}>
            <FormControl size="small" sx={{ minWidth: 130 }}>
              <InputLabel sx={{ fontSize: 12 }}>Output format</InputLabel>
              <Select value={format} onChange={(e) => setFormat(e.target.value)} label="Output format" sx={{ fontSize: 12 }}>
                <MenuItem value="png">PNG</MenuItem>
                <MenuItem value="exr">EXR</MenuItem>
              </Select>
            </FormControl>
            <FormControlLabel
              control={<Checkbox size="small" checked={organize} onChange={(e) => setOrganize(e.target.checked)}
                sx={{ color: C.green, '&.Mui-checked': { color: C.green } }} />}
              label={<Typography sx={{ fontSize: 11 }}>Organize by FPS / bit depth</Typography>}
            />
          </Stack>

          {/* Row: Extract */}
          <Button variant="contained" size="small" onClick={handleExtract} disabled={!file || loading}
            startIcon={<DownloadIcon />} sx={{ fontWeight: 700, fontSize: 11, px: 3 }}>
            {loading ? 'Extracting…' : 'Extract Frames'}
          </Button>

          {loading && <LinearProgress sx={{ mt: 2, '& .MuiLinearProgress-bar': { bgcolor: C.green } }} />}
          {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
          {success && <Alert severity="success" sx={{ mt: 2 }}>{success}</Alert>}
        </Box>
      </Box>

      {/* Output area */}
      <Box sx={{ mt: 1, border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', bgcolor: C.panel }}>
        <SectionHeader title="OUTPUT" />
        <Box sx={{ p: 2, minHeight: 80, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {success ? (
            <Typography sx={{ color: C.green, fontSize: 12 }}>✓ {success}</Typography>
          ) : (
            <Typography sx={{ color: '#333', fontSize: 12 }}>
              Select a video and click "Extract Frames" to begin
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  )
}
