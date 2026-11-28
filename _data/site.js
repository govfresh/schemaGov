import fs from 'node:fs'

// `site` is shaped like Jekyll's `site` object (site.baseurl,
// site.data.site, site.data.nav, site.data.icon_presets) so govfresh-ui's shared
// Liquid includes (nav.html, footer.html, cta-banner.html, footer-nav.html)
// render here unmodified instead of being hand-ported. Existing templates'
// `site.title`, `site.url`, etc. keep working. The config itself lives in
// _lib/site.json.
const read = (p) => JSON.parse(fs.readFileSync(new URL(p, import.meta.url), 'utf8'))

const site = read('../_lib/site.json')

export default {
  ...site,
  baseurl: '',
  data: {
    site,
    nav: read('./nav.json'),
    icon_presets: read('./icon_presets.json'),
    'site-index': true,
  },
}
