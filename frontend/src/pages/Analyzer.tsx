import { useState, useRef, useCallback, useEffect } from 'react'
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
import Dialog from '@mui/material/Dialog'
import DialogContent from '@mui/material/DialogContent'
import IconButton from '@mui/material/IconButton'
import ImageIcon from '@mui/icons-material/Image'
import MovieIcon from '@mui/icons-material/Movie'
import CompareIcon from '@mui/icons-material/Compare'
import SaveAltIcon from '@mui/icons-material/SaveAlt'
import VisibilityIcon from '@mui/icons-material/Visibility'
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff'
import FullscreenIcon from '@mui/icons-material/Fullscreen'
import CloseIcon from '@mui/icons-material/Close'
import ZoomInIcon from '@mui/icons-material/ZoomIn'
import ZoomOutIcon from '@mui/icons-material/ZoomOut'
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong'
import {
  ResponsiveContainer,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
} from 'recharts'
import { API_BASE } from '../api'

interface WaveformPoint { min: number; max: number; mean: number }
interface AnalysisResult {
  filename: string; width: number; height: number
  filesize: number; filesize_mb: number
  compression: string; native_type: string; colorspace: string; encoding: string
  eff_bits: number; avg_unique: number; above_1_pct: number
  rating: string; range_min: number; range_max: number; avg_step_ratio: number
  preview_b64: string
  waveform: { positions: number[]; R: WaveformPoint[]; G: WaveformPoint[]; B: WaveformPoint[] }
  histogram: { bin_centers: number[]; R: number[]; G: number[]; B: number[] }
  results: Record<string, { unique_count: number; min: number; max: number; mean: number; step_ratio: number }>
  fps?: number; duration?: number; nb_frames?: number
}

const C = {
  bg: '#0D0D0D', panel: '#111111', border: '#2A2A2A', text: '#E8E8E8',
  dim: '#777777', green: '#00FF88', red: '#FF4444', blue: '#4488FF', yellow: '#FFCC00',
}

// ── Zoomable/Pannable Image ─────────────────────────────────────────

function ZoomableImage({ src, alt, maxHeight }: { src: string; alt: string; maxHeight?: number }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)
  const [translate, setTranslate] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const dragStart = useRef({ x: 0, y: 0, tx: 0, ty: 0 })

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    setScale(s => Math.min(Math.max(s * delta, 0.25), 10))
  }, [])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return
    setDragging(true)
    dragStart.current = { x: e.clientX, y: e.clientY, tx: translate.x, ty: translate.y }
  }, [translate])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return
    setTranslate({
      x: dragStart.current.tx + (e.clientX - dragStart.current.x),
      y: dragStart.current.ty + (e.clientY - dragStart.current.y),
    })
  }, [dragging])

  const handleMouseUp = useCallback(() => setDragging(false), [])

  const reset = useCallback(() => { setScale(1); setTranslate({ x: 0, y: 0 }) }, [])

  return (
    <Box sx={{ position: 'relative' }}>
      <Box ref={containerRef} sx={{
        overflow: 'hidden', bgcolor: '#000', borderRadius: '2px',
        maxHeight: maxHeight ?? 280, cursor: dragging ? 'grabbing' : 'grab',
        userSelect: 'none',
      }}
        onWheel={handleWheel} onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}
      >
        <Box component="img" src={src} alt={alt} draggable={false} sx={{
          width: '100%', objectFit: 'contain', display: 'block',
          transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
          transformOrigin: 'center', transition: dragging ? 'none' : 'transform 0.1s ease',
        }} />
      </Box>
      <Stack direction="row" spacing={0.25} sx={{ position: 'absolute', bottom: 4, right: 4, opacity: 0.7, '&:hover': { opacity: 1 } }}>
        <IconButton size="small" onClick={() => setScale(s => Math.min(s * 1.3, 10))} sx={{ bgcolor: '#000A', color: '#ccc', p: 0.3 }}>
          <ZoomInIcon sx={{ fontSize: 16 }} />
        </IconButton>
        <IconButton size="small" onClick={() => setScale(s => Math.max(s * 0.7, 0.25))} sx={{ bgcolor: '#000A', color: '#ccc', p: 0.3 }}>
          <ZoomOutIcon sx={{ fontSize: 16 }} />
        </IconButton>
        <IconButton size="small" onClick={reset} sx={{ bgcolor: '#000A', color: '#ccc', p: 0.3 }}>
          <CenterFocusStrongIcon sx={{ fontSize: 16 }} />
        </IconButton>
      </Stack>
      {scale !== 1 && (
        <Typography sx={{ position: 'absolute', top: 4, right: 8, fontSize: 9, color: '#888', bgcolor: '#000A', px: 0.5, borderRadius: 1 }}>
          {Math.round(scale * 100)}%
        </Typography>
      )}
    </Box>
  )
}

