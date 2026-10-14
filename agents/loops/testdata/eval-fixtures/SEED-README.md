# Seed eval fixtures (Phase 5, LRN-02)

Every file in this directory is **seed content**: hand-shaped synthetic
pages and canned model outputs for offline eval proof. No real meeting
text, no real run output, no credential values of any shape appear here.
Real-run cases replace seeds as the trial produces them; the runner
accepts both (`origin: seed` vs `origin: real`).

Layout (flat page-JSON convention, mirroring
`agents/loops/testdata/meeting-pages/`):

- `seed-page-*.json` — canned input pages, one per eval shape (good
  contract, malformed, injection attempt, empty). The runner scans them
  in sorted filename order and shape-checks each offline.
- `seed-<nnn>.json` — canned model outputs keyed by eval-case id. When
  present, the runner grades the canned output instead of its local
  extraction, proving the offline grading path end to end.
