# Resume entry

**Medicare Provider Performance Analytics | Claims Analytics & Generative AI**
SQL, PostgreSQL, dbt, Python, Streamlit, OpenAI Responses API, Docker, GitHub Actions

- Built a reproducible claims warehouse from **23.0M raw rows** covering 232,747 synthetic Medicare members; reconciled silver and gold with 205 checks, preserving $41.335M in professional paid amounts on lines missing HCPCS codes.
- Quantified attribution sensitivity: **35%–52% of common qualifying providers** moved at least three medical-PMPM deciles across four sample/year cohorts; implemented audited 30-day readmissions, CCS inpatient cost grouping and descriptive cost adjustment.
- Implemented a guarded text-to-SQL assistant with **50 held-out evaluation cases**, a semantic layer, SQL AST validation and read-only PostgreSQL execution; verified the isolated pipeline with 133 Python tests. Paid model evaluation remains deferred.

These bullets describe implementation and measured synthetic-data findings. The 23.0M figure includes beneficiary records, claim segments and drug events; it is not a count of distinct medical claims. The 205 checks are full-data silver/gold reconciliations, while 133 is the later isolated database-enabled Python suite, not 133 assistant tests. The historical assistant checkpoint passed 114 tests. Offline execution of 45 gold queries plus five clarification cases supplies no model accuracy or improvement score.

Use the [interview notes](interview_prep.md) to explain these distinctions. Evidence: [source and reconciliation scope](steps/11b-sample2.md), [missing-HCPCS payments](silver_reconciliation.json), [rank findings](../analysis/findings.md), [CI verification](steps/15-ci.md), [evaluation status](../eval/results/summary.md).
