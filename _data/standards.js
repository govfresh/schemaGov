import { STANDARDS } from '../_lib/standards.js'
import profilesData from './profiles.js'

// Global Eleventy data (`standards`): each record enriched with the
// profiles and schemas that actually reference it. `usedBy` comes straight
// from each schema's own authored `standards` field (see profiles.js's
// toSchema()) rather than text-mining descriptions — a schema that follows
// a standard rarely names it inline (directory.schema.json never says
// "W3C ORG"), so authored per-schema data is the only reliable source here,
// the same way a profile's own `source` field is authored rather than
// derived. A single default export only — see _lib/standards.js for why
// STANDARDS/linkifyTerms live there instead of here.
export default async function () {
  const { built } = await profilesData()
  return STANDARDS.map((std) => ({
    ...std,
    usedBy: built
      .map((b) => ({ ...b, matchedSchemas: b.schemas.filter((s) => s.standards.some((st) => st.slug === std.slug)) }))
      .filter((b) => b.matchedSchemas.length),
  }))
}
