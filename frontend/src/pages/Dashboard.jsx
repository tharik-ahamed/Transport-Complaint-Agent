import { useState, useEffect, useCallback } from 'react'
import {
  getAllComplaints,
  getDashboardSummary,
  getComplaintIntelligence,
  getDepartmentDashboard,
  getPerformanceAnalytics,
  getEscalatedComplaints,
  getSlaComplaints,
  resolveComplaint,
  escalateComplaint,
  assignComplaint,
  updateComplaintStatus,
  getPredictiveAll,
  getHealthIndex,
  getGovernanceRecommendations,
  getHeatmapData,
  queryCopilot,
  downloadReport,
} from '../api/complaintsApi'

// ── Constants ──────────────────────────────────────────────────────────
const SENTIMENT_COLOR = {
  'Positive': '#10b981', 'Neutral': '#6366f1',
  'Negative': '#f59e0b', 'Highly Negative': '#ef4444', 'Unknown': '#64748b',
}
const SEVERITY_COLOR = {
  'Critical': '#ef4444', 'High': '#f97316', 'Medium': '#f59e0b', 'Low': '#10b981', 'Unknown': '#64748b',
}
const PRIORITY_COLOR = {
  'P1': '#ef4444', 'P2': '#f97316', 'P3': '#6366f1', 'P4': '#10b981', 'Unknown': '#64748b',
}
const SLA_COLOR = {
  'Within SLA': '#10b981', 'SLA Warning': '#f59e0b', 'SLA Breached': '#ef4444',
}
const STATUS_COLOR = {
  'Submitted': '#64748b', 'AI Analysis Completed': '#6366f1',
  'Assigned': '#0ea5e9', 'In Progress': '#f59e0b',
  'Resolved': '#10b981', 'Closed': '#94a3b8',
}
const CATEGORY_COLORS = ['#6366f1','#8b5cf6','#a78bfa','#06b6d4','#0ea5e9','#10b981','#22d3ee','#f59e0b','#ef4444','#f97316']
const DEPT_COLORS = ['#6366f1','#0ea5e9','#f59e0b','#10b981','#ef4444','#a78bfa','#f97316','#ec4899','#06b6d4','#22d3ee']

const VALID_STATUSES = ['Submitted','AI Analysis Completed','Assigned','In Progress','Resolved','Closed']
const ESCALATION_LEVELS = ['Regional Operations Manager','HR Manager','Regional Transport Officer','Transport Commissioner','Chief Operations Officer']
const DEPARTMENTS = [
  'Operations Department','Human Resources Department','Vehicle Maintenance Department',
  'Regional Transport Officer','Ticketing Department','Depot Management Team',
  'Route Monitoring Department','General Administration',
]
const DEPT_TEAMS = {
  'Operations Department': ['Route Scheduling Team','Route Monitoring Team','Fleet Allocation Team'],
  'Human Resources Department': ['Driver Management Team','Conductor Management Team'],
  'Vehicle Maintenance Department': ['Fleet Maintenance Team'],
  'Regional Transport Officer': ['Safety Compliance Team'],
  'Ticketing Department': ['Fare Audit Team'],
  'Depot Management Team': ['Cleanliness Standards Team'],
  'Route Monitoring Department': ['Route Monitoring Team'],
  'General Administration': ['Customer Relations Team'],
}

