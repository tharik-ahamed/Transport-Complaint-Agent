import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import ComplaintForm from './pages/ComplaintForm'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <div className="min-h-screen" style={{ background: 'radial-gradient(ellipse at top, #0d1433 0%, #0a0f1e 60%, #060a14 100%)' }}>
      {/* Ambient background effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, #6366f1, transparent)' }} />
        <div className="absolute top-1/2 -right-40 w-80 h-80 rounded-full opacity-8"
          style={{ background: 'radial-gradient(circle, #8b5cf6, transparent)' }} />
        <div className="absolute -bottom-20 left-1/3 w-72 h-72 rounded-full opacity-6"
          style={{ background: 'radial-gradient(circle, #4f46e5, transparent)' }} />
      </div>

      <div className="relative z-10">
        <Navbar />
        <main>
          <Routes>
            <Route path="/" element={<ComplaintForm />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
