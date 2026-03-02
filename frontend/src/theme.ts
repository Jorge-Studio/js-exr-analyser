/**
 * Material 3–inspired dark theme with EXR Analyzer color scheme.
 * Keeps existing palette; M3-style rounded corners and tonal surfaces.
 */
import { createTheme, alpha } from '@mui/material/styles'

const bg = '#0D0D0D'
const bgLight = '#1A1A1A'
const bgCard = '#141414'
const text = '#E8E8E8'
const textDim = '#888888'
const accent = '#00FF88'
const warning = '#FFaa00'
const error = '#FF4444'
const border = '#333333'

export const appTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: accent,
      light: alpha(accent, 0.8),
      dark: alpha(accent, 0.9),
      contrastText: bg,
    },
    secondary: {
      main: textDim,
      contrastText: text,
    },
    error: {
      main: error,
    },
    warning: {
      main: warning,
    },
    background: {
      default: bg,
      paper: bgCard,
    },
    text: {
      primary: text,
      secondary: textDim,
      disabled: alpha(textDim, 0.6),
    },
    divider: border,
    action: {
      active: text,
      hover: alpha(text, 0.08),
      selected: alpha(accent, 0.16),
      disabled: textDim,
    },
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: '"SF Pro Display", "Segoe UI", "Helvetica Neue", sans-serif',
    h1: { fontWeight: 700, letterSpacing: '0.02em' },
    h2: { fontWeight: 600, letterSpacing: '0.01em' },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    body1: { color: text },
    body2: { color: textDim },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: bg,
          color: text,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          backgroundColor: bgCard,
          border: `1px solid ${border}`,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: bgLight,
          borderRight: `1px solid ${border}`,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: bgLight,
          borderBottom: `1px solid ${border}`,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
          fontWeight: 600,
        },
        containedPrimary: {
          '&:hover': {
            backgroundColor: alpha(accent, 0.85),
          },
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          '&.Mui-selected': {
            backgroundColor: alpha(accent, 0.12),
            '&:hover': {
              backgroundColor: alpha(accent, 0.18),
            },
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: bgCard,
          border: `1px solid ${border}`,
          borderRadius: 12,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
})
