const API_KEY_STORAGE = 'tg_userbot_api_key'
const TOKEN_STORAGE = 'tg_userbot_access_token'

export function getApiKey() {
  return localStorage.getItem(API_KEY_STORAGE) || ''
}

export function setApiKey(key) {
  localStorage.setItem(API_KEY_STORAGE, key)
}

export function getAccessToken() {
  return localStorage.getItem(TOKEN_STORAGE) || ''
}

export function setAccessToken(token) {
  if (token) localStorage.setItem(TOKEN_STORAGE, token)
  else localStorage.removeItem(TOKEN_STORAGE)
}

async function request(path, options = {}) {
  const key = getApiKey()
  const token = getAccessToken()
  const res = await fetch(`/api${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(key ? { 'X-API-Key': key } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    // 会话过期时自动回到登录页（登录接口本身除外，避免刷新循环）
    if (res.status === 401 && path !== '/auth/login' && getAccessToken()) {
      setAccessToken('')
      location.reload()
      return new Promise(() => {})
    }
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getAuthConfig: () => fetch('/api/auth/config').then(r => r.json()),
  login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),

  getStatus: () => request('/status'),
  getHealth: () => fetch('/health').then(r => r.json()),

  getTelegramAuthStatus: () => request('/telegram-auth/status'),
  sendTelegramCode: (data) => request('/telegram-auth/send-code', { method: 'POST', body: JSON.stringify(data) }),
  signInTelegram: (data) => request('/telegram-auth/sign-in', { method: 'POST', body: JSON.stringify(data) }),
  signInTelegramPassword: (data) => request('/telegram-auth/password', { method: 'POST', body: JSON.stringify(data) }),

  getGroups: () => request('/groups'),
  addGroup: (data) => request('/groups', { method: 'POST', body: JSON.stringify(data) }),
  removeGroup: (chatId) => request(`/groups/${chatId}`, { method: 'DELETE' }),
  toggleGroup: (chatId, isActive) =>
    request(`/groups/${chatId}/toggle`, { method: 'PATCH', body: JSON.stringify({ is_active: isActive }) }),

  getRules: () => request('/rules'),
  addRule: (data) => request('/rules', { method: 'POST', body: JSON.stringify(data) }),
  updateRule: (id, data) => request(`/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteRule: (id) => request(`/rules/${id}`, { method: 'DELETE' }),
  toggleRule: (id, isActive) =>
    request(`/rules/${id}/toggle`, { method: 'PATCH', body: JSON.stringify({ is_active: isActive }) }),

  getSchedules: () => request('/schedules'),
  addSchedule: (data) => request('/schedules', { method: 'POST', body: JSON.stringify(data) }),
  updateSchedule: (id, data) => request(`/schedules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSchedule: (id) => request(`/schedules/${id}`, { method: 'DELETE' }),
  toggleSchedule: (id, isActive) =>
    request(`/schedules/${id}/toggle`, { method: 'PATCH', body: JSON.stringify({ is_active: isActive }) }),

  sendMessage: (data) => request('/messages/send', { method: 'POST', body: JSON.stringify(data) }),
  getLogs: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/messages/logs${qs ? '?' + qs : ''}`)
  },

  getDownloadSettings: () => request('/settings/download'),
  updateDownloadSettings: (data) =>
    request('/settings/download', { method: 'PUT', body: JSON.stringify(data) }),
  testWebDavSettings: (data) =>
    request('/settings/download/webdav-test', { method: 'POST', body: JSON.stringify(data) }),

  getDownloads: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/downloads${qs ? '?' + qs : ''}`)
  },
  retryDownload: (id) => request(`/downloads/${id}/retry`, { method: 'POST' }),
}
