import { useState, useEffect } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Chip from '@mui/material/Chip'
import Button from '@mui/material/Button'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { API_BASE } from '../api'

const C = { border: '#333333', dim: '#888888', green: '#00FF88', panel: '#111111', text: '#E8E8E8', red: '#FF4444', blue: '#4488FF' }

interface Shot {
  id: string
  label: string
  time_range: string
  notes: string
}

interface VideoResult {
  filename: string
  width: number
  height: number
  filesize_mb: number
  compression: string
  native_type: string
  encoding: string
  eff_bits: number
  above_1_pct: number
  rating: string
  avg_unique: number
  range_min: number
  range_max: number
  avg_step_ratio: number
  preview_b64: string
  results: Record<string, { unique_count: number; min: number; max: number; mean: number }>
  fps?: number
  duration?: number
  nb_frames?: number
}

function SectionHeader({ title }: { title: string }) {
  return (
    <Box sx={{ px: 1.5, py: 0.75, borderBottom: `1px solid ${C.border}`, bgcolor: '#0F0F0F' }}>
      <Typography variant="caption" sx={{ fontWeight: 700, letterSpacing: 1.5, color: C.dim, fontSize: '0.7rem' }}>
        {title}
      </Typography>
    </Box>
  )
}

function InfoRow({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.4, px: 1, borderBottom: `1px solid ${C.border}`, '&:last-child': { borderBottom: 'none' } }}>
      <Typography variant="caption" sx={{ color: C.dim, fontSize: '0.65rem' }}>{label}</Typography>
      <Typography variant="caption" sx={{ fontWeight: 600, fontSize: '0.65rem', color: accent ? C.green : C.text }}>{value}</Typography>
    </Box>
  )
}

