import { CheckCircle, Copy, X } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'

export default function SuccessModal({ complaintId, onClose }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(complaintId)
    setCopied(true)
    toast.success('Complaint ID copied!')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)' }}>
      <div className="glass-card gradient-border w-full max-w-md p-8 slide-up text-center relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-500 hover:text-slate-300 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Success Icon */}
        <div className="relative mx-auto w-20 h-20 mb-6">
          <div className="w-20 h-20 rounded-full bg-emerald-500/15 border-2 border-emerald-500/30 flex items-center justify-center">
            <CheckCircle className="w-10 h-10 text-emerald-400" />
          </div>
          <div className="absolute inset-0 rounded-full border-2 border-emerald-400/20 animate-ping" />
        </div>

        <h2 className="text-2xl font-700 text-slate-100 mb-2">Complaint Registered!</h2>
        <p className="text-slate-400 text-sm mb-6">
          Your complaint has been registered successfully. We will review it and get back to you shortly.
        </p>

        {/* Complaint ID */}
        <div className="bg-slate-900/70 border border-indigo-500/20 rounded-12 p-4 mb-6">
          <p className="text-xs text-slate-500 mb-2 uppercase tracking-wider font-500">Your Complaint ID</p>
          <div className="flex items-center justify-center gap-3">
            <span className="text-2xl font-700 gradient-text tracking-wider">{complaintId}</span>
            <button
              onClick={handleCopy}
              className="text-slate-400 hover:text-indigo-400 transition-colors p-1"
              title="Copy ID"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
          {copied && (
            <p className="text-xs text-emerald-400 mt-1 fade-in">Copied to clipboard!</p>
          )}
        </div>

        <p className="text-xs text-slate-500 mb-6">
          Please save your complaint ID for future reference and tracking.
        </p>

        <button onClick={onClose} className="btn-primary w-full">
          Submit Another Complaint
        </button>
      </div>
    </div>
  )
}
