import { defineConfig, presetUno } from 'unocss'

export default defineConfig({
  presets: [presetUno()],
  theme: {
    colors: {
      bg: { DEFAULT: '#0b1119', card: '#121b27', input: '#1b2534', hover: '#1d2a3a', sunken: '#0e1620' },
      border: { DEFAULT: '#233144', strong: '#31435c' },
      dim: '#8fa0b3',
      faint: '#5c6c80',
      accent: { DEFAULT: '#4da3ff', light: '#7cbcff', deep: '#2e7fd9' },
      violet: '#8f7ff7',
      ok: '#4bd07c',
      warn: '#f5b041',
      err: '#f26d6d',
    },
  },
  shortcuts: {
    'btn': 'inline-flex items-center justify-center gap-1.5 h-9 px-4 rounded-lg text-sm font-medium cursor-pointer select-none whitespace-nowrap border border-transparent outline-none transition-all duration-150 focus-visible:ring-2 focus-visible:ring-accent/40 disabled:opacity-45 disabled:cursor-not-allowed disabled:pointer-events-none',
    'btn-primary': 'btn bg-accent text-white shadow-lg shadow-accent/20 hover:bg-accent-light active:bg-accent-deep',
    'btn-danger': 'btn bg-err text-white shadow-lg shadow-err/20 hover:bg-err/85',
    'btn-ghost': 'btn bg-bg-input/50 text-dim border-border hover:text-white hover:border-border-strong hover:bg-bg-hover',
    'btn-icon': 'inline-flex items-center justify-center w-8 h-8 shrink-0 rounded-lg bg-transparent text-dim cursor-pointer border-none outline-none transition-colors duration-150 hover:bg-bg-hover hover:text-white focus-visible:ring-2 focus-visible:ring-accent/40 disabled:opacity-35 disabled:cursor-not-allowed',
    'btn-icon-danger': 'inline-flex items-center justify-center w-8 h-8 shrink-0 rounded-lg bg-transparent text-dim cursor-pointer border-none outline-none transition-colors duration-150 hover:bg-err/12 hover:text-err focus-visible:ring-2 focus-visible:ring-err/40 disabled:opacity-35 disabled:cursor-not-allowed',
    'input-base': 'w-full h-9 px-3 bg-bg-input border border-border rounded-lg text-sm text-white outline-none transition-all duration-150 placeholder:text-faint hover:border-border-strong focus:border-accent focus:ring-2 focus:ring-accent/15 disabled:opacity-50',
    'card': 'bg-bg-card border border-border rounded-xl p-5',
    'card-table': 'bg-bg-card border border-border rounded-xl overflow-hidden',
    'badge': 'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium leading-4 whitespace-nowrap',
    'badge-ok': 'badge bg-ok/12 text-ok',
    'badge-err': 'badge bg-err/12 text-err',
    'badge-warn': 'badge bg-warn/12 text-warn',
    'badge-accent': 'badge bg-accent/12 text-accent-light',
    'badge-dim': 'badge bg-bg-input text-dim',
    'tag': 'inline-flex items-center px-1.5 py-0.5 rounded text-[11px] leading-none text-dim bg-bg-input/80 border border-border/60 whitespace-nowrap',
  },
})
