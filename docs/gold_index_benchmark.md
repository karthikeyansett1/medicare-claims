# Gold index experiment

On isolated copies of all 9,388,987 professional line join columns
and 116,352 members, run a provider/year filter joined to members
and grouped by sex. Choose the most frequent rendering NPI deterministically.

- Before indexes: median **235.068 ms** across three measured runs.
- After indexes: median **27.686 ms** across three measured runs.
- Same query results: **20,867 matching lines**, identical sums.
- Added B-tree indexes on `(rendering_npi, service_dt)` and unique `(member_key)`.

Each condition had one warm-up. Planner choices were not forced. This is one
local, selective-query experiment with warm caches and narrower copied tables;
it does not establish a production speedup or a benefit for every query.
Bulk aggregations may still appropriately use sequential scans. Existing gold
indexes were not removed. The temporary benchmark schema was removed afterward.

See [all timings and EXPLAIN plans](gold_index_benchmark.json).
