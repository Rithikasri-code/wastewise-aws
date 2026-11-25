// Shows that demo mode loaded the fake account from the editable seed file.
// All labels are passed in as already-formatted strings from the language bundle.
export default function DemoStatus({ enabled, account, sourceFile, text }) {
  if (!enabled || !account) {
    return (
      <p className="text-sm text-slate-500">
        Demo mode is off. Switch to Demo on the Connect screen to try it without an AWS account.
      </p>
    )
  }
  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-slate-900">{text.loadedTitle}</p>
      <p className="text-sm text-slate-600">{text.resources}</p>
      <p className="text-xs text-slate-400">{text.source}</p>
    </div>
  )
}
