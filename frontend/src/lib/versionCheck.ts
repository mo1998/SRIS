let currentEntry: string | null = null

function readCurrentEntry(): string | null {
  const scripts = Array.from(document.querySelectorAll('script[src]'))
  const src = scripts
    .map((s) => s.getAttribute('src') || '')
    .find((s) => /index-[A-Za-z0-9_-]+\.js/.test(s))
  return src || null
}

function readServedEntry(html: string): string | null {
  const match = html.match(/[\w/-]*index-[A-Za-z0-9_-]+\.js/)
  return match ? match[0] : null
}

/**
 * Detect a new frontend deployment. Compares the entry bundle referenced by the
 * served index.html against the one currently loaded. When they diverge, calls
 * onUpdate() so the app can prompt the user to reload instead of silently
 * running a stale bundle against the new backend.
 */
export function startVersionCheck(onUpdate: () => void, intervalMs = 60000): () => void {
  currentEntry = currentEntry ?? readCurrentEntry()
  if (!currentEntry) return () => {}

  let stopped = false

  const check = async () => {
    if (stopped) return
    try {
      const response = await fetch('/', { cache: 'no-store' })
      const html = await response.text()
      const served = readServedEntry(html)
      if (served && served !== currentEntry) {
        onUpdate()
      }
    } catch {
      // Network/transient errors are ignored; retry on next tick.
    }
  }

  void check()
  const timer = window.setInterval(check, intervalMs)
  return () => {
    stopped = true
    window.clearInterval(timer)
  }
}