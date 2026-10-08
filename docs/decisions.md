# Decision log

| Date | Decision | Why |
| --- | --- | --- |
| 2026-10-08 | Require explicit approval for each GitHub push. | User request overrides automatic push instructions in the guide. |
| 2026-10-08 | Build and review one guide checkpoint at a time. | Keep verification and explanations understandable. |
| 2026-10-08 | Use the existing Project 3 workspace. | Avoid an unnecessary nested repository or folder move. |
| 2026-10-08 | Bind PostgreSQL to localhost and retain default memory settings initially. | Verify resource needs before tuning per-query memory. |
| 2026-10-08 | Install dependencies incrementally and lock resolved versions. | Keep each checkpoint reproducible without installing unused packages. |
| 2026-10-08 | Validate guide methodology against source documentation before implementation. | Example code and recalled column names are not verified specifications. |
| 2026-10-08 | Verify psycopg and SQLAlchemy connections in make verify. | Live integration exposed a driver parameter mismatch that import checks could not catch. |
| 2026-10-08 | Publish Step 0 to karthikeyansett1/medicare-claims after verification. | User explicitly approved this push; later pushes still require approval. |
