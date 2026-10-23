// Captures the landing-page screenshots from a signed-in demo workspace, in light and dark.
//
//   1. Run backend + frontend (frontend on http://localhost:3000) and open /app once so the demo workspace exists.
//   2. Copy the `sessionid` cookie from that browser session.
//   3. SESSION_ID=<cookie> WORKSPACE_ID=<demo workspace id> npx --yes -p playwright node scripts/capture-screenshots.mjs
//
// Output: public/landing/{tickets,ticket,knowledge}-{light,dark}.png, which landing-page.tsx picks up on its own.
import { chromium } from 'playwright'

const BASE = process.env.BASE_URL ?? 'http://localhost:3000'
const { SESSION_ID, WORKSPACE_ID } = process.env
if (!SESSION_ID || !WORKSPACE_ID) throw new Error('Set SESSION_ID and WORKSPACE_ID.')

const SHOTS = [
  { name: 'tickets', path: `/app/${WORKSPACE_ID}/tickets` },
  { name: 'knowledge', path: `/app/${WORKSPACE_ID}/knowledge` },
  { name: 'ask', path: `/app/${WORKSPACE_ID}/ask` },
]

const browser = await chromium.launch()
for (const scheme of ['light', 'dark']) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2, colorScheme: scheme })
  await context.addCookies([{ name: 'sessionid', value: SESSION_ID, url: BASE }])
  // The tour must not cover the page: mark every tour as seen before the app loads.
  await context.addInitScript(() => localStorage.setItem('resolveai-tour-seen', JSON.stringify(['dashboard', 'tickets', 'ticket', 'knowledge', 'ask', 'members', 'settings'])))
  const page = await context.newPage()
  for (const { name, path } of SHOTS) {
    await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' })
    await page.screenshot({ path: `public/landing/${name}-${scheme}.png` })
  }
  await context.close()
}
await browser.close()
