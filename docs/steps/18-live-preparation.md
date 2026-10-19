# Step 18 — prepare an access-controlled live fixture assistant

## What changed and why

The user subsequently authorized a free Streamlit deployment with a private access code and a separate **$5 lifetime allowance**. This supersedes the earlier choice to stop at the static showcase. The existing public dashboard remains available and unchanged in scope. The live assistant is a separate application for the hosted deterministic 1,000-member Sample 1 fixture; it does not query the full two-sample warehouse.

A shared PostgreSQL campaign reserves a conservative request cost before every API dispatch, serializing concurrent requests with a row lock. Its fixed lifetime cap, three-calls-per-minute limit and 30-calls-per-day limit apply across users and replicas. Failed calls retain reservations; runtime roles cannot reset the campaign or increase its allowance. A high-entropy shared access code is checked before client or database initialization. Query and budget credentials are separate least-privilege roles, with verified TLS and fixed fixture checks.

## Verified state

The one-time hosted bootstrap is complete. **Do not rerun bootstrap, recreate the campaign, or reset spending.** [Hosted evidence](../../deployment/live/verification.json) records seven passing checks: effective privileges/TLS/fixture identity; denied query-role writes and budget execution; budget privilege/cost/minute controls; lifetime cap; rolling-day cap; two-connection serialization; and rolled-back probes. Reserved spend and reservation rows remain zero, and verification made **zero API calls**. Sequence values can advance during rolled-back probes without spending allowance.

The generated `.runtime/streamlit-live-secrets.toml` is ignored and mode 600. It contains private server-side settings and must never enter Git, screenshots, logs or release assets. The owner must paste it into Streamlit's private secrets settings. Deployment is **not yet active or verified**; human review of PR #19 remains pending. The historical $20 local evaluation campaign is separate from this new $5 live-app allowance.

## Explain it in an interview

“I separated the full-data showcase from a small live engineering fixture. The static dashboard costs nothing per visit. The live assistant has a private access code and a database-backed lifetime allowance that is reserved before requests, including failures. I verified actual hosted privileges and concurrency with rolled-back probes rather than treating mocks as proof of database enforcement. The remaining deployment step is private owner configuration; I do not claim a live service until its hosted behavior is verified.”

[Implementation and owner setup](../../deployment/live/README.md) documents the scope, request bounds and runtime guarantees. The cap governs this app's requests, not unrelated API-key use or future provider price changes.