// ── Tiny helpers ───────────────────────────────────────────────────────
const badge = (label, color, size = 11) => (
  <span style={{ background: color + '22', color, border: `1px solid ${color}44`, borderRadius: 6, padding: '2px 8px', fontSize: size, fontWeight: 700, whiteSpace: 'nowrap' }}>{label}</span>
)
const sectionTitle = (title) => (
  <div style={{ color: '#94a3b8', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>{title}</div>
)

// ── Donut Chart ────────────────────────────────────────────────────────
function DonutChart({ data, colors, size = 110 }) {
  const entries = Object.entries(data).filter(([, v]) => v > 0)
  const total = entries.reduce((a, [, v]) => a + v, 0)
  if (!total) return <div style={{ height: size, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: 11 }}>No data</div>
  const r = 38, cx = size / 2, cy = size / 2, stroke = 16
  let offset = 0
  const segments = entries.map(([key, val], i) => {
    const pct = val / total
    const circ = 2 * Math.PI * r
    const seg = { key, val, dasharray: `${pct * circ} ${circ}`, dashoffset: -(offset * circ), color: colors[key] || CATEGORY_COLORS[i % CATEGORY_COLORS.length] }
    offset += pct
    return seg
  })
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1e293b" strokeWidth={stroke} />
      {segments.map(s => (
        <circle key={s.key} cx={cx} cy={cy} r={r} fill="none" stroke={s.color} strokeWidth={stroke}
          strokeDasharray={s.dasharray} strokeDashoffset={s.dashoffset} transform={`rotate(-90 ${cx} ${cy})`} />
      ))}
      <text x={cx} y={cy + 5} textAnchor="middle" fill="#f1f5f9" fontSize={14} fontWeight="700">{total}</text>
    </svg>
  )
}

// ── Forecast Chart (Phase 5) ──────────────────────────────────────────
function ForecastChart({ history = [], projection = [], height = 110 }) {
  const allPoints = [...history.map(h => ({ val: h.count, type: 'history' })), ...projection.map(p => ({ val: p.predicted, type: 'projection' }))]
  const maxVal = Math.max(...allPoints.map(p => p.val), 1)
  const n = allPoints.length
  if (n < 2) return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: 11 }}>No forecast trend data</div>

  const w = 100 / (n - 1)
  const historyPoints = history.map((h, i) => `${i * w},${height - (h.count / maxVal) * (height - 20) - 10}`)
  const projectionPoints = projection.map((p, i) => `${(history.length + i) * w},${height - (p.predicted / maxVal) * (height - 20) - 10}`)

  const linePoints = [
    ...history.map((h, i) => `${i * w},${height - (h.count / maxVal) * (height - 20) - 10}`),
    ...projection.map((p, i) => `${(history.length + i) * w},${height - (p.predicted / maxVal) * (height - 20) - 10}`)
  ].join(' ')

  return (
    <svg width="100%" height={height} viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${height} ${linePoints} 100,${height}`} fill="url(#forecastGrad)" />
      
      {historyPoints.length > 1 && (
        <polyline points={historyPoints.join(' ')} fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" />
      )}
      
      {projectionPoints.length > 0 && (
        <polyline points={[`${(history.length - 1) * w},${height - (history[history.length - 1]?.count / maxVal) * (height - 20) - 10}`, ...projectionPoints].join(' ')} fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="3,3" strokeLinecap="round" />
      )}

      {history.map((h, i) => (
        <circle key={`h-${i}`} cx={i * w} cy={height - (h.count / maxVal) * (height - 20) - 10} r="2" fill="#6366f1" />
      ))}

      {projection.map((p, i) => (
        <circle key={`p-${i}`} cx={(history.length + i) * w} cy={height - (p.predicted / maxVal) * (height - 20) - 10} r="2" fill="#10b981" />
      ))}
    </svg>
  )
}

// ── Horizontal bar ─────────────────────────────────────────────────────
function HBar({ label, value, max, color }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ color: '#cbd5e1', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '75%' }}>{label}</span>
        <span style={{ color: '#94a3b8', fontSize: 11 }}>{value}</span>
      </div>
      <div style={{ background: '#1e293b', borderRadius: 4, height: 7 }}>
        <div style={{ width: `${Math.min((value / Math.max(max, 1)) * 100, 100)}%`, height: '100%', background: color, borderRadius: 4, transition: 'width 0.8s ease' }} />
      </div>
    </div>
  )
}

// ── Metric Card ────────────────────────────────────────────────────────
function MetricCard({ icon, label, value, sub, color = '#6366f1', glow, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)',
      border: `1px solid ${color}30`, borderRadius: 16, padding: '20px 22px',
      cursor: onClick ? 'pointer' : 'default',
      boxShadow: glow ? `0 0 24px ${color}25` : 'none',
      transition: 'transform 0.2s, box-shadow 0.2s',
    }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = `0 8px 32px ${color}30` }}
      onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = glow ? `0 0 24px ${color}25` : 'none' }}
    >
      <div style={{ fontSize: 24 }}>{icon}</div>
      <div style={{ color, fontSize: 32, fontWeight: 800, lineHeight: 1, marginTop: 6 }}>{value}</div>
      <div style={{ color: '#f1f5f9', fontSize: 13, fontWeight: 600, marginTop: 4 }}>{label}</div>
      {sub && <div style={{ color: '#64748b', fontSize: 11, marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

// ── Tab bar ────────────────────────────────────────────────────────────
function TabBar({ tabs, active, onSelect }) {
  return (
    <div style={{ display: 'flex', gap: 4, background: '#0f172a', borderRadius: 12, padding: 4, marginBottom: 24 }}>
      {tabs.map(t => (
        <button key={t.id} onClick={() => onSelect(t.id)} style={{
          flex: 1, padding: '8px 16px', borderRadius: 9, border: 'none', cursor: 'pointer',
          background: active === t.id ? '#1e293b' : 'transparent',
          color: active === t.id ? '#f1f5f9' : '#64748b',
          fontSize: 13, fontWeight: active === t.id ? 700 : 400,
          boxShadow: active === t.id ? '0 1px 4px #00000040' : 'none',
          transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
        }}>
          <span>{t.icon}</span><span>{t.label}</span>
          {t.badge != null && <span style={{ background: '#ef4444', color: '#fff', borderRadius: 10, padding: '1px 6px', fontSize: 10, fontWeight: 700, minWidth: 18, textAlign: 'center' }}>{t.badge}</span>}
        </button>
      ))}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════
// INTELLIGENCE PANEL (Phase 3 + Phase 4 actions)
// ══════════════════════════════════════════════════════════════════════
function IntelligencePanel({ complaint, onClose, onRefresh }) {
  const [intel, setIntel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [activeAction, setActiveAction] = useState(null)
  const [resolveNotes, setResolveNotes] = useState('')
  const [escalateLevel, setEscalateLevel] = useState(ESCALATION_LEVELS[0])
  const [assignDept, setAssignDept] = useState(DEPARTMENTS[0])
  const [assignTeam, setAssignTeam] = useState('')
  const [newStatus, setNewStatus] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    getComplaintIntelligence(complaint.complaint_id)
      .then(setIntel).catch(() => setIntel(null)).finally(() => setLoading(false))
  }, [complaint.complaint_id])

  const doAction = async (fn, successText) => {
    setActionLoading(true); setErrorMsg('')
    try {
      await fn()
      setSuccessMsg(successText)
      setActiveAction(null)
      setTimeout(() => { setSuccessMsg(''); onRefresh() }, 2000)
    } catch (e) {
      setErrorMsg(e?.response?.data?.detail || 'Action failed')
    } finally {
      setActionLoading(false)
    }
  }

  const slaColor = SLA_COLOR[complaint.sla_status] || '#64748b'
  const statusColor = STATUS_COLOR[complaint.complaint_status] || '#64748b'

  return (
    <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 500, background: 'linear-gradient(180deg,#0f172a 0%,#0d1526 100%)', borderLeft: '1px solid #1e293b', zIndex: 200, overflowY: 'auto', display: 'flex', flexDirection: 'column', animation: 'slideIn 0.3s ease' }}>
      <style>{`@keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}} @keyframes spin{to{transform:rotate(360deg)}}`}</style>

      {/* Header */}
      <div style={{ padding: '18px 22px', borderBottom: '1px solid #1e293b', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, background: '#0f172a', zIndex: 10 }}>
        <div>
          <div style={{ color: '#6366f1', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Intelligence · Phase 3+4</div>
          <div style={{ color: '#f1f5f9', fontSize: 16, fontWeight: 700 }}>{complaint.complaint_id}</div>
        </div>
        <button onClick={onClose} style={{ background: '#1e293b', border: '1px solid #334155', color: '#94a3b8', borderRadius: 8, width: 32, height: 32, cursor: 'pointer', fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>
      </div>

      {/* Success / Error banners */}
      {successMsg && <div style={{ margin: '12px 22px 0', background: '#10b98120', border: '1px solid #10b981', borderRadius: 8, padding: '8px 14px', color: '#10b981', fontSize: 13 }}>✓ {successMsg}</div>}
      {errorMsg && <div style={{ margin: '12px 22px 0', background: '#ef444420', border: '1px solid #ef4444', borderRadius: 8, padding: '8px 14px', color: '#ef4444', fontSize: 13 }}>✗ {errorMsg}</div>}

      {/* Complaint brief */}
      <div style={{ padding: '14px 22px', borderBottom: '1px solid #1e2d45' }}>
        <div style={{ color: '#f1f5f9', fontSize: 12, lineHeight: 1.5 }}>{complaint.complaint_description?.slice(0, 200)}{complaint.complaint_description?.length > 200 ? '…' : ''}</div>
        <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ color: '#64748b', fontSize: 11 }}>📍 {complaint.incident_location}</span>
          <span style={{ color: '#64748b', fontSize: 11 }}>🚌 {complaint.bus_number}</span>
          <span style={{ color: '#64748b', fontSize: 11 }}>🗺 R:{complaint.route_number}</span>
        </div>
      </div>

      <div style={{ padding: '14px 22px', display: 'flex', flexDirection: 'column', gap: 12 }}>

        {/* Workflow Status + SLA */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div style={{ background: '#1e293b', borderRadius: 11, padding: 14, border: `1px solid ${statusColor}30` }}>
            {sectionTitle('Status')}
            <span style={{ background: statusColor + '25', color: statusColor, border: `1px solid ${statusColor}50`, borderRadius: 7, padding: '5px 10px', fontSize: 12, fontWeight: 700 }}>{complaint.complaint_status || '—'}</span>
          </div>
          <div style={{ background: '#1e293b', borderRadius: 11, padding: 14, border: `1px solid ${slaColor}30` }}>
            {sectionTitle('SLA')}
            <span style={{ background: slaColor + '25', color: slaColor, border: `1px solid ${slaColor}50`, borderRadius: 7, padding: '5px 10px', fontSize: 12, fontWeight: 700 }}>{complaint.sla_status || 'Not set'}</span>
            {complaint.sla_deadline && <div style={{ color: '#64748b', fontSize: 10, marginTop: 6 }}>Due: {new Date(complaint.sla_deadline).toLocaleString()}</div>}
          </div>
        </div>

        {/* Routing */}
        <div style={{ background: '#1e293b', borderRadius: 11, padding: 14 }}>
          {sectionTitle('Assigned To')}
          <div style={{ color: '#0ea5e9', fontSize: 13, fontWeight: 700 }}>{complaint.assigned_department || '—'}</div>
          <div style={{ color: '#64748b', fontSize: 11, marginTop: 3 }}>{complaint.assigned_team || '—'}</div>
          {complaint.assigned_at && <div style={{ color: '#475569', fontSize: 10, marginTop: 4 }}>Assigned: {new Date(complaint.assigned_at).toLocaleString()}</div>}
        </div>

        {/* Escalation */}
        {complaint.escalation_status && (
          <div style={{ background: 'linear-gradient(135deg,#3d1515 0%,#1e293b 100%)', borderRadius: 11, padding: 14, border: '1px solid #ef444430' }}>
            {sectionTitle('Escalation')}
            <div style={{ color: '#ef4444', fontWeight: 700, fontSize: 13 }}>🚨 {complaint.escalation_level}</div>
            {complaint.escalated_at && <div style={{ color: '#64748b', fontSize: 10, marginTop: 4 }}>Escalated: {new Date(complaint.escalated_at).toLocaleString()}</div>}
          </div>
        )}

        {/* Phase 3 AI data */}
        {!loading && intel && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div style={{ background: '#1e293b', borderRadius: 11, padding: 14 }}>
                {sectionTitle('Sentiment')}
                <span style={{ background: (SENTIMENT_COLOR[intel.sentiment] || '#64748b') + '25', color: SENTIMENT_COLOR[intel.sentiment] || '#64748b', border: `1px solid ${(SENTIMENT_COLOR[intel.sentiment] || '#64748b')}50`, borderRadius: 7, padding: '5px 10px', fontSize: 12, fontWeight: 700 }}>{intel.sentiment || '—'}</span>
              </div>
              <div style={{ background: '#1e293b', borderRadius: 11, padding: 14 }}>
                {sectionTitle('Severity')}
                <div style={{ color: SEVERITY_COLOR[intel.severity] || '#64748b', fontSize: 20, fontWeight: 800 }}>{intel.severity || '—'}</div>
              </div>
            </div>
            {intel.categories?.length > 0 && (
              <div style={{ background: '#1e293b', borderRadius: 11, padding: 14 }}>
                {sectionTitle('AI Categories')}
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {intel.categories.map((cat, i) => <span key={cat} style={{ background: CATEGORY_COLORS[i % CATEGORY_COLORS.length] + '22', color: CATEGORY_COLORS[i % CATEGORY_COLORS.length], border: `1px solid ${CATEGORY_COLORS[i % CATEGORY_COLORS.length]}44`, borderRadius: 6, padding: '3px 9px', fontSize: 11, fontWeight: 600 }}>{cat}</span>)}
                </div>
              </div>
            )}
            {intel.recommendation && (
              <div style={{ background: 'linear-gradient(135deg,#1e3a5f 0%,#1e293b 100%)', borderRadius: 11, padding: 14, border: '1px solid #2563eb30' }}>
                <div style={{ color: '#60a5fa', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>💡 Recommendation</div>
                <div style={{ color: '#e2e8f0', fontSize: 12, lineHeight: 1.6 }}>{intel.recommendation}</div>
              </div>
            )}
          </>
        )}

        {/* Resolution info */}
        {complaint.resolution_notes && (
          <div style={{ background: 'linear-gradient(135deg,#0f2a1a 0%,#1e293b 100%)', borderRadius: 11, padding: 14, border: '1px solid #10b98130' }}>
            {sectionTitle('Resolution')}
            <div style={{ color: '#d1fae5', fontSize: 12, lineHeight: 1.5 }}>{complaint.resolution_notes}</div>
            <div style={{ marginTop: 8, display: 'flex', gap: 12 }}>
              {complaint.resolved_by && <span style={{ color: '#10b981', fontSize: 11 }}>👤 {complaint.resolved_by}</span>}
              {complaint.resolution_time && <span style={{ color: '#10b981', fontSize: 11 }}>⏱ {complaint.resolution_time}</span>}
            </div>
          </div>
        )}

        {/* ── Phase 4 Action Panel ─────────────────────────────────── */}
        <div style={{ background: '#0f172a', borderRadius: 12, border: '1px solid #1e293b', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #1e293b', color: '#94a3b8', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>⚙️ Actions</div>

          {/* Action buttons */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, background: '#1e293b' }}>
            {[
              { id: 'status', label: 'Update Status', icon: '🔄', color: '#6366f1' },
              { id: 'assign', label: 'Re-Assign', icon: '📋', color: '#0ea5e9' },
              { id: 'escalate', label: 'Escalate', icon: '🚨', color: '#f97316' },
              { id: 'resolve', label: 'Resolve', icon: '✅', color: '#10b981' },
            ].map(btn => (
              <button key={btn.id} onClick={() => setActiveAction(activeAction === btn.id ? null : btn.id)}
                disabled={complaint.complaint_status === 'Closed'}
                style={{
                  background: activeAction === btn.id ? btn.color + '20' : '#0f172a',
                  border: 'none', color: activeAction === btn.id ? btn.color : '#94a3b8',
                  padding: '12px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                  transition: 'all 0.2s', opacity: complaint.complaint_status === 'Closed' ? 0.4 : 1,
                }}>
                <span style={{ fontSize: 18 }}>{btn.icon}</span>
                {btn.label}
              </button>
            ))}
          </div>

          {/* Action forms */}
          {activeAction === 'status' && (
            <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <select value={newStatus} onChange={e => setNewStatus(e.target.value)}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                <option value="">Select status…</option>
                {VALID_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <button disabled={!newStatus || actionLoading} onClick={() => doAction(() => updateComplaintStatus(complaint.complaint_id, newStatus), `Status updated to "${newStatus}"`)}
                style={{ background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '9px', fontSize: 12, fontWeight: 700, cursor: 'pointer', opacity: !newStatus || actionLoading ? 0.5 : 1 }}>
                {actionLoading ? 'Updating…' : 'Update Status'}
              </button>
            </div>
          )}

          {activeAction === 'assign' && (
            <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <select value={assignDept} onChange={e => { setAssignDept(e.target.value); setAssignTeam('') }}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
              <select value={assignTeam} onChange={e => setAssignTeam(e.target.value)}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                <option value="">Select team…</option>
                {(DEPT_TEAMS[assignDept] || []).map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <button disabled={!assignTeam || actionLoading} onClick={() => doAction(() => assignComplaint(complaint.complaint_id, assignDept, assignTeam), `Assigned to ${assignDept}`)}
                style={{ background: '#0ea5e9', color: '#fff', border: 'none', borderRadius: 8, padding: '9px', fontSize: 12, fontWeight: 700, cursor: 'pointer', opacity: !assignTeam || actionLoading ? 0.5 : 1 }}>
                {actionLoading ? 'Assigning…' : 'Assign'}
              </button>
            </div>
          )}

          {activeAction === 'escalate' && (
            <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <select value={escalateLevel} onChange={e => setEscalateLevel(e.target.value)}
                style={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
                {ESCALATION_LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
              <button disabled={actionLoading} onClick={() => doAction(() => escalateComplaint(complaint.complaint_id, escalateLevel), `Escalated to ${escalateLevel}`)}
                style={{ background: '#f97316', color: '#fff', border: 'none', borderRadius: 8, padding: '9px', fontSize: 12, fontWeight: 700, cursor: 'pointer', opacity: actionLoading ? 0.5 : 1 }}>
                {actionLoading ? 'Escalating…' : 'Escalate Now'}
              </button>
            </div>
          )}

          {activeAction === 'resolve' && (
            <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <textarea value={resolveNotes} onChange={e => setResolveNotes(e.target.value)} placeholder="Enter resolution notes…"
                rows={4} style={{ background: '#1e293b', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 8, padding: '8px 12px', fontSize: 12, resize: 'vertical', fontFamily: 'inherit' }} />
              <button disabled={!resolveNotes.trim() || actionLoading} onClick={() => doAction(() => resolveComplaint(complaint.complaint_id, resolveNotes), 'Complaint resolved')}
                style={{ background: '#10b981', color: '#fff', border: 'none', borderRadius: 8, padding: '9px', fontSize: 12, fontWeight: 700, cursor: 'pointer', opacity: !resolveNotes.trim() || actionLoading ? 0.5 : 1 }}>
                {actionLoading ? 'Resolving…' : 'Mark Resolved'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════
// COMPLAINTS TABLE
// ══════════════════════════════════════════════════════════════════════
function ComplaintsTable({ complaints, selectedId, onSelect }) {
  if (!complaints.length) return <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>No complaints match the current filters.</div>
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#0f172a' }}>
            {['ID','Passenger','Bus/Route','Category','Sentiment','Severity','Priority','SLA','Status','Dept','Action'].map(h => (
              <th key={h} style={{ padding: '10px 14px', textAlign: 'left', color: '#64748b', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', whiteSpace: 'nowrap', borderBottom: '1px solid #1e2d45' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {complaints.map((c, idx) => {
            const isActive = selectedId === c.complaint_id
            const slaClr = SLA_COLOR[c.sla_status] || '#64748b'
            const statusClr = STATUS_COLOR[c.complaint_status] || '#64748b'
            return (
              <tr key={c.complaint_id} style={{ borderBottom: '1px solid #1e2d45', background: isActive ? '#1e293b' : (idx % 2 === 0 ? 'transparent' : '#0d1526'), transition: 'background 0.15s', cursor: 'pointer' }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = '#1e2d45' }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = idx % 2 === 0 ? 'transparent' : '#0d1526' }}
              >
                <td style={{ padding: '10px 14px', fontSize: 11, color: '#a78bfa', fontWeight: 700, whiteSpace: 'nowrap' }}>
                  {c.complaint_id}
                  {c.escalation_status ? <span style={{ marginLeft: 4, color: '#ef4444', fontSize: 10 }}>🚨</span> : null}
                  {c.duplicate_detected ? <span style={{ marginLeft: 2, color: '#f59e0b', fontSize: 10 }}>🔗</span> : null}
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <div style={{ color: '#f1f5f9', fontSize: 11, fontWeight: 600 }}>{c.passenger_name}</div>
                  <div style={{ color: '#475569', fontSize: 10 }}>{c.email?.split('@')[0]}@…</div>
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <div style={{ color: '#cbd5e1', fontSize: 11 }}>{c.bus_number}</div>
                  <div style={{ color: '#475569', fontSize: 10 }}>R:{c.route_number}</div>
                </td>
                <td style={{ padding: '10px 14px' }}>{badge(c.category, '#6366f1', 10)}</td>
                <td style={{ padding: '10px 14px' }}>{c.sentiment ? badge(c.sentiment, SENTIMENT_COLOR[c.sentiment] || '#64748b', 10) : <span style={{ color: '#334155', fontSize: 10 }}>—</span>}</td>
                <td style={{ padding: '10px 14px' }}>
                  {c.severity ? <span style={{ color: SEVERITY_COLOR[c.severity] || '#64748b', fontWeight: 700, fontSize: 11 }}>{c.severity}</span> : <span style={{ color: '#334155', fontSize: 10 }}>—</span>}
                </td>
                <td style={{ padding: '10px 14px' }}>
                  {c.priority_level ? <span style={{ background: (PRIORITY_COLOR[c.priority_level] || '#64748b') + '22', color: PRIORITY_COLOR[c.priority_level] || '#64748b', border: `1px solid ${(PRIORITY_COLOR[c.priority_level] || '#64748b')}44`, borderRadius: 5, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>{c.priority_level}</span> : <span style={{ color: '#334155', fontSize: 10 }}>—</span>}
                </td>
                <td style={{ padding: '10px 14px' }}>
                  {c.sla_status ? <span style={{ color: slaClr, fontSize: 10, fontWeight: 700 }}>{c.sla_status}</span> : <span style={{ color: '#334155', fontSize: 10 }}>—</span>}
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{ background: statusClr + '22', color: statusClr, borderRadius: 5, padding: '2px 7px', fontSize: 10, fontWeight: 600 }}>{c.complaint_status || '—'}</span>
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <div style={{ color: '#94a3b8', fontSize: 10, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.assigned_department || '—'}</div>
                </td>
                <td style={{ padding: '10px 14px' }}>
                  <button onClick={() => onSelect(isActive ? null : c)}
                    style={{ background: isActive ? '#6366f1' : 'transparent', border: `1px solid ${isActive ? '#6366f1' : '#334155'}`, color: isActive ? '#fff' : '#94a3b8', borderRadius: 7, padding: '4px 10px', fontSize: 10, cursor: 'pointer', fontWeight: 600, transition: 'all 0.2s', whiteSpace: 'nowrap' }}>
                    {isActive ? 'Close' : '🧠 View'}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════
// MAIN DASHBOARD
// ══════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [complaints, setComplaints] = useState([])
  const [escalated, setEscalated] = useState([])
  const [slaList, setSlaList] = useState([])
  const [summary, setSummary] = useState(null)
  const [deptData, setDeptData] = useState(null)
  const [perfData, setPerfData] = useState(null)
  const [predictiveData, setPredictiveData] = useState(null)
  const [executiveData, setExecutiveData] = useState(null)    // Phase 6
  const [copilotQ, setCopilotQ] = useState('')
  const [copilotLoading, setCopilotLoading] = useState(false)
  const [copilotResult, setCopilotResult] = useState(null)
  const [copilotError, setCopilotError] = useState(null)
  const [reportDownloading, setReportDownloading] = useState({}) // { "daily-pdf": true, ... }
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedComplaint, setSelectedComplaint] = useState(null)
  const [filter, setFilter] = useState({ search: '', severity: '', priority: '', sentiment: '', department: '', status: '' })

  const fetchAll = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [c, s, e, sla, dept, perf, pred] = await Promise.all([
        getAllComplaints(),
        getDashboardSummary(),
        getEscalatedComplaints(),
        getSlaComplaints(),
        getDepartmentDashboard(),
        getPerformanceAnalytics(),
        getPredictiveAll(true),
      ])
      setComplaints(c.complaints || [])
      setSummary(s)
      setEscalated(e.complaints || [])
      setSlaList(sla.complaints || [])
      setDeptData(dept)
      setPerfData(perf)
      setPredictiveData(pred)
      // Phase 6 — executive data fetched separately to not block main dashboard
      getHealthIndex().then(hi =>
        getGovernanceRecommendations().then(gov =>
          getHeatmapData().then(hm =>
            setExecutiveData({ health: hi, governance: gov, heatmap: hm })
          )
        )
      ).catch(() => {}) // non-blocking
    } catch (err) {
      setError('Failed to load dashboard data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  const filtered = complaints.filter(c => {
    const s = filter.search.toLowerCase()
    const ms = !s || [c.complaint_id, c.passenger_name, c.bus_number, c.route_number, c.complaint_description, c.incident_location, c.assigned_department].some(f => f?.toLowerCase().includes(s))
    return ms
      && (!filter.severity || c.severity === filter.severity)
      && (!filter.priority || c.priority_level === filter.priority)
      && (!filter.sentiment || c.sentiment === filter.sentiment)
      && (!filter.department || (c.assigned_department || '').toLowerCase().includes(filter.department.toLowerCase()))
      && (!filter.status || c.complaint_status === filter.status)
  })

  const metrics = summary?.metrics || {}
  const slaBreachCount = slaList.filter(c => c.sla_status === 'SLA Breached').length
  const escalatedCount = escalated.length
  const alertCount = predictiveData?.alerts?.length || 0

  const TABS = [
    { id: 'overview', icon: '📊', label: 'Overview' },
    { id: 'complaints', icon: '📋', label: 'All Complaints' },
    { id: 'escalated', icon: '🚨', label: 'Escalated', badge: escalatedCount || null },
    { id: 'sla', icon: '⏱', label: 'SLA Monitor', badge: slaBreachCount || null },
    { id: 'departments', icon: '🏢', label: 'Departments' },
    { id: 'performance', icon: '📈', label: 'Performance' },
    { id: 'predictive', icon: '🧠', label: 'Predictive', badge: alertCount || null },
    { id: 'executive', icon: '🌟', label: 'Executive Intelligence' },
  ]

  const cs = (v, dict) => dict[v] || '#64748b'

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg,#0a0f1e 0%,#0f172a 50%,#0a0f1e 100%)', color: '#f1f5f9', fontFamily: '"Inter",sans-serif' }}>
      {selectedComplaint && (
        <>
          <div onClick={() => setSelectedComplaint(null)} style={{ position: 'fixed', inset: 0, background: '#00000060', zIndex: 150 }} />
          <IntelligencePanel complaint={selectedComplaint} onClose={() => setSelectedComplaint(null)} onRefresh={() => { fetchAll(); setSelectedComplaint(null) }} />
        </>
      )}

      {/* Top Bar */}
      <div style={{ background: 'rgba(15,23,42,0.96)', backdropFilter: 'blur(20px)', borderBottom: '1px solid #1e293b', padding: '0 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64, position: 'sticky', top: 0, zIndex: 100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 32, height: 32, background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>⚡</div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>Transport Complaint Agent</div>
            <div style={{ fontSize: 10, color: '#6366f1', fontWeight: 700, letterSpacing: '0.1em' }}>ADMIN DASHBOARD · PHASE 4</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <a href="/" style={{ textDecoration: 'none', color: '#94a3b8', fontSize: 12, padding: '6px 14px', borderRadius: 8, border: '1px solid #1e293b' }}>＋ New Complaint</a>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" style={{ textDecoration: 'none', color: '#94a3b8', fontSize: 12, padding: '6px 14px', borderRadius: 8, border: '1px solid #1e293b' }}>API Docs</a>
          <button onClick={fetchAll} style={{ background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '6px 14px', fontSize: 12, cursor: 'pointer', fontWeight: 700 }}>↺ Refresh</button>
        </div>
      </div>

      <div style={{ maxWidth: 1500, margin: '0 auto', padding: '28px 32px' }}>
        {loading && <div style={{ textAlign: 'center', padding: 80, color: '#64748b' }}><div style={{ fontSize: 40, animation: 'spin 1.5s linear infinite', display: 'inline-block' }}>⚙️</div><style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style><div style={{ marginTop: 12 }}>Loading dashboard…</div></div>}
        {error && <div style={{ background: '#2d1515', border: '1px solid #ef4444', borderRadius: 12, padding: 20, color: '#fca5a5', marginBottom: 24 }}>⚠️ {error}</div>}

        {!loading && !error && (
          <>
            {/* Tab Navigation */}
            <TabBar tabs={TABS} active={activeTab} onSelect={setActiveTab} />

            {/* ══ OVERVIEW TAB ══ */}
            {activeTab === 'overview' && (
              <>
                {/* Metric cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 14, marginBottom: 24 }}>
                  <MetricCard icon="📋" label="Total" value={metrics.total_complaints ?? 0} color="#6366f1" onClick={() => setActiveTab('complaints')} />
                  <MetricCard icon="🔴" label="Critical" value={metrics.critical_complaints ?? 0} color="#ef4444" glow={metrics.critical_complaints > 0} onClick={() => setActiveTab('complaints')} />
                  <MetricCard icon="⚡" label="High Priority" value={metrics.high_priority_complaints ?? 0} color="#f97316" glow={metrics.high_priority_complaints > 0} />
                  <MetricCard icon="🔗" label="Duplicates" value={metrics.duplicate_groups ?? 0} color="#a78bfa" />
                  <MetricCard icon="🚨" label="Escalated" value={escalatedCount} color="#ef4444" glow={escalatedCount > 0} onClick={() => setActiveTab('escalated')} />
                  <MetricCard icon="⏱" label="SLA Breaches" value={slaBreachCount} color="#f59e0b" glow={slaBreachCount > 0} onClick={() => setActiveTab('sla')} />
                </div>

                {/* Charts row */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
                  {[
                    { title: 'Sentiment', data: summary?.sentiment || {}, colors: SENTIMENT_COLOR },
                    { title: 'Severity', data: summary?.severity || {}, colors: SEVERITY_COLOR },
                    { title: 'Priority', data: summary?.priorities || {}, colors: PRIORITY_COLOR },
                    { title: 'SLA Status', data: Object.fromEntries(slaList.reduce((m, c) => { const k = c.sla_status || 'Unknown'; m.set(k, (m.get(k) || 0) + 1); return m }, new Map())), colors: SLA_COLOR },
                  ].map(({ title, data, colors }) => (
                    <div key={title} style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 20 }}>
                      <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 14 }}>{title}</div>
                      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 14 }}>
                        <DonutChart data={data} colors={colors} size={100} />
                      </div>
                      {Object.entries(data).filter(([, v]) => v > 0).map(([k, v]) => (
                        <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 7, height: 7, borderRadius: '50%', background: colors[k] || '#64748b' }} />
                            <span style={{ color: '#94a3b8', fontSize: 10 }}>{k}</span>
                          </div>
                          <span style={{ color: '#f1f5f9', fontSize: 10, fontWeight: 600 }}>{v}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>

                {/* Category bar + dept bars */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                    <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 16 }}>Category Distribution</div>
                    {Object.entries(summary?.categories || {}).slice(0, 8).map(([k, v], i) => (
                      <HBar key={k} label={k} value={v} max={Math.max(...Object.values(summary?.categories || { x: 1 }))} color={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                    ))}
                  </div>
                  <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                    <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 16 }}>Department Workload</div>
                    {(deptData?.departments || []).slice(0, 8).map((d, i) => (
                      <HBar key={d.department} label={d.department} value={d.total} max={Math.max(...(deptData?.departments || [{ total: 1 }]).map(x => x.total))} color={DEPT_COLORS[i % DEPT_COLORS.length]} />
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* ══ ALL COMPLAINTS TAB ══ */}
            {activeTab === 'complaints' && (
              <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, overflow: 'hidden' }}>
                {/* Toolbar */}
                <div style={{ padding: '18px 22px', borderBottom: '1px solid #1e2d45', display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                  <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, flex: 1 }}>All Complaints <span style={{ color: '#64748b', fontWeight: 400, fontSize: 12 }}>({filtered.length})</span></div>
                  <input placeholder="🔍 Search…" value={filter.search} onChange={e => setFilter(f => ({ ...f, search: e.target.value }))}
                    style={{ background: '#0f172a', border: '1px solid #334155', color: '#f1f5f9', borderRadius: 8, padding: '6px 12px', fontSize: 11, outline: 'none', width: 160 }} />
                  {[
                    ['severity', 'Severity', ['Critical','High','Medium','Low']],
                    ['priority', 'Priority', ['P1','P2','P3','P4']],
                    ['sentiment', 'Sentiment', ['Positive','Neutral','Negative','Highly Negative']],
                    ['status', 'Status', VALID_STATUSES],
                  ].map(([key, label, opts]) => (
                    <select key={key} value={filter[key]} onChange={e => setFilter(f => ({ ...f, [key]: e.target.value }))}
                      style={{ background: '#0f172a', border: '1px solid #334155', color: filter[key] ? '#f1f5f9' : '#64748b', borderRadius: 8, padding: '6px 10px', fontSize: 11, outline: 'none' }}>
                      <option value="">{label}</option>
                      {opts.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ))}
                  {Object.values(filter).some(Boolean) && (
                    <button onClick={() => setFilter({ search:'', severity:'', priority:'', sentiment:'', department:'', status:'' })}
                      style={{ background: 'transparent', border: '1px solid #334155', color: '#94a3b8', borderRadius: 8, padding: '6px 12px', fontSize: 11, cursor: 'pointer' }}>Clear</button>
                  )}
                </div>
                <ComplaintsTable complaints={filtered} selectedId={selectedComplaint?.complaint_id} onSelect={setSelectedComplaint} />
              </div>
            )}

            {/* ══ ESCALATED TAB ══ */}
            {activeTab === 'escalated' && (
              <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #ef444430', borderRadius: 16, overflow: 'hidden' }}>
                <div style={{ padding: '18px 22px', borderBottom: '1px solid #1e2d45', display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 20 }}>🚨</span>
                  <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13 }}>Escalated Complaints <span style={{ color: '#ef4444', fontWeight: 400, fontSize: 12 }}>({escalated.length})</span></div>
                </div>
                {escalated.length === 0 ? (
                  <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>✓ No escalated complaints</div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: '#0f172a' }}>
                          {['ID','Passenger','Category','Severity','Escalation Level','SLA','Status','Department','Action'].map(h => (
                            <th key={h} style={{ padding: '10px 14px', textAlign: 'left', color: '#64748b', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', whiteSpace: 'nowrap', borderBottom: '1px solid #1e2d45' }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {escalated.map((c, idx) => (
                          <tr key={c.complaint_id} style={{ borderBottom: '1px solid #1e2d45', background: idx % 2 === 0 ? 'transparent' : '#0d1526' }}>
                            <td style={{ padding: '10px 14px', color: '#a78bfa', fontSize: 11, fontWeight: 700 }}>{c.complaint_id}</td>
                            <td style={{ padding: '10px 14px', color: '#f1f5f9', fontSize: 11 }}>{c.passenger_name}</td>
                            <td style={{ padding: '10px 14px' }}>{badge(c.category, '#6366f1', 10)}</td>
                            <td style={{ padding: '10px 14px' }}><span style={{ color: cs(c.severity, SEVERITY_COLOR), fontWeight: 700, fontSize: 11 }}>{c.severity || '—'}</span></td>
                            <td style={{ padding: '10px 14px' }}><span style={{ color: '#ef4444', fontSize: 11, fontWeight: 600 }}>🚨 {c.escalation_level}</span></td>
                            <td style={{ padding: '10px 14px' }}><span style={{ color: cs(c.sla_status, SLA_COLOR), fontSize: 10, fontWeight: 700 }}>{c.sla_status || '—'}</span></td>
                            <td style={{ padding: '10px 14px' }}><span style={{ color: cs(c.complaint_status, STATUS_COLOR), fontSize: 10 }}>{c.complaint_status || '—'}</span></td>
                            <td style={{ padding: '10px 14px', color: '#94a3b8', fontSize: 10 }}>{c.assigned_department || '—'}</td>
                            <td style={{ padding: '10px 14px' }}>
                              <button onClick={() => { setSelectedComplaint(complaints.find(x => x.complaint_id === c.complaint_id) || c); setActiveTab('complaints') }}
                                style={{ background: 'transparent', border: '1px solid #334155', color: '#94a3b8', borderRadius: 7, padding: '4px 10px', fontSize: 10, cursor: 'pointer' }}>🧠 View</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* ══ SLA MONITOR TAB ══ */}
            {activeTab === 'sla' && (
              <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #f59e0b30', borderRadius: 16, overflow: 'hidden' }}>
                <div style={{ padding: '18px 22px', borderBottom: '1px solid #1e2d45', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ fontSize: 20 }}>⏱</span>
                    <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13 }}>SLA Monitor</div>
                  </div>
                  <div style={{ display: 'flex', gap: 16 }}>
                    {[['SLA Breached', '#ef4444'], ['SLA Warning', '#f59e0b'], ['Within SLA', '#10b981']].map(([label, color]) => (
                      <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                        <span style={{ color: '#94a3b8', fontSize: 11 }}>{label}: {slaList.filter(c => c.sla_status === label).length}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: '#0f172a' }}>
                        {['ID','Passenger','Severity','SLA Deadline','Time Remaining','SLA Status','Workflow Status','Department'].map(h => (
                          <th key={h} style={{ padding: '10px 14px', textAlign: 'left', color: '#64748b', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', whiteSpace: 'nowrap', borderBottom: '1px solid #1e2d45' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {slaList.map((c, idx) => {
                        const deadlineDate = c.sla_deadline ? new Date(c.sla_deadline) : null
                        const slaClr = SLA_COLOR[c.sla_status] || '#64748b'
                        const timeRemaining = deadlineDate ? (() => {
                          const diff = deadlineDate - Date.now()
                          if (diff < 0) return 'Overdue'
                          const h = Math.floor(diff / 3600000)
                          const m = Math.floor((diff % 3600000) / 60000)
                          return h > 0 ? `${h}h ${m}m` : `${m}m`
                        })() : '—'
                        return (
                          <tr key={c.complaint_id} style={{ borderBottom: '1px solid #1e2d45', background: c.sla_status === 'SLA Breached' ? '#2d150f' : idx % 2 === 0 ? 'transparent' : '#0d1526' }}>
                            <td style={{ padding: '10px 14px', color: '#a78bfa', fontSize: 11, fontWeight: 700 }}>{c.complaint_id}</td>
                            <td style={{ padding: '10px 14px', color: '#f1f5f9', fontSize: 11 }}>{c.passenger_name}</td>
                            <td style={{ padding: '10px 14px' }}><span style={{ color: cs(c.severity, SEVERITY_COLOR), fontWeight: 700, fontSize: 11 }}>{c.severity || '—'}</span></td>
                            <td style={{ padding: '10px 14px', color: '#94a3b8', fontSize: 10, whiteSpace: 'nowrap' }}>{deadlineDate ? deadlineDate.toLocaleString() : '—'}</td>
                            <td style={{ padding: '10px 14px' }}><span style={{ color: slaClr, fontWeight: 700, fontSize: 11 }}>{timeRemaining}</span></td>
                            <td style={{ padding: '10px 14px' }}><span style={{ background: slaClr + '22', color: slaClr, border: `1px solid ${slaClr}44`, borderRadius: 6, padding: '2px 8px', fontSize: 10, fontWeight: 700 }}>{c.sla_status}</span></td>
                            <td style={{ padding: '10px 14px' }}><span style={{ color: cs(c.complaint_status, STATUS_COLOR), fontSize: 10 }}>{c.complaint_status}</span></td>
                            <td style={{ padding: '10px 14px', color: '#64748b', fontSize: 10 }}>{c.assigned_department || '—'}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ══ DEPARTMENTS TAB ══ */}
            {activeTab === 'departments' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {/* Department Cards grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
                  {(deptData?.departments || []).map((d, i) => (
                    <div key={d.department} style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: `1px solid ${DEPT_COLORS[i % DEPT_COLORS.length]}30`, borderRadius: 16, padding: 20, transition: 'transform 0.2s', cursor: 'pointer' }}
                      onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                      onMouseLeave={e => e.currentTarget.style.transform = ''}
                      onClick={() => { setFilter(f => ({ ...f, department: d.department })); setActiveTab('complaints') }}
                    >
                      <div style={{ color: DEPT_COLORS[i % DEPT_COLORS.length], fontSize: 13, fontWeight: 700, marginBottom: 12 }}>{d.department}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        {[
                          { label: 'Total', value: d.total, color: '#f1f5f9' },
                          { label: 'Open', value: d.open, color: '#0ea5e9' },
                          { label: 'Escalated', value: d.escalated, color: '#ef4444' },
                          { label: 'SLA Breached', value: d.sla_breached, color: '#f59e0b' },
                          { label: 'Resolved', value: d.resolved, color: '#10b981' },
                        ].map(({ label, value, color }) => (
                          <div key={label} style={{ background: '#0f172a', borderRadius: 8, padding: '8px 12px' }}>
                            <div style={{ color: '#64748b', fontSize: 10 }}>{label}</div>
                            <div style={{ color: value > 0 && color !== '#f1f5f9' ? color : '#f1f5f9', fontSize: 20, fontWeight: 800 }}>{value}</div>
                          </div>
                        ))}
                        <div style={{ background: '#0f172a', borderRadius: 8, padding: '8px 12px' }}>
                          <div style={{ color: '#64748b', fontSize: 10 }}>Resolution</div>
                          <div style={{ color: '#f1f5f9', fontSize: 20, fontWeight: 800 }}>{d.total > 0 ? Math.round((d.resolved / d.total) * 100) : 0}%</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Department complaints table */}
                <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, overflow: 'hidden' }}>
                  <div style={{ padding: '18px 22px', borderBottom: '1px solid #1e2d45', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, flex: 1 }}>Department Complaints</div>
                    <select value={filter.department} onChange={e => setFilter(f => ({ ...f, department: e.target.value }))}
                      style={{ background: '#0f172a', border: '1px solid #334155', color: filter.department ? '#f1f5f9' : '#64748b', borderRadius: 8, padding: '6px 10px', fontSize: 11 }}>
                      <option value="">All Departments</option>
                      {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                    {filter.department && <button onClick={() => setFilter(f => ({ ...f, department: '' }))} style={{ background: 'transparent', border: '1px solid #334155', color: '#94a3b8', borderRadius: 8, padding: '6px 12px', fontSize: 11, cursor: 'pointer' }}>Clear</button>}
                  </div>
                  <ComplaintsTable complaints={complaints.filter(c => !filter.department || (c.assigned_department || '').toLowerCase().includes(filter.department.toLowerCase()))} selectedId={selectedComplaint?.complaint_id} onSelect={setSelectedComplaint} />
                </div>
              </div>
            )}

            {/* ══ PERFORMANCE TAB ══ */}
            {activeTab === 'performance' && perfData && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {/* Headline performance metrics */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14 }}>
                  <MetricCard icon="⏱" label="Avg Resolution" value={perfData.resolution_time?.average_human || '—'} sub={`${perfData.resolved_count} complaints resolved`} color="#10b981" />
                  <MetricCard icon="✅" label="SLA Compliance" value={`${perfData.sla_compliance?.percentage ?? 0}%`} sub={`${perfData.sla_compliance?.within_sla} within SLA`} color="#6366f1" />
                  <MetricCard icon="🚨" label="Escalation Rate" value={`${perfData.escalation?.escalation_rate_pct ?? 0}%`} sub={`${perfData.escalation?.escalated_count} total escalated`} color="#f97316" glow={perfData.escalation?.escalated_count > 0} />
                  <MetricCard icon="💥" label="SLA Breached" value={perfData.sla_compliance?.sla_breached ?? 0} sub="All-time breaches" color="#ef4444" glow={perfData.sla_compliance?.sla_breached > 0} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                  {/* Department workload */}
                  <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                    <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 16 }}>Dept Workload</div>
                    {Object.entries(perfData.department_workload || {}).slice(0, 7).map(([k, v], i) => (
                      <HBar key={k} label={k} value={v} max={Math.max(...Object.values(perfData.department_workload || { x: 1 }))} color={DEPT_COLORS[i % DEPT_COLORS.length]} />
                    ))}
                  </div>

                  {/* Top Routes */}
                  <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                    <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 16 }}>Most Problematic Routes</div>
                    {Object.entries(perfData.top_routes || {}).slice(0, 10).map(([route, count], i) => (
                      <div key={route} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #1e2d45' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ background: '#6366f120', color: '#6366f1', borderRadius: 5, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>#{i + 1}</span>
                          <span style={{ color: '#cbd5e1', fontSize: 12 }}>Route {route}</span>
                        </div>
                        <span style={{ color: '#f1f5f9', fontSize: 12, fontWeight: 700 }}>{count}</span>
                      </div>
                    ))}
                  </div>

                  {/* Top Buses */}
                  <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                    <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 16 }}>Most Complained Buses</div>
                    {Object.entries(perfData.top_buses || {}).slice(0, 10).map(([bus, count], i) => (
                      <div key={bus} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #1e2d45' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ background: '#f97316' + '20', color: '#f97316', borderRadius: 5, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>#{i + 1}</span>
                          <span style={{ color: '#cbd5e1', fontSize: 12 }}>🚌 {bus}</span>
                        </div>
                        <span style={{ color: '#f1f5f9', fontSize: 12, fontWeight: 700 }}>{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* SLA breakdown */}
                <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                  <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 16 }}>SLA Breakdown</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
                    {[
                      { label: 'Within SLA', value: perfData.sla_compliance?.within_sla, color: '#10b981' },
                      { label: 'SLA Warning', value: perfData.sla_compliance?.sla_warning, color: '#f59e0b' },
                      { label: 'SLA Breached', value: perfData.sla_compliance?.sla_breached, color: '#ef4444' },
                      { label: 'Not Tracked', value: (perfData.total_complaints - perfData.sla_compliance?.total_tracked), color: '#64748b' },
                    ].map(({ label, value, color }) => (
                      <div key={label} style={{ background: '#0f172a', borderRadius: 10, padding: '16px', textAlign: 'center', border: `1px solid ${color}20` }}>
                        <div style={{ color, fontSize: 28, fontWeight: 800 }}>{value ?? 0}</div>
                        <div style={{ color: '#94a3b8', fontSize: 11, marginTop: 4 }}>{label}</div>
                        <div style={{ background: '#1e293b', borderRadius: 4, height: 4, marginTop: 8, overflow: 'hidden' }}>
                          <div style={{ width: `${perfData.sla_compliance?.total_tracked ? (value / perfData.sla_compliance.total_tracked) * 100 : 0}%`, height: '100%', background: color, transition: 'width 0.8s' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ══ PREDICTIVE INTELLIGENCE TAB ══ */}
            {activeTab === 'predictive' && predictiveData && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                
                {/* Smart Alerts Section */}
                {predictiveData.alerts && predictiveData.alerts.length > 0 && (
                  <div style={{ background: 'linear-gradient(135deg, #2d1010 0%, #1e1e24 100%)', border: '1px solid #ef444450', borderRadius: 16, padding: 20 }}>
                    <div style={{ color: '#fca5a5', fontWeight: 700, fontSize: 14, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span>🚨 Smart Alerts</span>
                      <span style={{ background: '#ef4444', color: '#fff', borderRadius: 10, padding: '2px 8px', fontSize: 11 }}>{predictiveData.alerts.length} Active</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
                      {predictiveData.alerts.map((alert, i) => (
                        <div key={i} style={{ background: '#0f0f13', borderLeft: `4px solid ${alert.risk_level === 'Critical' ? '#ef4444' : '#f97316'}`, padding: '12px 16px', borderRadius: '4px 12px 12px 4px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                            <span style={{ color: '#cbd5e1', fontSize: 12, fontWeight: 700 }}>{alert.subject}</span>
                            <span style={{ color: alert.risk_level === 'Critical' ? '#ef4444' : '#f97316', fontSize: 10, fontWeight: 700 }}>{alert.risk_level}</span>
                          </div>
                          <p style={{ color: '#94a3b8', fontSize: 11, margin: 0, lineHeight: 1.4 }}>{alert.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Forecast & Trends Summary */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  {/* Forecast */}
                  <div style={{ background: 'linear-gradient(135deg, #1e293b 0%, #162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                      <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13 }}>Complaint Volume Forecasting</span>
                      <span style={{ background: '#10b98120', color: '#10b981', borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 600 }}>Trend: {predictiveData.forecast?.trend} ({predictiveData.forecast?.confidence} Confidence)</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 20 }}>
                      <div style={{ background: '#0f172a', padding: 12, borderRadius: 10, textAlign: 'center' }}>
                        <div style={{ color: '#64748b', fontSize: 10 }}>Next 24 Hours</div>
                        <div style={{ color: '#10b981', fontSize: 24, fontWeight: 800 }}>{predictiveData.forecast?.daily_forecast}</div>
                      </div>
                      <div style={{ background: '#0f172a', padding: 12, borderRadius: 10, textAlign: 'center' }}>
                        <div style={{ color: '#64748b', fontSize: 10 }}>Next 7 Days</div>
                        <div style={{ color: '#6366f1', fontSize: 24, fontWeight: 800 }}>{predictiveData.forecast?.weekly_forecast}</div>
                      </div>
                      <div style={{ background: '#0f172a', padding: 12, borderRadius: 10, textAlign: 'center' }}>
                        <div style={{ color: '#64748b', fontSize: 10 }}>Next 30 Days</div>
                        <div style={{ color: '#a78bfa', fontSize: 24, fontWeight: 800 }}>{predictiveData.forecast?.monthly_forecast}</div>
                      </div>
                    </div>
                    <div style={{ background: '#0f172a', padding: '16px 12px', borderRadius: 12 }}>
                      <div style={{ color: '#64748b', fontSize: 10, marginBottom: 8, textAlign: 'center' }}>14-Day Combined Projection (Solid: History, Dashed: Prediction)</div>
                      <ForecastChart history={predictiveData.forecast?.history} projection={predictiveData.forecast?.projection} />
                    </div>
                  </div>

                  {/* Emerging Issues / Trends */}
                  <div style={{ background: 'linear-gradient(135deg, #1e293b 0%, #162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                    <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, display: 'block', marginBottom: 16 }}>Emerging Issues & Trends</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 310, overflowY: 'auto' }}>
                      {predictiveData.trends?.map((trend, i) => (
                        <div key={i} style={{ background: '#0f172a', borderLeft: '3px solid #6366f1', padding: '10px 14px', borderRadius: '4px 8px 8px 4px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                            <span style={{ color: '#e2e8f0', fontSize: 11, fontWeight: 700 }}>{trend.subject}</span>
                            <span style={{ color: '#94a3b8', fontSize: 10 }}>Score: {trend.trend_score}</span>
                          </div>
                          <p style={{ color: '#94a3b8', fontSize: 11, margin: 0, lineHeight: 1.4 }}>{trend.trend_description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Risk Heatmaps / Grids */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                  {/* Route Risks */}
                  <div style={{ background: 'linear-gradient(135deg, #1e293b 0%, #162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 20 }}>
                    <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, display: 'block', marginBottom: 14 }}>High Risk Routes</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {predictiveData.route_risks?.slice(0, 5).map((route, i) => {
                        const scoreColor = SEVERITY_COLOR[route.risk_level] || '#64748b'
                        return (
                          <div key={i} style={{ background: '#0f172a', padding: 10, borderRadius: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <div style={{ color: '#f1f5f9', fontSize: 11, fontWeight: 700 }}>Route {route.route}</div>
                              <div style={{ color: '#64748b', fontSize: 10, marginTop: 2 }}>{route.complaint_count} complaints · {route.safety_count} safety</div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <span style={{ background: scoreColor + '20', color: scoreColor, border: `1px solid ${scoreColor}40`, borderRadius: 6, padding: '2px 6px', fontSize: 10, fontWeight: 700 }}>{route.risk_level} ({route.risk_score})</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Driver Risks */}
                  <div style={{ background: 'linear-gradient(135deg, #1e293b 0%, #162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 20 }}>
                    <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, display: 'block', marginBottom: 14 }}>High Risk Drivers (Bus Proxy)</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {predictiveData.driver_risks?.slice(0, 5).map((driver, i) => {
                        const scoreColor = SEVERITY_COLOR[driver.risk_level] || '#64748b'
                        return (
                          <div key={i} style={{ background: '#0f172a', padding: 10, borderRadius: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <div style={{ color: '#f1f5f9', fontSize: 11, fontWeight: 700 }}>Bus {driver.driver_identifier}</div>
                              <div style={{ color: '#64748b', fontSize: 10, marginTop: 2 }}>{driver.complaint_count} complaints · {driver.misconduct_count} misconduct</div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <span style={{ background: scoreColor + '20', color: scoreColor, border: `1px solid ${scoreColor}40`, borderRadius: 6, padding: '2px 6px', fontSize: 10, fontWeight: 700 }}>{driver.risk_level} ({driver.risk_score})</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Bus Risks */}
                  <div style={{ background: 'linear-gradient(135deg, #1e293b 0%, #162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 20 }}>
                    <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, display: 'block', marginBottom: 14 }}>High Risk Buses (Health)</span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {predictiveData.bus_risks?.slice(0, 5).map((bus, i) => {
                        const scoreColor = SEVERITY_COLOR[bus.maintenance_risk] || '#64748b'
                        return (
                          <div key={i} style={{ background: '#0f172a', padding: 10, borderRadius: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                              <div style={{ color: '#f1f5f9', fontSize: 11, fontWeight: 700 }}>Bus {bus.bus_number}</div>
                              <div style={{ color: '#64748b', fontSize: 10, marginTop: 2 }}>Maint: {bus.maintenance_count} · Overcrowding: {bus.overcrowding_count}</div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <span style={{ background: scoreColor + '20', color: scoreColor, border: `1px solid ${scoreColor}40`, borderRadius: 6, padding: '2px 6px', fontSize: 10, fontWeight: 700 }}>{bus.maintenance_risk}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>

                {/* Preventive Recommendations Section */}
                <div style={{ background: 'linear-gradient(135deg, #1e293b 0%, #162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                  <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, display: 'block', marginBottom: 16 }}>Preventive Recommendations</span>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    {predictiveData.recommendations?.map((rec, i) => {
                      const badgeColor = SEVERITY_COLOR[rec.priority] || '#64748b'
                      return (
                        <div key={i} style={{ background: '#0f172a', border: '1px solid #1e2d45', padding: 14, borderRadius: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: '#a78bfa', fontSize: 11, fontWeight: 700 }}>{rec.subject}</span>
                            <span style={{ background: badgeColor + '20', color: badgeColor, border: `1px solid ${badgeColor}40`, borderRadius: 6, padding: '1px 6px', fontSize: 10, fontWeight: 700 }}>{rec.priority} Priority</span>
                          </div>
                          <p style={{ color: '#e2e8f0', fontSize: 12, margin: 0, lineHeight: 1.5 }}>{rec.recommendation}</p>
                        </div>
                      )
                    })}
                  </div>
                </div>

              </div>
            )}

            {/* ══ EXECUTIVE INTELLIGENCE TAB ══ */}
            {activeTab === 'executive' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

                {/* Row 1: Health Index + Report Downloads */}
                <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 16 }}>
                  {/* Health Index */}
                  <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#0f1a30 100%)', border: '1px solid #6366f130', borderRadius: 20, padding: 28, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, position: 'relative', overflow: 'hidden' }}>
                    <div style={{ position: 'absolute', top: -30, right: -30, width: 120, height: 120, borderRadius: '50%', background: '#6366f110' }} />
                    <div style={{ fontSize: 12, color: '#6366f1', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase' }}>Transport Health Index</div>
                    {executiveData ? (
                      <>
                        <div style={{
                          width: 120, height: 120, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column',
                          border: `6px solid ${executiveData.health.transport_health_score >= 70 ? '#10b981' : executiveData.health.transport_health_score >= 50 ? '#f59e0b' : '#ef4444'}`,
                          boxShadow: `0 0 30px ${executiveData.health.transport_health_score >= 70 ? '#10b98140' : executiveData.health.transport_health_score >= 50 ? '#f59e0b40' : '#ef444440'}`,
                        }}>
                          <div style={{ fontSize: 36, fontWeight: 900, color: executiveData.health.transport_health_score >= 70 ? '#10b981' : executiveData.health.transport_health_score >= 50 ? '#f59e0b' : '#ef4444' }}>{executiveData.health.transport_health_score}</div>
                          <div style={{ fontSize: 10, color: '#64748b' }}>out of 100</div>
                        </div>
                        <div style={{ fontSize: 18, fontWeight: 800, color: '#f1f5f9' }}>{executiveData.health.rating}</div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, width: '100%', marginTop: 4 }}>
                          {Object.entries(executiveData.health.metrics || {}).map(([k, v]) => (
                            <div key={k} style={{ background: '#0f172a', borderRadius: 8, padding: '8px 10px' }}>
                              <div style={{ color: '#475569', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{k.replace(/_/g, ' ')}</div>
                              <div style={{ color: '#f1f5f9', fontSize: 14, fontWeight: 700 }}>{typeof v === 'number' ? Math.round(v) : v}</div>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : <div style={{ color: '#475569', fontSize: 13 }}>Loading health index…</div>}
                  </div>

                  {/* Reports + Governance summary */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    {/* Report Downloads */}
                    <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 20 }}>
                      <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Management Report Downloads</div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
                        {['daily', 'weekly', 'monthly'].map(period => (
                          <div key={period} style={{ background: '#0f172a', borderRadius: 10, padding: 14, textAlign: 'center' }}>
                            <div style={{ color: '#94a3b8', fontSize: 11, marginBottom: 10, fontWeight: 600, textTransform: 'capitalize' }}>{period} Report</div>
                            <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                              {[['pdf', '#ef4444', '📄'], ['docx', '#3b82f6', '📝']].map(([fmt, color, icon]) => {
                                const key = `${period}-${fmt}`
                                const busy = reportDownloading[key]
                                return (
                                  <button
                                    key={fmt}
                                    disabled={busy}
                                    onClick={async () => {
                                      setReportDownloading(s => ({ ...s, [key]: true }))
                                      try {
                                        await downloadReport(period, fmt)
                                      } catch (err) {
                                        alert(`Download failed: ${err.message}`)
                                      } finally {
                                        setReportDownloading(s => ({ ...s, [key]: false }))
                                      }
                                    }}
                                    style={{
                                      background: busy ? '#334155' : color,
                                      color: '#fff', border: 'none', borderRadius: 6,
                                      padding: '5px 12px', fontSize: 11, fontWeight: 700,
                                      cursor: busy ? 'not-allowed' : 'pointer',
                                      opacity: busy ? 0.7 : 1,
                                      transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: 4,
                                    }}
                                  >
                                    {busy ? <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⏳</span> : icon}
                                    {busy ? '…' : fmt.toUpperCase()}
                                  </button>
                                )
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Governance Recommendations Preview */}
                    <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 20, flex: 1 }}>
                      <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 12 }}>Strategic Governance Recommendations</div>
                      {executiveData ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 180, overflowY: 'auto' }}>
                          {executiveData.governance.map((rec, i) => {
                            const clr = rec.priority === 'Critical' ? '#ef4444' : rec.priority === 'High' ? '#f97316' : rec.priority === 'Medium' ? '#f59e0b' : '#10b981'
                            return (
                              <div key={i} style={{ background: '#0f172a', borderLeft: `3px solid ${clr}`, padding: '10px 14px', borderRadius: '4px 8px 8px 4px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                                  <span style={{ color: '#e2e8f0', fontSize: 11, fontWeight: 700 }}>{rec.title}</span>
                                  <span style={{ color: clr, fontSize: 10, fontWeight: 700 }}>{rec.priority}</span>
                                </div>
                                <p style={{ color: '#94a3b8', fontSize: 10, margin: 0, lineHeight: 1.4 }}>{rec.description}</p>
                              </div>
                            )
                          })}
                        </div>
                      ) : <div style={{ color: '#475569', fontSize: 12 }}>Loading recommendations…</div>}
                    </div>
                  </div>
                </div>

                {/* Row 2: AI Copilot */}
                <div style={{ background: 'linear-gradient(135deg,#0f1f3d 0%,#0f172a 100%)', border: '1px solid #6366f140', borderRadius: 20, padding: 24 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg,#6366f1,#a855f7)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, boxShadow: '0 0 16px #6366f140' }}>🤖</div>
                    <div>
                      <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 14 }}>Executive AI Copilot</div>
                      <div style={{ color: '#6366f1', fontSize: 10 }}>Ask any question about transport operations</div>
                    </div>
                  </div>

                  {/* Sample prompts */}
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
                    {[
                      'Which routes have the highest complaints?',
                      'Show all critical safety complaints',
                      'Which drivers have high risk scores?',
                      'What are the top delay reasons?',
                    ].map(prompt => (
                      <button key={prompt} onClick={() => setCopilotQ(prompt)}
                        style={{ background: '#6366f115', border: '1px solid #6366f130', color: '#a5b4fc', borderRadius: 8, padding: '5px 12px', fontSize: 11, cursor: 'pointer', transition: 'all 0.2s' }}
                        onMouseEnter={e => { e.currentTarget.style.background = '#6366f130'; e.currentTarget.style.borderColor = '#6366f160' }}
                        onMouseLeave={e => { e.currentTarget.style.background = '#6366f115'; e.currentTarget.style.borderColor = '#6366f130' }}>
                        {prompt}
                      </button>
                    ))}
                  </div>

                  {/* Input */}
                  <div style={{ display: 'flex', gap: 10 }}>
                    <input
                      value={copilotQ}
                      onChange={e => setCopilotQ(e.target.value)}
                      onKeyDown={async e => {
                        if (e.key === 'Enter' && copilotQ.trim() && !copilotLoading) {
                          setCopilotLoading(true); setCopilotResult(null); setCopilotError(null)
                          try {
                            const r = await queryCopilot(copilotQ)
                            setCopilotResult(r)
                          } catch (err) {
                            if (err.response?.status === 401) {
                              setCopilotError('Please login to use Executive AI Copilot.')
                            } else {
                              setCopilotError(err.response?.data?.detail || err.message || 'Unable to process query.')
                            }
                          } finally {
                            setCopilotLoading(false)
                          }
                        }
                      }}
                      placeholder="Ask about routes, drivers, complaints, trends…"
                      style={{ flex: 1, background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, padding: '10px 16px', color: '#f1f5f9', fontSize: 13, outline: 'none' }}
                    />
                    <button
                      disabled={!copilotQ.trim() || copilotLoading}
                      onClick={async () => {
                        if (!copilotQ.trim() || copilotLoading) return
                        setCopilotLoading(true); setCopilotResult(null); setCopilotError(null)
                        try {
                          const r = await queryCopilot(copilotQ)
                          setCopilotResult(r)
                        } catch (err) {
                          if (err.response?.status === 401) {
                            setCopilotError('Please login to use Executive AI Copilot.')
                          } else {
                            setCopilotError(err.response?.data?.detail || err.message || 'Unable to process query.')
                          }
                        } finally {
                          setCopilotLoading(false)
                        }
                      }}
                      style={{ background: copilotLoading ? '#334155' : 'linear-gradient(135deg,#6366f1,#a855f7)', color: '#fff', border: 'none', borderRadius: 10, padding: '10px 20px', fontSize: 13, fontWeight: 700, cursor: copilotLoading ? 'not-allowed' : 'pointer', minWidth: 90, transition: 'all 0.2s' }}>
                      {copilotLoading ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⚙️</span> Processing…
                        </span>
                      ) : '✦ Ask'}
                    </button>
                  </div>

                  {/* Error display */}
                  {copilotError && (
                    <div style={{ marginTop: 14, background: '#2d1515', border: '1px solid #ef4444', borderRadius: 10, padding: '12px 16px', color: '#fca5a5', fontSize: 13 }}>
                      ⚠️ {copilotError}
                    </div>
                  )}

                  {/* Result */}
                  {copilotResult && (
                    <div style={{ marginTop: 16, background: '#0f172a', borderRadius: 12, border: '1px solid #1e2d45', padding: 18 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ color: '#6366f1', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em' }}>AI Response</div>
                        {copilotResult.source && (
                          <span style={{
                            background: copilotResult.source === 'openai' ? '#10b98120' : copilotResult.source === 'gemini' ? '#3b82f620' : '#6366f120',
                            color: copilotResult.source === 'openai' ? '#10b981' : copilotResult.source === 'gemini' ? '#60a5fa' : '#a78bfa',
                            border: `1px solid ${copilotResult.source === 'openai' ? '#10b98140' : copilotResult.source === 'gemini' ? '#3b82f640' : '#6366f140'}`,
                            borderRadius: 6, padding: '2px 10px', fontSize: 10, fontWeight: 700,
                          }}>
                            {copilotResult.source === 'openai' ? '⚡ OpenAI' : copilotResult.source === 'gemini' ? '✦ Gemini' : '🧠 Local Intelligence Engine'}
                          </span>
                        )}
                      </div>
                      <p style={{ color: '#f1f5f9', fontSize: 13, lineHeight: 1.7, margin: 0 }}>{copilotResult.answer}</p>
                      {copilotResult.supporting_data && Object.keys(copilotResult.supporting_data).length > 0 && (
                        <details style={{ marginTop: 12 }}>
                          <summary style={{ color: '#6366f1', fontSize: 11, cursor: 'pointer', fontWeight: 600 }}>View supporting data</summary>
                          <pre style={{ marginTop: 8, color: '#64748b', fontSize: 10, lineHeight: 1.5, overflow: 'auto', maxHeight: 180, background: '#0a0f1e', padding: 12, borderRadius: 8 }}>
                            {JSON.stringify(copilotResult.supporting_data, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>

                {/* Row 3: Geographic Complaint Heatmap */}
                {executiveData && (
                  <div style={{ background: 'linear-gradient(135deg,#1e293b 0%,#162032 100%)', border: '1px solid #1e2d45', borderRadius: 16, padding: 22 }}>
                    <div style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 13, marginBottom: 4 }}>Geographic Complaint Heatmap</div>
                    <div style={{ color: '#475569', fontSize: 11, marginBottom: 16 }}>Complaint density by reported incident location</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, maxHeight: 320, overflowY: 'auto' }}>
                      {executiveData.heatmap.locations?.slice(0, 20).map((loc, i) => {
                        const maxCount = executiveData.heatmap.locations[0]?.complaint_count || 1
                        const pct = Math.round(loc.complaint_count / maxCount * 100)
                        const heatColor = pct >= 80 ? '#ef4444' : pct >= 60 ? '#f97316' : pct >= 40 ? '#f59e0b' : '#10b981'
                        return (
                          <div key={i} style={{ background: '#0f172a', padding: '10px 14px', borderRadius: 10, border: `1px solid ${heatColor}20` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                              <span style={{ color: '#e2e8f0', fontSize: 11, fontWeight: 600, maxWidth: '75%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>📍 {loc.location}</span>
                              <span style={{ color: heatColor, fontSize: 11, fontWeight: 700 }}>{loc.complaint_count}</span>
                            </div>
                            <div style={{ background: '#1e293b', borderRadius: 4, height: 5, marginBottom: 6 }}>
                              <div style={{ width: `${pct}%`, height: '100%', background: heatColor, borderRadius: 4, transition: 'width 0.8s' }} />
                            </div>
                            <div style={{ display: 'flex', gap: 10 }}>
                              {loc.safety_count > 0 && <span style={{ color: '#ef4444', fontSize: 9 }}>⚠️ {loc.safety_count} Safety</span>}
                              {loc.delay_count > 0 && <span style={{ color: '#f59e0b', fontSize: 9 }}>⏱ {loc.delay_count} Delay</span>}
                              {loc.maintenance_count > 0 && <span style={{ color: '#6366f1', fontSize: 9 }}>🔧 {loc.maintenance_count} Maint</span>}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

