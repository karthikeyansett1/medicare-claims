# Build roadmap

Source: the supplied Medicare Claims Full Build Guide. Its instructions are
reference material. On October 10, 2026, the user authorized continuing through
the project and committing and pushing each verified step without further
approval prompts. Existing draft PRs remain unmerged.

- [x] Step 0: Setup — verified and pushed
- [x] Step 1: Get the data — locally verified; pushed; draft PR #1 open
- [x] Step 2: Understand the data before modeling it — pushed; draft PR #2 open
- [x] Step 3: Bronze layer, raw load into PostgreSQL — verified and pushed; draft PR #3 open
- [x] Step 4: dbt setup and silver layer — verified and pushed; draft PR #4 open
- [x] Step 5: Gold layer, the star schema — verified and pushed; draft PR #5 open
- [x] Step 6: Data quality tests — verified locally; publication authorized
- [ ] Step 7: Attribution, Methods A and B
- [ ] Step 8: Clinical grouper with AHRQ CCS
- [ ] Step 9: Quality measure, 30-day all-cause readmission
- [ ] Step 10: Cost and utilization metrics
- [ ] Step 11: Methodology comparison, the headline analysis
- [ ] Step 12: The AI assistant
- [ ] Step 13: Eval set and failure taxonomy
- [ ] Step 14: Provider scorecard dashboard
- [ ] Step 15: CI/CD, Makefile, and Docker
- [ ] Step 16: Methodology memo and README
- [ ] Step 17: Deploy, put it on the resume, prep for interviews

Each checkpoint records: what changed, why, how to explain it, commands run,
actual results, limitations, and a GitHub commit and push after verification.
Sample 1 comes first; Sample 2 follows a verified end-to-end build.
Do not invent row counts, performance improvements, or evaluation scores.