// ── Zoomable Chart wrapper ──────────────────────────────────────────

function ZoomableWaveformChart({ data, channels }: { data: AnalysisResult['waveform']; channels: { R: boolean; G: boolean; B: boolean } }) {
  const chartData = data.positions.map((pos, i) => ({
    pos: pos * 1000,
    R_mean: data.R[i]?.mean ?? 0, R_max: data.R[i]?.max ?? 0,
    G_mean: data.G[i]?.mean ?? 0, G_max: data.G[i]?.max ?? 0,
    B_mean: data.B[i]?.mean ?? 0, B_max: data.B[i]?.max ?? 0,
  }))

  const [refAreaLeft, setRefAreaLeft] = useState<number | null>(null)
  const [refAreaRight, setRefAreaRight] = useState<number | null>(null)
  const [xDomain, setXDomain] = useState<[number, number] | null>(null)
  const [yDomain, setYDomain] = useState<[number, number]>([0, 1.2])

  const handleMouseDown = (e: any) => { if (e?.activeLabel != null) setRefAreaLeft(e.activeLabel) }
  const handleMouseMove = (e: any) => { if (refAreaLeft != null && e?.activeLabel != null) setRefAreaRight(e.activeLabel) }
  const handleMouseUp = () => {
    if (refAreaLeft != null && refAreaRight != null && refAreaLeft !== refAreaRight) {
      const left = Math.min(refAreaLeft, refAreaRight)
      const right = Math.max(refAreaLeft, refAreaRight)
      setXDomain([left, right])
      const subset = chartData.filter(d => d.pos >= left && d.pos <= right)
      if (subset.length) {
        const allVals = subset.flatMap(d => [d.R_max, d.G_max, d.B_max, d.R_mean, d.G_mean, d.B_mean])
        setYDomain([0, Math.max(...allVals) * 1.1])
      }
    }
    setRefAreaLeft(null)
    setRefAreaRight(null)
  }

  const resetZoom = () => { setXDomain(null); setYDomain([0, 1.2]) }

  return (
    <Box sx={{ position: 'relative' }}>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}
          onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" />
          <XAxis dataKey="pos" domain={xDomain ?? ['dataMin', 'dataMax']} tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#222' }} type="number" allowDataOverflow />
          <YAxis domain={yDomain} tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#222' }} allowDataOverflow />
          <Tooltip contentStyle={{ backgroundColor: '#1A1A1A', border: '1px solid #333', borderRadius: 4, fontSize: 10, padding: '4px 8px' }} labelStyle={{ color: '#888' }} />
          {channels.R && <><Area type="monotone" dataKey="R_max" stroke="none" fill={C.red} fillOpacity={0.1} animationDuration={300} /><Line type="monotone" dataKey="R_mean" stroke={C.red} strokeWidth={1} dot={false} animationDuration={300} /></>}
          {channels.G && <><Area type="monotone" dataKey="G_max" stroke="none" fill={C.green} fillOpacity={0.1} animationDuration={300} /><Line type="monotone" dataKey="G_mean" stroke={C.green} strokeWidth={1} dot={false} animationDuration={300} /></>}
          {channels.B && <><Area type="monotone" dataKey="B_max" stroke="none" fill={C.blue} fillOpacity={0.1} animationDuration={300} /><Line type="monotone" dataKey="B_mean" stroke={C.blue} strokeWidth={1} dot={false} animationDuration={300} /></>}
          {refAreaLeft != null && refAreaRight != null && (
            <ReferenceArea x1={refAreaLeft} x2={refAreaRight} strokeOpacity={0.3} fill="#FFF" fillOpacity={0.05} />
          )}
        </AreaChart>
      </ResponsiveContainer>
      {xDomain && (
        <Button size="small" onClick={resetZoom}
          sx={{ position: 'absolute', top: 2, right: 8, fontSize: 9, color: C.yellow, minWidth: 'auto', px: 0.5, py: 0 }}>
          Reset Zoom
        </Button>
      )}
    </Box>
  )
}

