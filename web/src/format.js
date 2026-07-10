// 通用格式化工具
export function fmtDate(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

export function fmtBytes(value) {
  if (!value) return '—'
  let size = Number(value)
  for (const unit of ['B', 'KB', 'MB', 'GB', 'TB']) {
    if (size < 1024 || unit === 'TB') {
      return unit === 'B' ? `${size} ${unit}` : `${size.toFixed(2)} ${unit}`
    }
    size /= 1024
  }
}

export function fmtDuration(ms) {
  if (!ms) return ''
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)} s`
}

export function fmtSpeed(bps) {
  if (!bps) return ''
  return `${fmtBytes(bps)}/s`
}
