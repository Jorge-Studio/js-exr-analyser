import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Grid from '@mui/material/Grid'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Chip from '@mui/material/Chip'
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import Stack from '@mui/material/Stack'
import ImageIcon from '@mui/icons-material/Image'
import MovieIcon from '@mui/icons-material/Movie'
import CompareIcon from '@mui/icons-material/Compare'
import SaveAltIcon from '@mui/icons-material/SaveAlt'
import VisibilityIcon from '@mui/icons-material/Visibility'
import FullscreenIcon from '@mui/icons-material/Fullscreen'
import {
  ResponsiveContainer,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import { API_BASE } from '../api'

interface WaveformPoint { min: number; max: number; mean: number }
interface AnalysisResult {
  filename: string
  width: number
  height: number
  filesize: number
  filesize_mb: number
  compression: string
  native_type: string
  colorspace: string
  encoding: string
  eff_bits: number
  avg_unique: number
  above_1_pct: number
  rating: string
  range_min: number
  range_max: number
  avg_step_ratio: number
  preview_b64: string
  waveform: {
    positions: number[]
    R: WaveformPoint[]
    G: WaveformPoint[]
    B: WaveformPoint[]
  }
  histogram: {
    bin_centers: number[]
    R: number[]
    G: number[]
    B: number[]
  }
  results: Record<string, {
    unique_count: number
    min: number
    max: number
    mean: number
    step_ratio: number
  }>
  fps?: number
  duration?: number
  nb_frames?: number
}

const C = {
  bg: '#0D0D0D',
  panel: '#111111',
  border: '#2A2A2A',
  text: '#E8E8E8',
  dim: '#777777',
  green: '#00FF88',
  red: '#FF4444',
  blue: '#4488FF',
  yellow: '#FFCC00',
}

function Section({ title, children, actions }: { title: string; children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <Box sx={{ mb: 1, border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', bgcolor: C.panel }}>
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 1.5, py: 0.5, borderBottom: `1px solid ${C.border}`, bgcolor: '#0A0A0A',
      }}>
        <Typography sx={{ fontWeight: 700, letterSpacing: 1.5, color: C.dim, fontSize: 10 }}>
          {title}
        </Typography>
        {actions || (
          <Stack direction="row" spacing={0.5}>
            <VisibilityIcon sx={{ fontSize: 14, color: '#555', cursor: 'pointer' }} />
            <FullscreenIcon sx={{ fontSize: 14, color: '#555', cursor: 'pointer' }} />
          </Stack>
        )}
      </Box>
      <Box sx={{ p: 1 }}>{children}</Box>
    </Box>
  )
}

function WaveformChart({ data, channels }: { data: AnalysisResult['waveform']; channels: { R: boolean; G: boolean; B: boolean } }) {
  const chartData = data.positions.map((pos, i) => ({
    pos: pos * 1000,
    R_mean: data.R[i]?.mean ?? 0, R_max: data.R[i]?.max ?? 0,
    G_mean: data.G[i]?.mean ?? 0, G_max: data.G[i]?.max ?? 0,
    B_mean: data.B[i]?.mean ?? 0, B_max: data.B[i]?.max ?? 0,
  }))
  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" />
        <XAxis dataKey="pos" tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#222' }} />
        <YAxis domain={[0, 1.2]} tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#222' }} />
        <Tooltip contentStyle={{ backgroundColor: '#1A1A1A', border: `1px solid #333`, borderRadius: 4, fontSize: 10, padding: '4px 8px' }} labelStyle={{ color: '#888' }} />
        {channels.R && <><Area type="monotone" dataKey="R_max" stroke="none" fill={C.red} fillOpacity={0.1} /><Line type="monotone" dataKey="R_mean" stroke={C.red} strokeWidth={1} dot={false} /></>}
        {channels.G && <><Area type="monotone" dataKey="G_max" stroke="none" fill={C.green} fillOpacity={0.1} /><Line type="monotone" dataKey="G_mean" stroke={C.green} strokeWidth={1} dot={false} /></>}
        {channels.B && <><Area type="monotone" dataKey="B_max" stroke="none" fill={C.blue} fillOpacity={0.1} /><Line type="monotone" dataKey="B_mean" stroke={C.blue} strokeWidth={1} dot={false} /></>}
      </AreaChart>
    </ResponsiveContainer>
  )
}

