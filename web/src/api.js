const API_KEY_STORAGE = 'tg_userbot_api_key'

export function getApiKey() {
  return localStorage.getItem(API_KEY_STORAGE) || ''
}

export function setApiKey(key) {
  localStorage.setItem(API_KEY_STORAGE, key)
}

async function request(path, options = {}) {
  const key = getApiKey()
  const res = await fetch(`/api${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': key,
      ...options.headers,
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getStatus: () => request('/status'),
  getHealth: () => fetch('/health').then(r => r.json()),

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
}
