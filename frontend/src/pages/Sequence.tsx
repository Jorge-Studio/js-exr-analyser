import { useState, useRef, useEffect, useCallback } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Alert from '@mui/material/Alert'
import LinearProgress from '@mui/material/LinearProgress'
import Slider from '@mui/material/Slider'
import Stack from '@mui/material/Stack'
import Chip from '@mui/material/Chip'
import TextField from '@mui/material/TextField'
import IconButton from '@mui/material/IconButton'
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import PauseIcon from '@mui/icons-material/Pause'
import SkipPreviousIcon from '@mui/icons-material/SkipPrevious'
import SkipNextIcon from '@mui/icons-material/SkipNext'
import ImageIcon from '@mui/icons-material/Image'
import { API_BASE } from '../api'

const C = { border: '#2A2A2A', dim: '#777', green: '#00FF88', panel: '#111111', text: '#E8E8E8' }

function SH({ title }: { title: string }) {
  return (
    <Box sx={{ px: 1.5, py: 0.5, borderBottom: `1px solid ${C.border}`, bgcolor: '#0A0A0A' }}>
      <Typography sx={{ fontWeight: 700, letterSpacing: 1.5, color: C.dim, fontSize: 10 }}>{title}</Typography>
    </Box>
  )
}

interface Sess { session_id: string; frame_count: number; filenames: string[] }