function ZoomableHistogramChart({ data, channels }: { data: AnalysisResult['histogram']; channels: { R: boolean; G: boolean; B: boolean } }) {
  const chartData = data.bin_centers.map((v, i) => ({
    value: Math.round(v * 100) / 100, R: data.R[i] ?? 0, G: data.G[i] ?? 0, B: data.B[i] ?? 0,
  }))

  const [refAreaLeft, setRefAreaLeft] = useState<number | null>(null)
  const [refAreaRight, setRefAreaRight] = useState<number | null>(null)
  const [xDomain, setXDomain] = useState<[number, number] | null>(null)
  const [yDomain, setYDomain] = useState<[string, string]>(['auto', 'auto'])

  const handleMouseDown = (e: any) => { if (e?.activeLabel != null) setRefAreaLeft(e.activeLabel) }
  const handleMouseMove = (e: any) => { if (refAreaLeft != null && e?.activeLabel != null) setRefAreaRight(e.activeLabel) }
  const handleMouseUp = () => {
    if (refAreaLeft != null && refAreaRight != null && refAreaLeft !== refAreaRight) {
      const left = Math.min(refAreaLeft, refAreaRight)
      const right = Math.max(refAreaLeft, refAreaRight)
      setXDomain([left, right])
      const subset = chartData.filter(d => d.value >= left && d.value <= right)
      if (subset.length) {
        const maxVal = Math.max(...subset.flatMap(d => [d.R, d.G, d.B]))
        setYDomain(['0', String(maxVal * 1.1)])
      }
    }
    setRefAreaLeft(null)
    setRefAreaRight(null)
  }

  const resetZoom = () => { setXDomain(null); setYDomain(['auto', 'auto']) }

  return (
    <Box sx={{ position: 'relative' }}>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}
          onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1A1A1A" />
          <XAxis dataKey="value" domain={xDomain ?? ['dataMin', 'dataMax']} tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#222' }} type="number" allowDataOverflow />
          <YAxis domain={yDomain as any} tick={{ fill: '#555', fontSize: 9 }} tickLine={false} axisLine={{ stroke: '#222' }} allowDataOverflow />
          <Tooltip contentStyle={{ backgroundColor: '#1A1A1A', border: '1px solid #333', borderRadius: 4, fontSize: 10, padding: '4px 8px' }} labelStyle={{ color: '#888' }} />
          {channels.R && <Area type="monotone" dataKey="R" stroke={C.red} fill={C.red} fillOpacity={0.2} strokeWidth={1} dot={false} animationDuration={300} />}
          {channels.G && <Area type="monotone" dataKey="G" stroke={C.green} fill={C.green} fillOpacity={0.2} strokeWidth={1} dot={false} animationDuration={300} />}
          {channels.B && <Area type="monotone" dataKey="B" stroke={C.blue} fill={C.blue} fillOpacity={0.2} strokeWidth={1} dot={false} animationDuration={300} />}
          {refAreaLeft != null && refAreaRight != null && (
            <ReferenceArea x1={refAreaLeft} x2={refAreaRight} strokeOpacity={0.3} fill="#FFF" fillOpacity={0.05} />
          )}
        </AreaChart>
      </ResponsiveContainer>
      {xDomain && (
        <Button size="small" onClick={resetZoom}
          sx={{ position: 'absolute', top: 2, right: 8, fontSize: 9, color: C.yellow, minWidth: 'auto', px: 0.5, py: 0 }}>
          Reset Zoom
        </Button>
      )}
    </Box>
  )
}

// ── Section with working hide/fullscreen ────────────────────────────

