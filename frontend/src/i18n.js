// Tiny i18n helper. All display text comes from the backend language bundle;
// components call these helpers instead of embedding strings.

/** Look up a nested key like "home.title" in a bundle. */
export function lookup(bundle, path) {
  return path.split('.').reduce((acc, key) => (acc == null ? acc : acc[key]), bundle)
}

/** Replace {placeholders} in a template with values. */
export function format(template, vars = {}) {
  if (typeof template !== 'string') return template
  return template.replace(/\{(\w+)\}/g, (_, key) => (key in vars ? String(vars[key]) : `{${key}}`))
}

/** Resolve and interpolate a language key. Returns the key if missing. */
export function t(bundle, path, vars) {
  const raw = lookup(bundle, path)
  return raw == null ? path : format(raw, vars)
}
