import { useEffect, useMemo, useState } from 'react'
import { getBranding, getLanguage, getDemoAccount, quotePrice } from './api.js'
import { t } from './i18n.js'
import Brand from './components/Brand.jsx'
import DemoStatus from './components/DemoStatus.jsx'

export default function App() {
  const [branding, setBranding] = useState(null)
  const [language, setLanguage] = useState(null)
  const [demo, setDemo] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [price, setPrice] = useState({ status: 'idle', data: null, error: null })

  useEffect(() => {
    let active = true
    Promise.all([getBranding(), getLanguage(), getDemoAccount()])
      .then(([b, lang, d]) => {
        if (!active) return
        setBranding(b)
        setLanguage(lang)
        setDemo(d)
        // Browser tab title comes from branding, never a hardcoded string.
        if (b?.name) document.title = b.name
      })
      .catch((err) => active && setLoadError(String(err)))
    return () => {
      active = false
    }
  }, [])

  // Prove the pricing pipeline works in demo mode: quote the first demo EC2
  // instance type through the same live+cache+fallback path used in real mode.
  const demoInstance = demo?.account?.ec2_instances?.[0]
  useEffect(() => {
    if (!demoInstance) return
    let active = true
    setPrice({ status: 'loading', data: null, error: null })
    quotePrice({
      service: 'AmazonEC2',
      region: demoInstance.region,
      filters: {
        instanceType: demoInstance.instance_type,
        operatingSystem: 'Linux',
        tenancy: 'Shared',
      },
      unit: 'Hrs',
    })
      .then((res) => {
        if (!active) return
        if (res.error) setPrice({ status: 'error', data: null, error: res.error })
        else setPrice({ status: 'ok', data: res, error: null })
      })
      .catch((err) => active && setPrice({ status: 'error', data: null, error: String(err) }))
    return () => {
      active = false
    }
  }, [demoInstance?.instance_id])

  const demoText = useMemo(() => {
    if (!language) return null
    return {
      loadedTitle: t(language, 'demo.loaded_title'),
      resources: t(language, 'demo.resources_count', { count: demo?.account?.resource_count ?? 0 }),
      source: t(language, 'demo.source', { path: demo?.source_file ?? '' }),
    }
  }, [language, demo])

  const fullName = branding?.full_name || language?.branding?.full_name || ''

  if (loadError) {
    return (
      <Shell title={fullName}>
        <p className="text-sm text-red-600">
          {t(language || {}, 'errors.backend_unreachable', { name: fullName, detail: loadError })}
        </p>
      </Shell>
    )
  }
  if (!branding || !language) {
    return <Shell title={fullName}>{t(language || {}, 'common.loading')}</Shell>
  }

  return (
    <Shell title={fullName}>
      <Brand name={branding.name} tagline={branding.tagline} subtitle={branding.subtitle} />

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <Card title={t(language, 'connect.demo_mode')}>
          <DemoStatus
            enabled={demo?.enabled}
            account={demo?.account}
            sourceFile={demo?.source_file}
            text={demoText}
          />
        </Card>

        <Card
          title={t(language, 'pricing.last_updated', {
            date: price.data ? new Date(price.data.fetched_at).toLocaleDateString() : '—',
          })}
        >
          <PricingPanel language={language} price={price} demoInstance={demoInstance} />
        </Card>
      </div>
    </Shell>
  )
}

function PricingPanel({ language, price, demoInstance }) {
  if (price.status === 'loading' || price.status === 'idle') {
    return <p className="text-sm text-slate-500">{t(language, 'common.loading')}</p>
  }
  if (price.status === 'error') {
    return (
      <p className="text-sm text-amber-700">
        {t(language, 'pricing.unavailable', { reason: price.error })}
      </p>
    )
  }
  const q = price.data
  return (
    <div className="text-sm text-slate-700">
      <p>
        {t(language, 'pricing.row', {
          type: demoInstance.instance_type,
          region: demoInstance.region,
          currency: q.currency,
          price: q.price.toFixed(4),
          unit: q.unit,
        })}
      </p>
      <p className="mt-1 text-xs text-slate-400">
        {t(language, 'pricing.source_note', { source: t(language, `pricing.${q.source}`) })}
      </p>
    </div>
  )
}

function Shell({ title, children }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-4xl px-6 py-4 text-sm font-medium text-slate-400">
          {title}
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-6 py-10">{children}</main>
    </div>
  )
}

function Card({ title, children }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</h2>
      {children}
    </section>
  )
}
