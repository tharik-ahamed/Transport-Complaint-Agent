/**
 * Transport Complaint Agent — API Client
 *
 * Warning 2 fix: Admin endpoints (GET /complaints, AI routes) now require
 * a Bearer JWT. This client auto-authenticates using credentials from
 * environment variables and caches the token in memory for the session.
 *
 * Public endpoint (no auth):
 *   POST /api/v1/complaints/create
 *
 * Protected endpoints (auto-auth handled here transparently):
 *   GET  /api/v1/complaints
 *   POST /api/v1/ai/analyze-complaint
 *   GET  /api/v1/complaints/{id}/analysis
 */
import axios from 'axios'

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  "https://transport-complaint-agent.onrender.com";

// Admin credentials from Vite environment variables
// Set VITE_ADMIN_USERNAME / VITE_ADMIN_PASSWORD in frontend/.env
const ADMIN_USERNAME = import.meta.env.VITE_ADMIN_USERNAME || 'admin'
const ADMIN_PASSWORD = import.meta.env.VITE_ADMIN_PASSWORD || 'admin123'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

// ── JWT token cache (in-memory; cleared on page reload) ────────────
let _cachedToken = null

/**
 * Obtain (or re-use) an admin JWT token.
 * On 401, call with forceRefresh=true to discard the cached token and
 * log in again.
 */
const _getAdminToken = async (forceRefresh = false) => {
  if (_cachedToken && !forceRefresh) return _cachedToken

  const response = await api.post('/api/v1/auth/login', {
    username: ADMIN_USERNAME,
    password: ADMIN_PASSWORD,
  })
  _cachedToken = response.data.access_token
  return _cachedToken
}

/**
 * Wrapper for admin requests: adds Bearer header, auto-retries once on
 * token expiry (401).
 */
const _adminRequest = async (requestFn) => {
  try {
    const token = await _getAdminToken()
    return await requestFn(token)
  } catch (err) {
    if (err.response?.status === 401) {
      // Token may have expired — refresh and retry once
      try {
        const freshToken = await _getAdminToken(true)
        return await requestFn(freshToken)
      } catch (retryErr) {
        throw retryErr
      }
    }
    throw err
  }
}

// ── Public endpoints ───────────────────────────────────────────────

/**
 * Submit a new complaint. No authentication required.
 */
export const submitComplaint = async (formData) => {
  const response = await api.post('/api/v1/complaints/create', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

/**
 * Get a single complaint by ID. Public — passengers can track their complaint.
 */
export const getComplaintById = async (complaintId) => {
  const response = await api.get(`/api/v1/complaints/${complaintId}`)
  return response.data
}

// ── Protected admin endpoints (auto-JWT) ──────────────────────────

/**
 * List all complaints. Requires admin JWT (handled automatically).
 */
export const getAllComplaints = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/complaints', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

/**
 * Trigger or re-run AI analysis on a complaint. Requires admin JWT.
 */
export const analyzeComplaint = async (complaintId) => {
  return _adminRequest(async (token) => {
    const response = await api.post(
      '/api/v1/ai/analyze-complaint',
      { complaint_id: complaintId },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  })
}

/**
 * Retrieve stored AI analysis for a complaint. Requires admin JWT.
 */
export const getComplaintAnalysis = async (complaintId) => {
  return _adminRequest(async (token) => {
    const response = await api.get(
      `/api/v1/complaints/${complaintId}/analysis`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  })
}

// ── Phase 3: Intelligence & Analytics ─────────────────────────────

export const getComplaintIntelligence = async (complaintId) => {
  return _adminRequest(async (token) => {
    const response = await api.get(
      `/api/v1/complaints/${complaintId}/intelligence`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  })
}

export const getSentimentAnalytics = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/sentiment', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getCategoryAnalytics = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/categories', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getSeverityAnalytics = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/severity', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getPriorityAnalytics = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/priorities', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getDashboardSummary = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/summary', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

// ── Phase 4: Workflow list endpoints ──────────────────────────────

export const getAssignedComplaints = async (department = '') => {
  return _adminRequest(async (token) => {
    const params = department ? `?department=${encodeURIComponent(department)}` : ''
    const response = await api.get(`/api/v1/complaints/assigned${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getEscalatedComplaints = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/complaints/escalated', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getSlaComplaints = async (status = '') => {
  return _adminRequest(async (token) => {
    const params = status ? `?status=${encodeURIComponent(status)}` : ''
    const response = await api.get(`/api/v1/complaints/sla${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getDepartmentDashboard = async (department = '') => {
  return _adminRequest(async (token) => {
    const params = department ? `?department=${encodeURIComponent(department)}` : ''
    const response = await api.get(`/api/v1/departments/dashboard${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getPerformanceAnalytics = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/performance', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

// ── Phase 4: Action mutations ─────────────────────────────────────

export const assignComplaint = async (complaintId, department, team) => {
  return _adminRequest(async (token) => {
    const response = await api.post(
      `/api/v1/complaints/${complaintId}/assign`,
      { department, team },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  })
}

export const escalateComplaint = async (complaintId, escalation_level) => {
  return _adminRequest(async (token) => {
    const response = await api.post(
      `/api/v1/complaints/${complaintId}/escalate`,
      { escalation_level },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  })
}

export const resolveComplaint = async (complaintId, resolution_notes) => {
  return _adminRequest(async (token) => {
    const response = await api.post(
      `/api/v1/complaints/${complaintId}/resolve`,
      { resolution_notes },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  })
}

export const updateComplaintStatus = async (complaintId, complaint_status) => {
  return _adminRequest(async (token) => {
    const response = await api.post(
      `/api/v1/complaints/${complaintId}/status`,
      { complaint_status },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    return response.data
  })
}

// ── Phase 5: Predictive Analytics ──────────────────────────────────

export const getTrends = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/trends', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getRouteRisks = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/routes/risk', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getDriverRisks = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/drivers/risk', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getBusRisks = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/buses/risk', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getForecast = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/forecast', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getRecommendations = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/recommendations', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getSmartAlerts = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/analytics/alerts', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getPredictiveAll = async (refresh = false) => {
  return _adminRequest(async (token) => {
    const response = await api.get(`/api/v1/analytics/predictive?refresh=${refresh}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

// ── Phase 6: Executive Intelligence ────────────────────────────────

export const getHealthIndex = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/health-index', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getGovernanceRecommendations = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/governance/recommendations', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getHeatmapData = async () => {
  return _adminRequest(async (token) => {
    const response = await api.get('/api/v1/heatmap', {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const getAIExplanation = async (complaintId) => {
  return _adminRequest(async (token) => {
    const response = await api.get(`/api/v1/explanations/${complaintId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

export const queryCopilot = async (question) => {
  return _adminRequest(async (token) => {
    const response = await api.post('/api/v1/copilot/query', { question }, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return response.data
  })
}

/**
 * Download a management report as a file (PDF or DOCX).
 * Uses the path-based endpoints: /api/v1/reports/{period}/{format}
 * Authenticates with JWT and triggers a browser file download.
 *
 * @param {string} period  - "daily" | "weekly" | "monthly"
 * @param {string} format  - "pdf" | "docx"
 */
export const downloadReport = async (period, format) => {
  return _adminRequest(async (token) => {
    const url = `${API_BASE_URL}/api/v1/reports/${period}/${format}`
    const response = await fetch(url, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
      const text = await response.text()
      throw new Error(`Report download failed (${response.status}): ${text}`)
    }
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = objectUrl
    anchor.download = `${period}_operations_report.${format}`
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(objectUrl)
  })
}

export default api


