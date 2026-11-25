// Product wordmark: a simple text logo plus a small leak/droplet icon.
// No borrowed artwork. Name and tagline arrive as props (from the backend
// language file) so they are never typed into this component.
export default function Brand({ name, tagline, subtitle }) {
  return (
    <div className="flex items-start gap-3">
      <span
        aria-hidden="true"
        className="mt-1 inline-flex h-9 w-9 items-center justify-center rounded-full bg-sky-100 text-sky-600"
      >
        {/* droplet-with-leak mark */}
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 3c3.5 4.2 6 7.3 6 10.2A6 6 0 0 1 6 13.2C6 10.3 8.5 7.2 12 3Z"
            fill="currentColor"
            opacity="0.9"
          />
          <path d="M12 12v5" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" />
          <circle cx="12" cy="19" r="1.4" fill="#fff" />
        </svg>
      </span>
      <div>
        <div className="text-xl font-semibold tracking-tight text-slate-900">{name}</div>
        {tagline && <div className="text-sm text-slate-500">{tagline}</div>}
        {subtitle && <div className="text-xs text-slate-400">{subtitle}</div>}
      </div>
    </div>
  )
}