function Section({ title, children, actions, sectionId, hiddenSections, onToggleHide, onFullscreen }:
  { title: string; children: React.ReactNode; actions?: React.ReactNode; sectionId: string;
    hiddenSections: Set<string>; onToggleHide: (id: string) => void; onFullscreen: (id: string) => void }) {
  const hidden = hiddenSections.has(sectionId)
  return (
    <Box sx={{ mb: 1, border: `1px solid ${C.border}`, borderRadius: '4px', overflow: 'hidden', bgcolor: C.panel }}>
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 1.5, py: 0.5, borderBottom: hidden ? 'none' : `1px solid ${C.border}`, bgcolor: '#0A0A0A',
      }}>
        <Typography sx={{ fontWeight: 700, letterSpacing: 1.5, color: hidden ? '#444' : C.dim, fontSize: 10 }}>
          {title}
        </Typography>
        {actions || (
          <Stack direction="row" spacing={0.5}>
            <IconButton size="small" onClick={() => onToggleHide(sectionId)} sx={{ p: 0.2 }}>
              {hidden
                ? <VisibilityOffIcon sx={{ fontSize: 14, color: '#444' }} />
                : <VisibilityIcon sx={{ fontSize: 14, color: '#555', '&:hover': { color: '#aaa' } }} />
              }
            </IconButton>
            <IconButton size="small" onClick={() => onFullscreen(sectionId)} sx={{ p: 0.2 }}>
              <FullscreenIcon sx={{ fontSize: 14, color: '#555', '&:hover': { color: '#aaa' } }} />
            </IconButton>
          </Stack>
        )}
      </Box>
      {!hidden && <Box sx={{ p: 1 }}>{children}</Box>}
    </Box>
  )
}

// ── Channel toggles ─────────────────────────────────────────────────

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
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 0.35, px: 1, borderBottom: '1px solid #1A1A1A', '&:last-child': { borderBottom: 'none' } }}>
      <Typography sx={{ color: C.dim, fontSize: 11 }}>{label}</Typography>
      <Typography sx={{ fontWeight: 600, fontSize: 11, color: accent ? C.green : C.text, textAlign: 'right' }}>{value}</Typography>
    </Box>
  )
}

// ── Compare View ────────────────────────────────────────────────────

