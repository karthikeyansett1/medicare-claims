# Step 13 evaluation status

**Offline harness checkpoint only. No model accuracy has been measured.**
The user requested continuing without paid evaluation. Earlier provider attempts
failed with HTTP 429 `credit_balance_exhausted` / `insufficient_quota`; no successful
generation resulted. This checkpoint makes no paid API requests.

| Evidence | v1 | v2 |
|---|---|---|
| Execution accuracy (50 questions) | Pending live evaluation | Pending live evaluation |
| Failures by methodology type | Pending | Pending |
| Three-run accuracy range | Pending | Pending |
| Answer faithfulness (15 manual reviews) | Pending | Pending |
| Actual token usage and dollar cost | Unknown | Unknown |

The 50-question set has 45 executable gold queries and five clarification cases.
Their read-only validation is implementation evidence, **not** AI accuracy.
Actual offline validation completed: **45 gold queries executed, 5 clarification
cases**, and **123 database-enabled tests passed**. See
`offline_gold_validation.json` for the execution metadata and reproducibility hashes.
Mock responses exist only in unit tests and never supply an evaluation score.

All ten required failure types are defined in `eval/run_eval.py`. Each failed
case receives exactly one provisional automated label and evidence. A reviewer
must confirm or replace the label using generated SQL and result evidence; a
result mismatch alone does not prove a denominator, join, or methodology error.
Three example model failures cannot be supplied until actual generations exist.

## Authorized future workflow

1. Verify quota and obtain new authorization before any live invocation. Record
   the immutable sample/build identity; freeze the v1 prompt and gold set hashes.
2. Run v1 with explicit call/token limits. Investigate operational failures;
   incomplete runs have no accuracy score. Never turn quota errors into 50 retries.
3. Review every failure and select the leading two or three failure types.
   Improve general definitions, prompt rules, or separate training examples.
   Never put gold SQL or held-out expected answers in runtime context.
4. Freeze v2 and run all 50 questions, eventually three repetitions. The current
   API omits temperature because support for this model is unverified; do not
   claim temperature-zero variance until the configuration is supported and used.
5. Complete the 15-answer faithfulness review with named reviewer provenance.
   Report v1/v2 execution scores, all ten failure counts, three genuine failure
   examples, review scores and v2 range. Preserve every run, including failures.

No v2 improvement or before/after gain is claimed at this checkpoint.
