# Legacy

`munischema.json` is the original single-file draft that started this repository. It is kept
for reference and is **not conformant**. Three problems motivated the current design:

1. **Typed `City` but carried `Organization` properties** — `employee`, `department`,
   `parentOrganization`, `subOrganization`, `member`, `knowsAbout`, and `foundingDate` all
   have domain `Organization`, and `City` is a `Place`. See SPEC §1.1.

2. **Twelve properties that do not exist in schema.org** — `population`, `timeZone`,
   `mayor`, `governmentService`, `news`, `committee`, `legislation`, `ordinances`,
   `resolutions`, `meetingSchedule`, `legislationStatus`, `supersedes`. Most have real
   replacements; see the table in SPEC §1.3.

3. **Entities inlined rather than referenced** — `{"@type":"City","name":"Example City"}`
   appears seven times as a stub copy. See SPEC §1.2.

The conformant equivalent is `examples/example-gov/`.