function CompareView({ a, b, onClose }: { a: AnalysisResult; b: AnalysisResult; onClose: () => void }) {
  const [sliderX, setSliderX] = useState(50)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMove = useCallback((e: React.MouseEvent) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    setSliderX(Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100)))
  }, [])

  return (
    <Dialog open fullScreen PaperProps={{ sx: { bgcolor: '#000' } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2, py: 1, bgcolor: '#0A0A0A', borderBottom: '1px solid #222' }}>
        <Typography sx={{ color: C.text, fontSize: 12, fontWeight: 700 }}>
          COMPARE: {a.filename} vs {b.filename}
        </Typography>
        <IconButton onClick={onClose} sx={{ color: '#888' }}><CloseIcon /></IconButton>
      </Box>

      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Wipe comparison */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Typography sx={{ textAlign: 'center', color: C.dim, fontSize: 10, py: 0.5 }}>
            Drag to compare — Left: {a.filename} | Right: {b.filename}
          </Typography>
          <Box ref={containerRef} onMouseMove={handleMove} sx={{
            flex: 1, position: 'relative', cursor: 'col-resize', overflow: 'hidden',
            mx: 2, mb: 2, border: '1px solid #222', borderRadius: 1,
          }}>
            <Box component="img" src={`data:image/jpeg;base64,${b.preview_b64}`} alt={b.filename}
              sx={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'contain' }} />
            <Box sx={{ position: 'absolute', top: 0, left: 0, width: `${sliderX}%`, height: '100%', overflow: 'hidden' }}>
              <Box component="img" src={`data:image/jpeg;base64,${a.preview_b64}`} alt={a.filename}
                sx={{ position: 'absolute', top: 0, left: 0, width: containerRef.current?.offsetWidth ?? '100%', height: '100%', objectFit: 'contain' }} />
            </Box>
            <Box sx={{
              position: 'absolute', top: 0, left: `${sliderX}%`, width: 2, height: '100%',
              bgcolor: C.green, transform: 'translateX(-50%)', pointerEvents: 'none',
            }} />
            <Box sx={{ position: 'absolute', top: 8, left: 8, bgcolor: '#000A', px: 0.5, borderRadius: 0.5 }}>
              <Typography sx={{ color: C.green, fontSize: 9 }}>{a.filename}</Typography>
            </Box>
            <Box sx={{ position: 'absolute', top: 8, right: 8, bgcolor: '#000A', px: 0.5, borderRadius: 0.5 }}>
              <Typography sx={{ color: C.yellow, fontSize: 9 }}>{b.filename}</Typography>
            </Box>
          </Box>
        </Box>

        {/* Side-by-side metrics */}
        <Box sx={{ width: 320, borderLeft: '1px solid #222', overflow: 'auto', p: 1.5 }}>
          <Typography sx={{ fontWeight: 700, fontSize: 10, color: C.dim, mb: 1, letterSpacing: 1 }}>METRIC COMPARISON</Typography>
          {([
            ['Filename', a.filename, b.filename],
            ['Resolution', `${a.width}×${a.height}`, `${b.width}×${b.height}`],
            ['File Size', `${a.filesize_mb} MB`, `${b.filesize_mb} MB`],
            ['Eff. Bits', `${a.eff_bits}`, `${b.eff_bits}`],
            ['Quality', a.rating, b.rating],
            ['Above 1.0', `${a.above_1_pct}%`, `${b.above_1_pct}%`],
            ['Encoding', a.encoding, b.encoding],
            ['Range', `${a.range_min.toFixed(3)}–${a.range_max.toFixed(3)}`, `${b.range_min.toFixed(3)}–${b.range_max.toFixed(3)}`],
          ] as [string, string, string][]).map(([label, va, vb]) => (
            <Box key={label} sx={{ mb: 0.5, p: 0.5, borderBottom: '1px solid #1A1A1A' }}>
              <Typography sx={{ color: C.dim, fontSize: 9, mb: 0.2 }}>{label}</Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Typography sx={{ flex: 1, color: C.green, fontSize: 10, fontWeight: 600 }}>{va}</Typography>
                <Typography sx={{ flex: 1, color: C.yellow, fontSize: 10, fontWeight: 600 }}>{vb}</Typography>
              </Box>
            </Box>
          ))}

          <Typography sx={{ fontWeight: 700, fontSize: 10, color: C.dim, mt: 2, mb: 1, letterSpacing: 1 }}>CHANNEL COMPARISON</Typography>
          {(['R', 'G', 'B'] as const).map(ch => {
            const da = a.results[ch], db = b.results[ch]
            const color = ch === 'R' ? C.red : ch === 'G' ? C.green : C.blue
            return (
              <Box key={ch} sx={{ mb: 0.5, p: 0.5, borderBottom: '1px solid #1A1A1A' }}>
                <Typography sx={{ color, fontSize: 10, fontWeight: 700, mb: 0.2 }}>{ch}</Typography>
                <Box sx={{ display: 'flex', gap: 1, fontSize: 9 }}>
                  <Typography sx={{ flex: 1, color: '#aaa', fontSize: 9 }}>
                    {da.min.toFixed(4)}–{da.max.toFixed(4)} μ{da.mean.toFixed(4)}
                  </Typography>
                  <Typography sx={{ flex: 1, color: '#aaa', fontSize: 9 }}>
                    {db.min.toFixed(4)}–{db.max.toFixed(4)} μ{db.mean.toFixed(4)}
                  </Typography>
                </Box>
              </Box>
            )
          })}
        </Box>
      </Box>
    </Dialog>
  )
}

// ── Main Analyzer ───────────────────────────────────────────────────

