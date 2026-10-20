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

## Credential recovery checkpoint

Replaced the runtime database passwords and private access code after accidental disclosure, and rebuilt the ignored private configuration using the owner’s replacement API key. Verified new runtime connections and fixture permissions with the lifetime campaign and reservation count unchanged. No API calls were made. Owner must replace any previously saved Streamlit Secrets before activation; provider-side revocation of the old API key remains owner-managed.

## Hosted startup verified

The [protected Streamlit assistant](https://karthikeyans-afjcffkdltc8rije9i7upq.streamlit.app/) now starts on Python 3.11 and accepts the saved configuration. The browser renders the fixture scope, shared allowance and question form; submitting without the private code is rejected. Startup/access checks made no paid model calls. An authenticated cloud query and generated answer remain to be verified; local hosted-database checks do not establish that complete path.

## Public demo navigation and design

Added a Live AI Demo link in the dashboard sidebar and a separate invitation beside saved examples. Both disclose the private-code requirement and fixture scope. Refreshed the static UI as a warm field guide with serif headlines, numbered navigation, paper colors, ink borders and orange/green accents. Measures, exports and filters are unchanged. This makes the project more approachable while keeping the difference between full-data charts and the live fixture explicit.

## Live explorer presentation

Styled the Streamlit app to match Atlas: paper/green palette, branded sidebar, clear question form, readable attribution choices, starter questions, and separate result-table/SQL tabs. Assumptions render as bullets rather than a JSON tree. Authentication still occurs before database or API initialization; form values clear after submission. Offline UI checks covered startup, empty-code rejection and rendering a synthetic answer with assumptions/table/SQL without model calls.

## Live presentation reverted

The owner rejected the decorative live explorer redesign. Restored the previous Streamlit interface; access controls, query behavior and spending limits remain unchanged. The public static dashboard and Live AI Demo links remain as previously accepted. All 31 targeted live tests passed after restoration.

## Restrained color theme

Applied a native Streamlit light theme with white background, light-gray input surfaces, charcoal text and navy accents. This color-only update preserves the restored layout, labels, authentication and spending controls. Verified configuration parsing and app rendering offline without API calls.

## Unified dark analytics interface

Replaced the warm decorative styling with charcoal/gray surfaces, high-contrast text, restrained typography and subtle borders across the static dashboard and live assistant. Kept navigation, dataset boundaries and live access requirements visible. The live form groups year/method controls; answers expose readable assumptions and Data/SQL tabs. Verified 35 targeted tests and offline UI startup, access rejection and result rendering without paid calls.
