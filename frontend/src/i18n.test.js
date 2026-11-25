import { describe, it, expect } from 'vitest'
import { format, lookup, t } from './i18n.js'

// Basic frontend test setup (vitest): proves the text/formatting layer that all
// screens depend on, without needing a browser.
describe('i18n helpers', () => {
  const bundle = {
    branding: { name: 'SampleBrand' },
    demo: { resources_count: '{count} resources in the sample account' },
  }

  it('looks up nested keys', () => {
    expect(lookup(bundle, 'branding.name')).toBe('SampleBrand')
  })

  it('formats placeholders', () => {
    expect(format(bundle.demo.resources_count, { count: 12 })).toBe(
      '12 resources in the sample account',
    )
  })

  it('resolves and interpolates together', () => {
    expect(t(bundle, 'demo.resources_count', { count: 3 })).toBe(
      '3 resources in the sample account',
    )
  })

  it('returns the key when missing instead of crashing', () => {
    expect(t(bundle, 'nope.missing')).toBe('nope.missing')
  })
})