export default function Shots() {
  const [shots, setShots] = useState<Shot[]>([])
  const [selected, setSelected] = useState<Shot | null>(null)
  const [loadingShots, setLoadingShots] = useState(true)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [videoResult, setVideoResult] = useState<VideoResult | null>(null)
  const [videoError, setVideoError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/shots`)
      .then((r) => r.json())
      .then((data) => {
        setShots(data.shots || [])
        if (data.shots?.length) setSelected(data.shots[0])
      })
      .catch(() => setShots([]))
      .finally(() => setLoadingShots(false))
  }, [])

  const handleShotSelect = (s: Shot) => {
    setSelected(s)
    setVideoFile(null)
    setVideoResult(null)
    setVideoError(null)
  }

  const handleVideoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setVideoFile(f)
    setAnalyzing(true)
    setVideoError(null)
    setVideoResult(null)
    try {
      const form = new FormData()
      form.append('file', f)
      const res = await fetch(`${API_BASE}/analyze-video`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || res.statusText)
      }
      const data = await res.json()
      setVideoResult(data as VideoResult)
    } catch (e) {
      setVideoError(e instanceof Error ? e.message : 'Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <Box sx={{ display: 'flex', gap: 1.5, flexDirection: { xs: 'column', md: 'row' }, minHeight: 'calc(100vh - 120px)' }}>
      {/* ── Left: Shot list ────────────────────────────────── */}
      <Box sx={{ flex: '0 0 240px' }}>
        <Paper sx={{ border: `1px solid ${C.border}`, borderRadius: 1, overflow: 'hidden', bgcolor: C.panel }}>
          <SectionHeader title="SUBSECTIONS" />
          {loadingShots ? (
            <Box sx={{ p: 2, textAlign: 'center' }}><CircularProgress size={20} /></Box>
          ) : (
            <List dense sx={{ maxHeight: 'calc(100vh - 180px)', overflow: 'auto', p: 0.5 }}>
              {shots.map((s) => (
                <ListItemButton
                  key={s.id}
                  selected={selected?.id === s.id}
                  onClick={() => handleShotSelect(s)}
                  sx={{ borderRadius: 1, mb: 0.25, py: 0.5 }}
                >
                  <ListItemText
                    primary={s.label}
                    secondary={s.time_range}
                    primaryTypographyProps={{ fontWeight: 600, fontSize: '0.75rem' }}
                    secondaryTypographyProps={{ fontSize: '0.6rem' }}
                  />
                </ListItemButton>
              ))}
            </List>
          )}
        </Paper>
      </Box>

      {/* ── Right: Shot detail ─────────────────────────────── */}
      <Box sx={{ flex: 1 }}>
        {selected && (
          <Box>
            {/* Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem' }}>{selected.label}</Typography>
              <Chip label={selected.time_range} size="small" variant="outlined" />
            </Box>

            <Box sx={{ display: 'flex', gap: 1.5, flexDirection: { xs: 'column', lg: 'row' } }}>
              {/* Left column: Notes + Video */}
              <Box sx={{ flex: '1 1 55%' }}>
                {/* Notes */}
                <Paper sx={{ mb: 1.5, border: `1px solid ${C.border}`, borderRadius: 1, overflow: 'hidden', bgcolor: C.panel }}>
                  <SectionHeader title="NOTES (FROM FEEDBACK)" />
                  <Box sx={{ p: 1.5, maxHeight: 180, overflow: 'auto' }}>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontSize: '0.72rem', lineHeight: 1.6 }}>
                      {selected.notes || 'No notes available for this shot.'}
                    </Typography>
                  </Box>
                </Paper>

                {/* Video upload */}
                <Paper sx={{ mb: 1.5, border: `1px solid ${C.border}`, borderRadius: 1, overflow: 'hidden', bgcolor: C.panel }}>
                  <SectionHeader title="VIDEO" />
                  <Box sx={{ p: 1.5 }}>
                    <Button variant="outlined" size="small" component="label" startIcon={<UploadFileIcon />}
                      sx={{ fontWeight: 600, fontSize: '0.72rem', mb: 1 }}>
                      Upload video for this shot
                      <input type="file" hidden accept=".mov,.mp4,.avi,.mkv,.mxf,.webm" onChange={handleVideoUpload} />
                    </Button>
                    {videoFile && <Chip label={videoFile.name} size="small" sx={{ ml: 1 }} />}
                    {analyzing && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                        <CircularProgress size={16} sx={{ color: C.green }} />
                        <Typography variant="caption" color="text.secondary">Analyzing…</Typography>
                      </Box>
                    )}
                    {videoError && <Alert severity="error" sx={{ mt: 1 }}>{videoError}</Alert>}

                    {/* Preview */}
                    {videoResult?.preview_b64 && (
                      <Box sx={{ mt: 1.5, bgcolor: '#000', borderRadius: 0.5, overflow: 'hidden' }}>
                        <Box
                          component="img"
                          src={`data:image/jpeg;base64,${videoResult.preview_b64}`}
                          alt="Frame preview"
                          sx={{ width: '100%', maxHeight: 250, objectFit: 'contain', display: 'block' }}
                        />
                      </Box>
                    )}
                  </Box>
                </Paper>
              </Box>

              {/* Right column: Analysis */}
              <Box sx={{ flex: '1 1 45%' }}>
                {videoResult && (
                  <>
                    <Paper sx={{ mb: 1.5, border: `1px solid ${C.border}`, borderRadius: 1, overflow: 'hidden', bgcolor: C.panel }}>
                      <SectionHeader title="FILE INFO" />
                      <Box>
                        <InfoRow label="Filename" value={videoResult.filename} />
                        <InfoRow label="Resolution" value={`${videoResult.width} × ${videoResult.height}`} />
                        <InfoRow label="File Size" value={`${videoResult.filesize_mb} MB`} />
                        <InfoRow label="Codec" value={videoResult.compression} />
                        <InfoRow label="Bit Depth" value={videoResult.native_type} />
                        <InfoRow label="Encoding" value={videoResult.encoding} />
                        {videoResult.fps && <InfoRow label="FPS" value={videoResult.fps} />}
                        {videoResult.duration != null && videoResult.duration > 0 && <InfoRow label="Duration" value={`${videoResult.duration.toFixed(2)}s`} />}
                        {videoResult.nb_frames && <InfoRow label="Frames" value={videoResult.nb_frames} />}
                      </Box>
                    </Paper>

                    <Paper sx={{ mb: 1.5, border: `1px solid ${C.border}`, borderRadius: 1, overflow: 'hidden', bgcolor: C.panel }}>
                      <SectionHeader title="QUALITY METRICS" />
                      <Box>
                        <InfoRow label="Range" value={`${videoResult.range_min.toFixed(3)} — ${videoResult.range_max.toFixed(3)}`} />
                        <InfoRow label="Above 1.0" value={`${videoResult.above_1_pct}%`} />
                        <InfoRow label="Unique Values" value={Math.round(videoResult.avg_unique).toLocaleString()} />
                        <InfoRow label="Midtone Step" value={`${videoResult.avg_step_ratio}× finer than 8-bit`} />
                        <InfoRow label="Effective Bits" value={`~${videoResult.eff_bits} bits`} />
                        <InfoRow label="Quality" value={videoResult.rating} accent />
                      </Box>
                    </Paper>

                    <Paper sx={{ border: `1px solid ${C.border}`, borderRadius: 1, overflow: 'hidden', bgcolor: C.panel }}>
                      <SectionHeader title="CHANNEL ANALYSIS" />
                      <Table size="small" sx={{ '& td, & th': { py: 0.3, px: 1, fontSize: '0.65rem', borderColor: C.border } }}>
                        <TableHead>
                          <TableRow>
                            <TableCell sx={{ color: C.dim, fontWeight: 700 }}>CH</TableCell>
                            <TableCell align="right" sx={{ color: C.dim, fontWeight: 700 }}>MIN</TableCell>
                            <TableCell align="right" sx={{ color: C.dim, fontWeight: 700 }}>MAX</TableCell>
                            <TableCell align="right" sx={{ color: C.dim, fontWeight: 700 }}>MEAN</TableCell>
                            <TableCell align="right" sx={{ color: C.dim, fontWeight: 700 }}>UNIQUE</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {(['R', 'G', 'B'] as const).map((ch) => {
                            const d = videoResult.results[ch]
                            if (!d) return null
                            const color = ch === 'R' ? C.red : ch === 'G' ? C.green : C.blue
                            return (
                              <TableRow key={ch}>
                                <TableCell sx={{ color, fontWeight: 700 }}>{ch}</TableCell>
                                <TableCell align="right">{d.min.toFixed(4)}</TableCell>
                                <TableCell align="right">{d.max.toFixed(4)}</TableCell>
                                <TableCell align="right">{d.mean.toFixed(4)}</TableCell>
                                <TableCell align="right">{d.unique_count.toLocaleString()}</TableCell>
                              </TableRow>
                            )
                          })}
                        </TableBody>
                      </Table>
                    </Paper>
                  </>
                )}

                {!videoResult && !analyzing && (
                  <Paper sx={{ border: `1px solid ${C.border}`, borderRadius: 1, overflow: 'hidden', bgcolor: C.panel }}>
                    <SectionHeader title="BIT DEPTH & INFO" />
                    <Box sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="caption" color="text.secondary">
                        Upload a video to see analysis results
                      </Typography>
                    </Box>
                  </Paper>
                )}
              </Box>
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  )
}
