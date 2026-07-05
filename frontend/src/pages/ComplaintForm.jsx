import { useState, useRef } from 'react'
import {
  User, Phone, Mail, Bus, Route, Tag, FileText, MapPin, Calendar,
  Mic, Image, Upload, X, ChevronDown, AlertCircle, Loader2, Send,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { submitComplaint } from '../api/complaintsApi'
import SuccessModal from '../components/SuccessModal'

const CATEGORIES = [
  'Bus Delay', 'Driver Misconduct', 'Conductor Misconduct', 'Stop Skipping',
  'Overcrowding', 'Maintenance Issue', 'Ticket Issue', 'Safety Issue',
  'Cleanliness Issue', 'Other',
]

const INITIAL_FORM = {
  passenger_name: '',
  mobile_number: '',
  email: '',
  bus_number: '',
  route_number: '',
  category: '',
  complaint_description: '',
  incident_location: '',
  incident_datetime: '',
}

function FormField({ label, icon: Icon, error, required, children }) {
  return (
    <div>
      <label className="form-label flex items-center gap-1.5">
        {Icon && <Icon className="w-3.5 h-3.5 text-indigo-400" />}
        {label}
        {required && <span className="text-indigo-400">*</span>}
      </label>
      {children}
      {error && (
        <p className="mt-1.5 flex items-center gap-1 text-xs text-red-400 fade-in">
          <AlertCircle className="w-3 h-3 flex-shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}

export default function ComplaintForm() {
  const [form, setForm] = useState(INITIAL_FORM)
  const [errors, setErrors] = useState({})
  const [voiceFile, setVoiceFile] = useState(null)
  const [imageFile, setImageFile] = useState(null)
  const [voiceDragging, setVoiceDragging] = useState(false)
  const [imageDragging, setImageDragging] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [successData, setSuccessData] = useState(null)

  const voiceInputRef = useRef(null)
  const imageInputRef = useRef(null)

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const newErrors = {}
    if (!form.passenger_name.trim() || form.passenger_name.trim().length < 2)
      newErrors.passenger_name = 'Name must be at least 2 characters'
    if (!/^\+?[0-9]{7,15}$/.test(form.mobile_number.trim()))
      newErrors.mobile_number = 'Enter a valid mobile number'
    if (!/^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(form.email.trim()))
      newErrors.email = 'Enter a valid email address'
    if (!form.bus_number.trim()) newErrors.bus_number = 'Bus number is required'
    if (!form.route_number.trim()) newErrors.route_number = 'Route number is required'
    if (!form.category) newErrors.category = 'Please select a category'
    if (!form.complaint_description.trim() || form.complaint_description.trim().length < 10)
      newErrors.complaint_description = 'Description must be at least 10 characters'
    if (!form.incident_location.trim()) newErrors.incident_location = 'Location is required'
    if (!form.incident_datetime) newErrors.incident_datetime = 'Date and time is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) {
      toast.error('Please fix the errors before submitting')
      return
    }
    setSubmitting(true)
    try {
      const fd = new FormData()
      Object.entries(form).forEach(([k, v]) => fd.append(k, v))
      if (voiceFile) fd.append('voice_file', voiceFile)
      if (imageFile) fd.append('image_file', imageFile)

      const result = await submitComplaint(fd)
      setSuccessData(result)
      setForm(INITIAL_FORM)
      setVoiceFile(null)
      setImageFile(null)
    } catch (err) {
      const detail = err?.response?.data?.detail
      if (Array.isArray(detail)) {
        toast.error(detail[0])
      } else if (typeof detail === 'string') {
        toast.error(detail)
      } else {
        toast.error('Failed to submit complaint. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleFileDrop = (e, type) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (!file) return
    if (type === 'voice') {
      setVoiceDragging(false)
      setVoiceFile(file)
    } else {
      setImageDragging(false)
      setImageFile(file)
    }
  }

  return (
    <>
      {successData && (
        <SuccessModal
          complaintId={successData.complaint_id}
          onClose={() => setSuccessData(null)}
        />
      )}

      <div className="min-h-screen py-10 px-4">
        {/* Hero Header */}
        <div className="max-w-4xl mx-auto mb-10 text-center fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-500 text-indigo-300 mb-5"
            style={{ background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)' }}>
            <span className="pulse-dot w-2 h-2 rounded-full bg-indigo-400"></span>
            Phase 1 — Complaint Collection System
          </div>
          <h1 className="text-4xl sm:text-5xl font-800 mb-4">
            <span className="text-slate-100">Submit a </span>
            <span className="gradient-text">Transport Complaint</span>
          </h1>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            Report issues with bus services quickly and easily. Your feedback helps us improve public transport.
          </p>
        </div>

        {/* Form Card */}
        <div className="max-w-4xl mx-auto">
          <div className="glass-card gradient-border p-8 slide-up">
            <form onSubmit={handleSubmit} noValidate>
              {/* Section: Passenger Info */}
              <SectionHeader icon={User} title="Passenger Information" step="01" />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-8">
                <FormField label="Full Name" icon={User} error={errors.passenger_name} required>
                  <input
                    type="text"
                    name="passenger_name"
                    value={form.passenger_name}
                    onChange={handleChange}
                    placeholder="e.g. John Smith"
                    className={`form-input ${errors.passenger_name ? 'error' : ''}`}
                    id="passenger_name"
                  />
                </FormField>

                <FormField label="Mobile Number" icon={Phone} error={errors.mobile_number} required>
                  <input
                    type="tel"
                    name="mobile_number"
                    value={form.mobile_number}
                    onChange={handleChange}
                    placeholder="e.g. +94771234567"
                    className={`form-input ${errors.mobile_number ? 'error' : ''}`}
                    id="mobile_number"
                  />
                </FormField>

                <FormField label="Email Address" icon={Mail} error={errors.email} required>
                  <input
                    type="email"
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    placeholder="e.g. john@example.com"
                    className={`form-input ${errors.email ? 'error' : ''}`}
                    id="email"
                  />
                </FormField>
              </div>

              {/* Section: Bus Details */}
              <SectionHeader icon={Bus} title="Bus & Route Details" step="02" />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-8">
                <FormField label="Bus Number" icon={Bus} error={errors.bus_number} required>
                  <input
                    type="text"
                    name="bus_number"
                    value={form.bus_number}
                    onChange={handleChange}
                    placeholder="e.g. NB-1234"
                    className={`form-input ${errors.bus_number ? 'error' : ''}`}
                    id="bus_number"
                  />
                </FormField>

                <FormField label="Route Number" icon={Route} error={errors.route_number} required>
                  <input
                    type="text"
                    name="route_number"
                    value={form.route_number}
                    onChange={handleChange}
                    placeholder="e.g. Route 120"
                    className={`form-input ${errors.route_number ? 'error' : ''}`}
                    id="route_number"
                  />
                </FormField>
              </div>

              {/* Section: Complaint Details */}
              <SectionHeader icon={FileText} title="Complaint Details" step="03" />
              <div className="grid grid-cols-1 gap-5 mb-8">
                <FormField label="Complaint Category" icon={Tag} error={errors.category} required>
                  <div className="relative">
                    <select
                      name="category"
                      value={form.category}
                      onChange={handleChange}
                      className={`form-input appearance-none pr-10 ${errors.category ? 'error' : ''}`}
                      id="category"
                    >
                      <option value="" disabled>Select a category...</option>
                      {CATEGORIES.map(cat => (
                        <option key={cat} value={cat} style={{ background: '#0f172a' }}>{cat}</option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                  </div>
                </FormField>

                <FormField label="Complaint Description" icon={FileText} error={errors.complaint_description} required>
                  <textarea
                    name="complaint_description"
                    value={form.complaint_description}
                    onChange={handleChange}
                    rows={4}
                    placeholder="Please describe the incident in detail..."
                    className={`form-input resize-none ${errors.complaint_description ? 'error' : ''}`}
                    id="complaint_description"
                  />
                  <p className="text-xs text-slate-600 mt-1 text-right">
                    {form.complaint_description.length} chars (min. 10)
                  </p>
                </FormField>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <FormField label="Incident Location" icon={MapPin} error={errors.incident_location} required>
                    <input
                      type="text"
                      name="incident_location"
                      value={form.incident_location}
                      onChange={handleChange}
                      placeholder="e.g. Main St Bus Stop"
                      className={`form-input ${errors.incident_location ? 'error' : ''}`}
                      id="incident_location"
                    />
                  </FormField>

                  <FormField label="Date & Time of Incident" icon={Calendar} error={errors.incident_datetime} required>
                    <input
                      type="datetime-local"
                      name="incident_datetime"
                      value={form.incident_datetime}
                      onChange={handleChange}
                      className={`form-input ${errors.incident_datetime ? 'error' : ''}`}
                      id="incident_datetime"
                      style={{ colorScheme: 'dark' }}
                    />
                  </FormField>
                </div>
              </div>

              {/* Section: Evidence Upload */}
              <SectionHeader icon={Upload} title="Supporting Evidence" step="04" optional />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-8">
                {/* Voice Upload */}
                <div>
                  <label className="form-label flex items-center gap-1.5">
                    <Mic className="w-3.5 h-3.5 text-indigo-400" />
                    Voice Complaint
                    <span className="text-slate-600 text-xs">(optional)</span>
                  </label>
                  <div
                    className={`upload-zone ${voiceDragging ? 'active' : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setVoiceDragging(true) }}
                    onDragLeave={() => setVoiceDragging(false)}
                    onDrop={(e) => handleFileDrop(e, 'voice')}
                    onClick={() => voiceInputRef.current?.click()}
                    id="voice_upload_zone"
                  >
                    <input
                      ref={voiceInputRef}
                      type="file"
                      accept="audio/*"
                      className="hidden"
                      onChange={(e) => setVoiceFile(e.target.files[0])}
                      id="voice_file_input"
                    />
                    {voiceFile ? (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Mic className="w-4 h-4 text-indigo-400" />
                          <span className="text-sm text-slate-300 truncate max-w-32">{voiceFile.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); setVoiceFile(null) }}
                          className="text-slate-500 hover:text-red-400 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div>
                        <Mic className="w-7 h-7 text-indigo-400/60 mx-auto mb-2" />
                        <p className="text-xs text-slate-500">
                          Drag & drop audio or <span className="text-indigo-400">browse</span>
                        </p>
                        <p className="text-xs text-slate-600 mt-1">MP3, WAV, M4A</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Image Upload */}
                <div>
                  <label className="form-label flex items-center gap-1.5">
                    <Image className="w-3.5 h-3.5 text-indigo-400" />
                    Photo Evidence
                    <span className="text-slate-600 text-xs">(optional)</span>
                  </label>
                  <div
                    className={`upload-zone ${imageDragging ? 'active' : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setImageDragging(true) }}
                    onDragLeave={() => setImageDragging(false)}
                    onDrop={(e) => handleFileDrop(e, 'image')}
                    onClick={() => imageInputRef.current?.click()}
                    id="image_upload_zone"
                  >
                    <input
                      ref={imageInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => setImageFile(e.target.files[0])}
                      id="image_file_input"
                    />
                    {imageFile ? (
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Image className="w-4 h-4 text-indigo-400" />
                          <span className="text-sm text-slate-300 truncate max-w-32">{imageFile.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); setImageFile(null) }}
                          className="text-slate-500 hover:text-red-400 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div>
                        <Image className="w-7 h-7 text-indigo-400/60 mx-auto mb-2" />
                        <p className="text-xs text-slate-500">
                          Drag & drop image or <span className="text-indigo-400">browse</span>
                        </p>
                        <p className="text-xs text-slate-600 mt-1">JPG, PNG, WEBP</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-2 border-t border-slate-800">
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary w-full flex items-center justify-center gap-2 text-base"
                  id="submit_complaint_btn"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Submitting Complaint...
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      Submit Complaint
                    </>
                  )}
                </button>
                <p className="text-center text-xs text-slate-600 mt-3">
                  Fields marked with <span className="text-indigo-400">*</span> are required
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  )
}

function SectionHeader({ icon: Icon, title, step, optional }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className="flex items-center justify-center w-8 h-8 rounded-lg text-xs font-700 text-indigo-300"
        style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.25)' }}>
        {step}
      </div>
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-indigo-400" />
        <h2 className="text-sm font-600 text-slate-300 uppercase tracking-wider">{title}</h2>
        {optional && <span className="text-xs text-slate-600">(optional)</span>}
      </div>
      <div className="flex-1 h-px bg-gradient-to-r from-indigo-500/20 to-transparent" />
    </div>
  )
}