export default function Analyzer() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [wCh, setWCh] = useState({ R: true, G: true, B: true })
  const [hCh, setHCh] = useState({ R: true, G: true, B: true })

  const [hiddenSections, setHiddenSections] = useState<Set<string>>(new Set())
  const [fullscreenSection, setFullscreenSection] = useState<string | null>(null)

  const [compareResult, setCompareResult] = useState<AnalysisResult | null>(null)
  const [comparing, setComparing] = useState(false)
  const [compareLoading, setCompareLoading] = useState(false)

  const toggleHide = useCallback((id: string) => {
    setHiddenSections(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }, [])

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f); setResult(null); setError(null)
    setCompareResult(null); setComparing(false)
    analyze(f)
  }

  const analyze = async (f: File) => {
    setLoading(true); setError(null); setResult(null)
    try {
      const form = new FormData()
      form.append('file', f)
      const ep = f.name.toLowerCase().endsWith('.exr') ? '/analyze-exr' : '/analyze-video'
      const res = await fetch(`${API_BASE}${ep}`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || res.statusText)
      }
      setResult(await res.json() as AnalysisResult)
    } catch (e) { setError(e instanceof Error ? e.message : 'Analysis failed') }
    finally { setLoading(false) }
  }

  const handleCompare = () => {
    if (!result) return
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.exr,.mov,.mp4,.avi,.mkv,.mxf,.webm,.m4v,.mpg,.mpeg'
    input.onchange = async () => {
      const f = input.files?.[0]
      if (!f) return
      setCompareLoading(true)
      try {
        const form = new FormData()
        form.append('file', f)
        const ep = f.name.toLowerCase().endsWith('.exr') ? '/analyze-exr' : '/analyze-video'
        const res = await fetch(`${API_BASE}${ep}`, { method: 'POST', body: form })
        if (!res.ok) throw new Error('Failed to analyze comparison file')
        const data = await res.json() as AnalysisResult
        setCompareResult(data)
        setComparing(true)
      } catch { setError('Compare file analysis failed') }
      finally { setCompareLoading(false) }
    }
    input.click()
  }

  const handleExport = () => {
    if (!result?.preview_b64) return
    const a = document.createElement('a')
    a.href = `data:image/jpeg;base64,${result.preview_b64}`
    a.download = `${result.filename.replace(/\.[^.]+$/, '')}_preview.jpg`
    a.click()
  }

  // Listen for Escape to close fullscreen
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setFullscreenSection(null) }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const twCh = (c: 'R' | 'G' | 'B') => setWCh(p => ({ ...p, [c]: !p[c] }))
  const thCh = (c: 'R' | 'G' | 'B') => setHCh(p => ({ ...p, [c]: !p[c] }))
  const r = result

  // Section content builders for reuse in fullscreen
  const sectionContent: Record<string, React.ReactNode> = {
    preview: r?.preview_b64 ? (
      <ZoomableImage src={`data:image/jpeg;base64,${r.preview_b64}`} alt="Preview" maxHeight={fullscreenSection === 'preview' ? undefined : 280} />
    ) : (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 200, bgcolor: '#080808', borderRadius: '2px', cursor: 'pointer' }} component="label">
        <ImageIcon sx={{ fontSize: 36, color: '#2A2A2A', mb: 1 }} />
        <Typography sx={{ color: '#444', fontSize: 12 }}>Open a file to preview</Typography>
        <input type="file" hidden accept=".exr,.mov,.mp4,.avi,.mkv,.mxf,.webm,.m4v,.mpg,.mpeg" onChange={handleFile} />
      </Box>
    ),
    waveform: (
      <>
        <ChToggles ch={wCh} onChange={twCh} showFull />
        {r?.waveform ? (
          <ZoomableWaveformChart data={r.waveform} channels={wCh} />
        ) : (
          <Box sx={{ height: 130, bgcolor: '#080808', borderRadius: '2px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography sx={{ color: '#333', fontSize: 11 }}>No data</Typography>
          </Box>
        )}
        <Typography sx={{ color: '#444', textAlign: 'center', fontSize: 9, mt: 0.5 }}>Drag to zoom — Frame Position (×0.001)</Typography>
      </>
    ),
    histogram: (
      <>
        <ChToggles ch={hCh} onChange={thCh} />
        {r?.histogram ? (
          <ZoomableHistogramChart data={r.histogram} channels={hCh} />
        ) : (
          <Box sx={{ height: 130, bgcolor: '#080808', borderRadius: '2px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography sx={{ color: '#333', fontSize: 11 }}>No data</Typography>
          </Box>
        )}
        <Typography sx={{ color: '#444', textAlign: 'center', fontSize: 9, mt: 0.5 }}>Drag to zoom</Typography>
      </>
    ),
    fileinfo: (
      <>
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
      </>
    ),
    quality: (
      <>
        <InfoRow label="Range" value={r ? `${r.range_min.toFixed(3)} — ${r.range_max.toFixed(3)}` : '—'} />
        <InfoRow label="Above 1.0" value={r ? `${r.above_1_pct}%` : '—'} />
        <InfoRow label="Unique Values" value={r ? Math.round(r.avg_unique).toLocaleString() : '—'} />
        <InfoRow label="Midtone Step" value={r ? `${r.avg_step_ratio}× finer than 8-bit` : '—'} />
        <InfoRow label="Effective Bits" value={r ? `~${r.eff_bits} bits` : '—'} />
        <InfoRow label="Quality" value={r?.rating ?? '—'} accent={!!r} />
      </>
    ),
    channels: (
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
    ),
  }

  const sectionTitles: Record<string, string> = {
    preview: 'IMAGE PREVIEW', waveform: 'WAVEFORM', histogram: 'HISTOGRAM',
    fileinfo: 'FILE INFO', quality: 'QUALITY METRICS', channels: 'CHANNEL ANALYSIS',
  }

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
        <Button variant="outlined" size="small" startIcon={<CompareIcon />}
          disabled={!result || compareLoading}
          onClick={handleCompare}
          sx={{ fontWeight: 700, fontSize: 11, px: 2 }}>
          {compareLoading ? 'Loading…' : 'Compare'}
        </Button>
        <Button variant="outlined" size="small" startIcon={<SaveAltIcon />}
          disabled={!result}
          onClick={handleExport}
          sx={{ fontWeight: 700, fontSize: 11, px: 2 }}>
          Export frame…
        </Button>
        {file && <Chip label={file.name} size="small" onDelete={() => { setFile(null); setResult(null); setCompareResult(null); setComparing(false) }} />}
      </Stack>

      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
          <CircularProgress size={20} sx={{ color: C.green }} />
          <Typography sx={{ fontSize: 12, color: C.dim }}>Analyzing {file?.name}…</Typography>
        </Box>
      )}
      {error && <Alert severity="error" sx={{ mb: 1.5 }}>{error}</Alert>}

      {/* Layout */}
      <Grid container spacing={1}>
        <Grid item xs={12} md={7}>
          <Section title="IMAGE PREVIEW" sectionId="preview" hiddenSections={hiddenSections} onToggleHide={toggleHide} onFullscreen={setFullscreenSection}>
            {sectionContent.preview}
          </Section>
          <Section title="WAVEFORM" sectionId="waveform" hiddenSections={hiddenSections} onToggleHide={toggleHide} onFullscreen={setFullscreenSection}>
            {sectionContent.waveform}
          </Section>
          <Section title="HISTOGRAM" sectionId="histogram" hiddenSections={hiddenSections} onToggleHide={toggleHide} onFullscreen={setFullscreenSection}>
            {sectionContent.histogram}
          </Section>
        </Grid>

        <Grid item xs={12} md={5}>
          <Section title="FILE INFO" sectionId="fileinfo" hiddenSections={hiddenSections} onToggleHide={toggleHide} onFullscreen={setFullscreenSection}>
            {sectionContent.fileinfo}
          </Section>
          <Section title="QUALITY METRICS" sectionId="quality" hiddenSections={hiddenSections} onToggleHide={toggleHide} onFullscreen={setFullscreenSection}>
            {sectionContent.quality}
          </Section>
          <Section title="CHANNEL ANALYSIS" sectionId="channels" hiddenSections={hiddenSections} onToggleHide={toggleHide} onFullscreen={setFullscreenSection}>
            {sectionContent.channels}
          </Section>
        </Grid>
      </Grid>

      {r && (
        <Box sx={{ mt: 0.5, px: 1 }}>
          <Typography sx={{ color: C.green, fontSize: 10 }}>✓ Analyzed: {r.filename}</Typography>
        </Box>
      )}

      {/* Fullscreen Dialog */}
      <Dialog open={!!fullscreenSection} onClose={() => setFullscreenSection(null)} maxWidth={false}
        PaperProps={{ sx: { bgcolor: '#0D0D0D', width: '90vw', height: '85vh', maxWidth: '90vw', borderRadius: 2 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2, py: 1, borderBottom: '1px solid #222', bgcolor: '#0A0A0A' }}>
          <Typography sx={{ fontWeight: 700, letterSpacing: 1.5, color: C.dim, fontSize: 11 }}>
            {fullscreenSection ? sectionTitles[fullscreenSection] ?? '' : ''}
          </Typography>
          <IconButton onClick={() => setFullscreenSection(null)} sx={{ color: '#888' }}><CloseIcon /></IconButton>
        </Box>
        <DialogContent sx={{ bgcolor: '#111', p: 2, overflow: 'auto' }}>
          {fullscreenSection && sectionContent[fullscreenSection]}
        </DialogContent>
      </Dialog>

      {/* Compare Overlay */}
      {comparing && result && compareResult && (
        <CompareView a={result} b={compareResult} onClose={() => { setComparing(false); setCompareResult(null) }} />
      )}
    </Box>
  )
}
