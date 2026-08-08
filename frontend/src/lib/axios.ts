import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
// In the browser, use '' (relative) so Vite proxy forwards /v1 → localhost:8000
// VITE_API_URL can override for production deployments
import { useAuthStore } from '../store/auth.store'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
  withCredentials: true, // Crucial: send the HttpOnly refresh cookie
})
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken
  if (token && config.headers) config.headers.Authorization = `Bearer ${token}`
  return config
})
let isRefreshing = false
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = []
const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => error ? reject(error) : resolve(token!))
  failedQueue = []
}
apiClient.interceptors.response.use(
  r => r,
  async error => {
    const original = error.config
    if (error.response?.status !== 401 || original._retry) return Promise.reject(error)
    if (isRefreshing) return new Promise((resolve, reject) => { failedQueue.push({ resolve, reject }) })
      .then(token => { original.headers.Authorization = `Bearer ${token}`; return apiClient(original) })
    original._retry = true; isRefreshing = true
    try {
      // The HttpOnly refresh token cookie is automatically sent because of withCredentials: true
      const { data } = await axios.post(`${BASE_URL}/v1/auth/refresh`, {}, { withCredentials: true })
      
      // Update in-memory state
      useAuthStore.getState().setAuth(
        useAuthStore.getState().user!, 
        useAuthStore.getState().organization!, 
        data.access_token
      )
      
      processQueue(null, data.access_token)
      original.headers.Authorization = `Bearer ${data.access_token}`
      return apiClient(original)
    } catch (e) { processQueue(e, null); _clearAuth(); return Promise.reject(e) }
    finally { isRefreshing = false }
  }
)
function _clearAuth() {
  useAuthStore.getState().logout()
  window.location.href = '/login'
}
