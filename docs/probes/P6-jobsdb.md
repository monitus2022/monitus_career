# P6 — JobsDB stability

**Verdict: PASS — structure unchanged from the design doc's finding.**

(Design doc not in repo; structure recorded here + in the untracked capture so
any later regression can be diffed.)

- `GET https://hk.jobsdb.com/api/jobsearch/v5/search?siteId=hk-jobsdb&keyword=test&pageSize=2&page=1&locale=en`
  → 200 JSON (2.7 KB):
```json
{"data":[{"advertiser":{"id":"…","description":"…"},
          "classifications":[{"classification":{…},"subclassification":{…}}],
          "displayType":"standard","id":"95617673",
          "isFeatured":false,
          "listingDate":"2026-10-31T09:43:51Z",
          "listingDateDisplay":"1d ago",
          "locations":[{"label":"…","countryCode":"AU","seoHierarchy":[…]}, …], …}]}
```
- **Caution observed:** with the probe's minimal params the endpoint returned
  geo-mismatched results (AU rows). `sources/jobsdb.py` filters by
  `countryCode == "HK"` (discards foreign rows) and the B1 capture re-records
  the exact request params used by the daily run.
- No further probing outside the daily run (build-plan rule).
