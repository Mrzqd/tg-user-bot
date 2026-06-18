import { defineConfig, presetUno, presetIcons } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetIcons({ scale: 1.2, cdn: 'https://esm.sh/' }),
  ],
  theme: {
    colors: {
      bg: { DEFAULT: '#0e1621', card: '#17212b', input: '#242f3d', hover: '#1e2c3a' },
      border: '#2b3945',
      dim: '#6c7883',
      accent: { DEFAULT: '#3390ec', light: '#4ea4f6' },
      ok: '#4fae4e',
      warn: '#e0a030',
      err: '#e05555',
    },
  },
  shortcuts: {
    'btn': 'inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium cursor-pointer border-none transition-all duration-150 text-white disabled:opacity-50',
    'btn-primary': 'btn bg-accent hover:bg-accent-light',
    'btn-danger': 'btn bg-err hover:bg-err/80',
    'btn-ghost': 'btn bg-transparent text-dim border border-border hover:bg-bg-hover hover:text-white',
    'btn-sm': 'btn text-xs px-2.5 py-1',
    'btn-icon': 'w-8 h-8 flex items-center justify-center rounded-md bg-transparent text-dim cursor-pointer border-none transition-colors hover:bg-bg-hover hover:text-white',
    'input-base': 'w-full px-3 py-2 bg-bg-input border border-border rounded-lg text-sm text-white outline-none transition-colors placeholder:text-dim focus:border-accent',
    'badge': 'inline-block px-2 py-0.5 rounded-full text-xs font-semibold',
    'badge-on': 'badge bg-ok/15 text-ok',
    'badge-off': 'badge bg-err/15 text-err',
    'card': 'bg-bg-card border border-border rounded-xl p-5',
  },
})