export default function Sequence() {
  const [session, setSession] = useState<Sess | null>(null)
  const [idx, setIdx] = useState(0)
  const [img, setImg] = useState<string | null>(null)
  const [fname, setFname] = useState('')
  const [fps, setFps] = useState(24)
  const [exposure, setExposure] = useState(0)
  const [gamma, setGamma] = useState(2.2)
  const [playing, setPlaying] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)
  const idxRef = useRef(0)

  const loadFrame = useCallback(async (i: number, sid: string, exp = 0, gam = 2.2) => {
    try {
      const r = await fetch(`${API_BASE}/sequence/${sid}/frame/${i}?exposure=${exp}&gamma=${gam}`)
      if (!r.ok) return
      const d = await r.json()
      setImg(d.preview_b64); setFname(d.filename)
    } catch { /* skip */ }
  }, [])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files; if (!files || !files.length) return
    setUploading(true); setError(null)
    try {
      const form = new FormData()
      for (let i = 0; i < files.length; i++) form.append('files', files[i])
      const r = await fetch(`${API_BASE}/sequence/upload`, { method: 'POST', body: form })
      if (!r.ok) { const err = await r.json().catch(() => ({ detail: r.statusText })); throw new Error(err.detail || 'Upload failed') }
      const data: Sess = await r.json()
      setSession(data); setIdx(0); idxRef.current = 0
      await loadFrame(0, data.session_id, exposure, gamma)
    } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed') }
    finally { setUploading(false) }
  }

  const go = (i: number) => {
    if (!session) return
    const c = Math.max(0, Math.min(i, session.frame_count - 1))
    setIdx(c); idxRef.current = c; loadFrame(c, session.session_id, exposure, gamma)
  }

  const togglePlay = () => {
    if (!session) return
    if (playing) { if (timer.current) clearInterval(timer.current); timer.current = null; setPlaying(false) }
    else {
      setPlaying(true)
      timer.current = setInterval(() => {
        if (!session) return
        const n = (idxRef.current + 1) % session.frame_count
        idxRef.current = n; setIdx(n); loadFrame(n, session.session_id, exposure, gamma)
      }, 1000 / fps)
    }
  }

  useEffect(() => () => { if (timer.current) clearInterval(timer.current) }, [])
  useEffect(() => {
    if (playing && timer.current) {
      clearInterval(timer.current)
      timer.current = setInterval(() => {
        if (!session) return
        const n = (idxRef.current + 1) % session.frame_count
        idxRef.current = n; setIdx(n); loadFrame(n, session.session_id, exposure, gamma)
      }, 1000 / fps)
    }
  }, [fps, playing, session, exposure, gamma, loadFrame])

  const applyGrading = () => { if (session) loadFrame(idx, session.session_id, exposure, gamma) }

  return (
    <Box>
      {/* Toolbar */}
      <Stack direction="row" spacing={1} sx={{ mb: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        <Button variant="contained" size="small" component="label" startIcon={<FolderOpenIcon />} sx={{ fontWeight: 700, fontSize: 11, px: 2 }}>
          Load EXR Folder<input type="file" hidden accept=".exr" multiple onChange={handleUpload} />
        </Button>
        {session && <Chip label={`${session.frame_count} frames`} size="small" sx={{ bgcolor: '#1a1a1a' }} />}
        {uploading && <Typography sx={{ fontSize: 11, color: C.dim }}>Uploading…</Typography>}
      </Stack>
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
      {uploading && <LinearProgress sx={{ mb: 1, '& .MuiLinearProgress-bar': { bgcolor: C.green } }} />}

      <Box sx={{ display: 'flex', gap: 1, flexDirection: { xs: 'column', md: 'row' } }}>
        {/* LEFT: Preview + playback */}
        <Box sx={{ flex: '1 1 70%' }}>
          <Box sx={{ mb: 1, border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', bgcolor: C.panel }}>
            <SH title="PREVIEW" />
            <Box sx={{ p: 0.5, bgcolor: '#000', minHeight: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              {img ? (
                <Box component="img" src={`data:image/jpeg;base64,${img}`} alt={`Frame ${idx}`}
                  sx={{ maxWidth: '100%', maxHeight: 360, objectFit: 'contain' }} />
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }} component="label">
                  <ImageIcon sx={{ fontSize: 36, color: '#2A2A2A', mb: 1 }} />
                  <Typography sx={{ color: '#444', fontSize: 12 }}>Load EXR files to preview</Typography>
                  <input type="file" hidden accept=".exr" multiple onChange={handleUpload} />
                </Box>
              )}
            </Box>
          </Box>

          {/* Playback */}
          <Box sx={{ border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', bgcolor: C.panel }}>
            <SH title="PLAYBACK" />
            <Box sx={{ px: 1.5, py: 1 }}>
              <Slider value={idx} min={0} max={Math.max((session?.frame_count ?? 1) - 1, 0)}
                onChange={(_, v) => go(v as number)} disabled={!session}
                sx={{ color: C.green, mb: 0.5, '& .MuiSlider-thumb': { width: 12, height: 12 } }} />
              <Stack direction="row" spacing={0.5} alignItems="center" justifyContent="space-between">
                <Stack direction="row" spacing={0}>
                  <IconButton size="small" onClick={() => go(0)} disabled={!session} sx={{ color: C.text }}><SkipPreviousIcon sx={{ fontSize: 18 }} /></IconButton>
                  <IconButton size="small" onClick={togglePlay} disabled={!session} sx={{ color: C.green }}>
                    {playing ? <PauseIcon sx={{ fontSize: 20 }} /> : <PlayArrowIcon sx={{ fontSize: 20 }} />}
                  </IconButton>
                  <IconButton size="small" onClick={() => go((session?.frame_count ?? 1) - 1)} disabled={!session} sx={{ color: C.text }}><SkipNextIcon sx={{ fontSize: 18 }} /></IconButton>
                </Stack>
                <Typography sx={{ color: C.dim, fontSize: 10 }}>
                  Frame {idx + 1} / {session?.frame_count ?? 0}{fname ? ` — ${fname}` : ''}
                </Typography>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <Typography sx={{ color: C.dim, fontSize: 10 }}>FPS:</Typography>
                  <TextField value={fps} onChange={(e) => setFps(Math.max(1, parseInt(e.target.value) || 1))}
                    size="small" type="number" disabled={!session}
                    sx={{ width: 50, '& input': { py: 0.3, px: 0.5, fontSize: 11 } }} />
                </Stack>
              </Stack>
            </Box>
          </Box>
        </Box>

        {/* RIGHT: Grading + info */}
        <Box sx={{ flex: '0 0 200px' }}>
          <Box sx={{ border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', bgcolor: C.panel, mb: 1 }}>
            <SH title="GRADING" />
            <Box sx={{ p: 1.5 }}>
              <Typography sx={{ color: C.dim, fontSize: 9, mb: 0.3 }}>Exposure ({exposure > 0 ? '+' : ''}{exposure.toFixed(1)})</Typography>
              <Slider value={exposure} min={-5} max={5} step={0.1} disabled={!session}
                onChange={(_, v) => setExposure(v as number)} onChangeCommitted={applyGrading}
                size="small" sx={{ color: C.green, mb: 1.5 }} />
              <Typography sx={{ color: C.dim, fontSize: 9, mb: 0.3 }}>Gamma ({gamma.toFixed(2)})</Typography>
              <Slider value={gamma} min={0.2} max={4.0} step={0.05} disabled={!session}
                onChange={(_, v) => setGamma(v as number)} onChangeCommitted={applyGrading}
                size="small" sx={{ color: C.green, mb: 1.5 }} />
              <Button variant="outlined" size="small" fullWidth disabled={!session}
                onClick={() => { setExposure(0); setGamma(2.2); if (session) loadFrame(idx, session.session_id, 0, 2.2) }}
                sx={{ fontWeight: 600, fontSize: 10 }}>Reset Grading</Button>
            </Box>
          </Box>

          <Box sx={{ border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', bgcolor: C.panel }}>
            <SH title="SEQUENCE INFO" />
            <Box sx={{ p: 1 }}>
              {[
                ['Frames', session?.frame_count ?? '—'],
                ['Duration', session ? `${(session.frame_count / fps).toFixed(2)}s @ ${fps}fps` : '—'],
                ['Current', fname || '—'],
              ].map(([l, v]) => (
                <Box key={l as string} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.3 }}>
                  <Typography sx={{ color: C.dim, fontSize: 10 }}>{l}</Typography>
                  <Typography sx={{ color: C.text, fontSize: 10, fontWeight: 600 }}>{v}</Typography>
                </Box>
              ))}
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
