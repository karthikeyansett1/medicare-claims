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
- [x] Step 6: Data quality tests — verified and pushed; draft PR #6 open
- [x] Step 7: Attribution, Methods A and B — verified and pushed; draft PR #7 open
- [x] Step 8: Clinical grouper with AHRQ CCS — verified and pushed; draft PR #8 open
- [x] Step 9: Quality measure, 30-day all-cause readmission — verified and pushed; draft PR #9 open
- [x] Step 10: Cost and utilization metrics — verified and pushed; draft PR #10 open
- [x] Step 11: Methodology comparison — verified and pushed; draft PR #11 open
- [x] Step 11b: Integrate and verify Sample 2 before assistant evaluation — verified and pushed; draft PR #12 open
- [x] Step 12: Assistant implementation verified and pushed, draft PR #13; live validation deferred by user
- [ ] Step 13: Offline evaluation harness and gold validation implemented; paid accuracy, v1/v2 and faithfulness deferred
- [ ] Step 14: Provider scorecard dashboard
- [ ] Step 15: CI/CD, Makefile, and Docker
- [ ] Step 16: Methodology memo and README
- [ ] Step 17: Deploy, put it on the resume, prep for interviews

Each checkpoint records: what changed, why, how to explain it, commands run,
actual results, limitations, and a GitHub commit and push after verification.
Sample 1 comes first; Sample 2 follows a verified end-to-end build.
Do not invent row counts, performance improvements, or evaluation scores.
