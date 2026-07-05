import { Link, useLocation } from 'react-router-dom'
import { Bus, LayoutDashboard, FileText, ChevronRight } from 'lucide-react'

export default function Navbar() {
  const location = useLocation()

  const links = [
    { to: '/', label: 'Submit Complaint', icon: FileText },
    { to: '/dashboard', label: 'Admin Dashboard', icon: LayoutDashboard },
  ]

  return (
    <nav className="sticky top-0 z-50 border-b border-[#1e293b]/80 backdrop-blur-xl"
      style={{ background: 'rgba(10, 15, 30, 0.95)' }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30 group-hover:shadow-indigo-500/50 transition-all duration-300">
                <Bus className="w-5 h-5 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#0a0f1e]">
                <span className="pulse-dot w-full h-full rounded-full block"></span>
              </div>
            </div>
            <div>
              <span className="text-base font-700 gradient-text">Transport</span>
              <span className="text-base font-700 text-slate-200"> Complaint</span>
              <div className="text-[10px] text-slate-500 font-400 -mt-0.5 tracking-wider">AI Multi-Agent System</div>
            </div>
          </Link>

          {/* Nav Links */}
          <div className="flex items-center gap-1">
            {links.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={`nav-link flex items-center gap-2 ${location.pathname === to ? 'active' : ''}`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  )
}