function HistogramChart({ data, channels }: { data: AnalysisResult['histogram']; channels: { R: boolean; G: boolean; B: boolean } }) {
  const chartData = data.bin_centers.map((v, i) => ({
    value: Math.round(v * 100) / 100, R: data.R[i] ?? 0, G: data.G[i] ?? 0, B: data.B[i] ?? 0,
  }))
  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" />
        <XAxis dataKey="value" tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#222' }} />
        <YAxis tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#222' }} />
        <Tooltip contentStyle={{ backgroundColor: '#1A1A1A', border: `1px solid #333`, borderRadius: 4, fontSize: 10, padding: '4px 8px' }} labelStyle={{ color: '#888' }} />
        {channels.R && <Area type="monotone" dataKey="R" stroke={C.red} fill={C.red} fillOpacity={0.2} strokeWidth={1} dot={false} />}
        {channels.G && <Area type="monotone" dataKey="G" stroke={C.green} fill={C.green} fillOpacity={0.2} strokeWidth={1} dot={false} />}
        {channels.B && <Area type="monotone" dataKey="B" stroke={C.blue} fill={C.blue} fillOpacity={0.2} strokeWidth={1} dot={false} />}
      </AreaChart>
    </ResponsiveContainer>
  )
}

function ChToggles({ ch, onChange, showFull }: { ch: { R: boolean; G: boolean; B: boolean }; onChange: (c: 'R' | 'G' | 'B') => void; showFull?: boolean }) {
  const items: { key: 'R' | 'G' | 'B'; color: string }[] = [{ key: 'R', color: C.red }, { key: 'G', color: C.green }, { key: 'B', color: C.blue }]
  return (
    <Stack direction="row" spacing={0.5} sx={{ mb: 0.5 }}>
      {showFull && (
        <FormControlLabel sx={{ mr: 0, ml: -0.5 }} control={
          <Checkbox size="small" checked={ch.R && ch.G && ch.B} onChange={() => { onChange('R'); onChange('G'); onChange('B') }}
            sx={{ p: 0.3, color: C.yellow, '&.Mui-checked': { color: C.yellow } }} />
        } label={<Typography sx={{ color: C.yellow, fontWeight: 700, fontSize: 9 }}>FULL waveform</Typography>} />
      )}
      {items.map(({ key, color }) => (
        <FormControlLabel key={key} sx={{ mr: 0 }} control={
          <Checkbox size="small" checked={ch[key]} onChange={() => onChange(key)}
            sx={{ p: 0.3, color, '&.Mui-checked': { color } }} />
        } label={<Typography sx={{ fontWeight: 700, fontSize: 9, color }}>{key}</Typography>} />
      ))}
    </Stack>
  )
}

function InfoRow({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 0.35, px: 1, borderBottom: `1px solid #1A1A1A`, '&:last-child': { borderBottom: 'none' } }}>
      <Typography sx={{ color: C.dim, fontSize: 11 }}>{label}</Typography>
      <Typography sx={{ fontWeight: 600, fontSize: 11, color: accent ? C.green : C.text, textAlign: 'right' }}>{value}</Typography>
    </Box>
  )
}

