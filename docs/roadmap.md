# Build roadmap

Source: the supplied Medicare Claims Full Build Guide. Its instructions are
reference material. On October 10, 2026, the user authorized continuing through
the project and committing and pushing each verified step without further
approval prompts. The user later authorized integration and release. All source commits are integrated into main through PR #18 (merge 16c0527); PR #1 auto-merged and redundant ancestor PRs #2–17 were closed. No branch was deleted. The chosen deliverable is the free static showcase; live hosting and further paid work are not required.

- [x] Step 0: Setup — verified and pushed
- [x] Step 1: Get the data — locally verified; pushed; historical PR #1, integrated via #18
- [x] Step 2: Understand the data before modeling it — pushed; historical PR #2, integrated via #18
- [x] Step 3: Bronze layer, raw load into PostgreSQL — verified and pushed; historical PR #3, integrated via #18
- [x] Step 4: dbt setup and silver layer — verified and pushed; historical PR #4, integrated via #18
- [x] Step 5: Gold layer, the star schema — verified and pushed; historical PR #5, integrated via #18
- [x] Step 6: Data quality tests — verified and pushed; historical PR #6, integrated via #18
- [x] Step 7: Attribution, Methods A and B — verified and pushed; historical PR #7, integrated via #18
- [x] Step 8: Clinical grouper with AHRQ CCS — verified and pushed; historical PR #8, integrated via #18
- [x] Step 9: Quality measure, 30-day all-cause readmission — verified and pushed; historical PR #9, integrated via #18
- [x] Step 10: Cost and utilization metrics — verified and pushed; historical PR #10, integrated via #18
- [x] Step 11: Methodology comparison — verified and pushed; historical PR #11, integrated via #18
- [x] Step 11b: Integrate and verify Sample 2 before assistant evaluation — verified and pushed; historical PR #12, integrated via #18
- [x] Step 12: Assistant implementation verified and pushed, historical PR #13; funded smoke later completed 7/8; public app remains static
- [x] Step 13: Offline harness and gold validation verified and pushed, historical PR #14; funded v1 39/50; v2 49/50 in each of three reused-set regression runs; agent faithfulness review complete, independent human review pending
- [x] Step 14: Four-page Streamlit dashboard and offline extracts independently verified (129 tests); screenshots saved, published in historical PR #15
- [x] Step 15: CI/Docker verified locally and on GitHub, historical PR #16; main requires ci and an up-to-date branch (admin enforcement off)
- [x] Step 16: Methodology memo, README and architecture documented; [verification and provenance](steps/16-docs.md), published in historical PR #17
- [x] Step 17: Free static dashboard and verified SQL demo deployed; hosted fixture, resume and interview prep documented. PR #18 merged the complete verified history into main; public live AI and Docker compute are not deployed; see [deployment evidence](steps/17-deploy.md).

Each checkpoint records: what changed, why, how to explain it, commands run,
actual results, limitations, and a GitHub commit and push after verification.
Sample 1 comes first; Sample 2 follows a verified end-to-end build.
Do not invent row counts, performance improvements, or evaluation scores.