export default function Analyzer() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [wCh, setWCh] = useState({ R: true, G: true, B: true })
  const [hCh, setHCh] = useState({ R: true, G: true, B: true })

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f); setResult(null); setError(null)
    analyze(f)
  }

  const analyze = async (f: File) => {
    setLoading(true); setError(null); setResult(null)
    try {
      const form = new FormData()
      form.append('file', f)
      const ep = f.name.toLowerCase().endsWith('.exr') ? '/analyze-exr' : '/analyze-video'
      const res = await fetch(`${API_BASE}${ep}`, { method: 'POST', body: form })
      if (!res.ok) { const err = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(err.detail || res.statusText) }
      setResult(await res.json() as AnalysisResult)
    } catch (e) { setError(e instanceof Error ? e.message : 'Analysis failed') }
    finally { setLoading(false) }
  }

  const twCh = (c: 'R' | 'G' | 'B') => setWCh(p => ({ ...p, [c]: !p[c] }))
  const thCh = (c: 'R' | 'G' | 'B') => setHCh(p => ({ ...p, [c]: !p[c] }))
  const r = result

  return (
    <Box>
      {/* Toolbar */}
      <Stack direction="row" spacing={1} sx={{ mb: 1.5, flexWrap: 'wrap', alignItems: 'center' }}>
        <Button variant="contained" size="small" component="label" startIcon={<ImageIcon />} sx={{ fontWeight: 700, fontSize: 11, px: 2 }}>
          Open EXR<input type="file" hidden accept=".exr" onChange={handleFile} />
        </Button>
        <Button variant="contained" size="small" component="label" startIcon={<MovieIcon />} sx={{ fontWeight: 700, fontSize: 11, px: 2 }}>
          Open Video<input type="file" hidden accept=".mov,.mp4,.avi,.mkv,.mxf,.webm,.m4v,.mpg,.mpeg" onChange={handleFile} />
        </Button>
        <Button variant="outlined" size="small" startIcon={<CompareIcon />} disabled sx={{ fontWeight: 700, fontSize: 11, px: 2 }}>Compare</Button>
        <Button variant="outlined" size="small" startIcon={<SaveAltIcon />} disabled sx={{ fontWeight: 700, fontSize: 11, px: 2 }}>Export frame…</Button>
        {file && <Chip label={file.name} size="small" onDelete={() => { setFile(null); setResult(null) }} />}
      </Stack>

      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
          <CircularProgress size={20} sx={{ color: C.green }} />
          <Typography sx={{ fontSize: 12, color: C.dim }}>Analyzing {file?.name}…</Typography>
        </Box>
      )}
      {error && <Alert severity="error" sx={{ mb: 1.5 }}>{error}</Alert>}

      {/* Layout: always show panels, populated or empty */}
      <Grid container spacing={1}>
        {/* LEFT: Visualizations */}
        <Grid item xs={12} md={7}>
          <Section title="IMAGE PREVIEW">
            {r?.preview_b64 ? (
              <Box component="img" src={`data:image/jpeg;base64,${r.preview_b64}`} alt="Preview"
                sx={{ width: '100%', maxHeight: 280, objectFit: 'contain', display: 'block', bgcolor: '#000', borderRadius: '2px' }} />
            ) : (
              <Box sx={{
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                height: 200, bgcolor: '#080808', borderRadius: '2px', cursor: 'pointer',
              }} component="label">
                <ImageIcon sx={{ fontSize: 36, color: '#2A2A2A', mb: 1 }} />
                <Typography sx={{ color: '#444', fontSize: 12 }}>Open a file to preview</Typography>
                <input type="file" hidden accept=".exr,.mov,.mp4,.avi,.mkv,.mxf,.webm,.m4v,.mpg,.mpeg" onChange={handleFile} />
              </Box>
            )}
          </Section>

          <Section title="WAVEFORM">
            <ChToggles ch={wCh} onChange={twCh} showFull />
            {r?.waveform ? (
              <WaveformChart data={r.waveform} channels={wCh} />
            ) : (
              <Box sx={{ height: 130, bgcolor: '#080808', borderRadius: '2px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography sx={{ color: '#333', fontSize: 11 }}>No data</Typography>
              </Box>
            )}
            <Typography sx={{ color: '#444', textAlign: 'center', fontSize: 9, mt: 0.5 }}>Frame Position (×0.001)</Typography>
          </Section>

          <Section title="HISTOGRAM">
            <ChToggles ch={hCh} onChange={thCh} />
            {r?.histogram ? (
              <HistogramChart data={r.histogram} channels={hCh} />
            ) : (
              <Box sx={{ height: 130, bgcolor: '#080808', borderRadius: '2px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography sx={{ color: '#333', fontSize: 11 }}>No data</Typography>
              </Box>
            )}
          </Section>
        </Grid>

        {/* RIGHT: Info panels */}
        <Grid item xs={12} md={5}>
          <Section title="FILE INFO">
            <InfoRow label="Filename" value={r?.filename ?? '—'} />
            <InfoRow label="Resolution" value={r ? `${r.width} × ${r.height}` : '—'} />
            <InfoRow label="File Size" value={r ? `${r.filesize_mb} MB` : '—'} />
            <InfoRow label="Compression" value={r?.compression ?? '—'} />
            <InfoRow label="Bit Depth" value={r?.native_type || '—'} />
            <InfoRow label="Color Space" value={r?.colorspace || '—'} />
            <InfoRow label="Encoding" value={r?.encoding ?? '—'} />
            {r?.fps != null && <InfoRow label="FPS" value={r.fps} />}
            {r?.duration != null && r.duration > 0 && <InfoRow label="Duration" value={`${r.duration.toFixed(2)}s`} />}
            {r?.nb_frames != null && <InfoRow label="Frames" value={r.nb_frames} />}
          </Section>

          <Section title="QUALITY METRICS">
            <InfoRow label="Range" value={r ? `${r.range_min.toFixed(3)} — ${r.range_max.toFixed(3)}` : '—'} />
            <InfoRow label="Above 1.0" value={r ? `${r.above_1_pct}%` : '—'} />
            <InfoRow label="Unique Values" value={r ? Math.round(r.avg_unique).toLocaleString() : '—'} />
            <InfoRow label="Midtone Step" value={r ? `${r.avg_step_ratio}× finer than 8-bit` : '—'} />
            <InfoRow label="Effective Bits" value={r ? `~${r.eff_bits} bits` : '—'} />
            <InfoRow label="Quality" value={r?.rating ?? '—'} accent={!!r} />
          </Section>

          <Section title="CHANNEL ANALYSIS">
            <Table size="small" sx={{ '& td, & th': { py: 0.35, px: 0.75, fontSize: 11, borderColor: '#1A1A1A' } }}>
              <TableHead>
                <TableRow>
                  {['CHANNEL', 'MIN', 'MAX', 'MEAN', 'UNIQUE'].map(h => (
                    <TableCell key={h} align={h === 'CHANNEL' ? 'left' : 'right'} sx={{ color: C.dim, fontWeight: 700, fontSize: '10px !important' }}>{h}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {(['R', 'G', 'B'] as const).map(ch => {
                  const d = r?.results[ch]
                  const color = ch === 'R' ? C.red : ch === 'G' ? C.green : C.blue
                  return (
                    <TableRow key={ch}>
                      <TableCell sx={{ color, fontWeight: 700 }}>{ch}</TableCell>
                      <TableCell align="right">{d ? d.min.toFixed(4) : '—'}</TableCell>
                      <TableCell align="right">{d ? d.max.toFixed(4) : '—'}</TableCell>
                      <TableCell align="right">{d ? d.mean.toFixed(4) : '—'}</TableCell>
                      <TableCell align="right">{d ? d.unique_count.toLocaleString() : '—'}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </Section>
        </Grid>
      </Grid>

      {r && (
        <Box sx={{ mt: 0.5, px: 1 }}>
          <Typography sx={{ color: C.green, fontSize: 10 }}>✓ Analyzed: {r.filename}</Typography>
        </Box>
      )}
    </Box>
  )
}
