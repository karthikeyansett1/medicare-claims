# Architecture decisions

| Decision | Rationale and tradeoff |
| --- | --- |
| Preserve raw bronze records | Enables source tracing and reconciliation; costs additional storage. |
| Use sample-aware identifiers | Prevents member and claim collisions when combining CMS samples. |
| Resolve claims before joining diagnoses | Avoids multiplying financial amounts across segments or diagnoses; conflicting headers remain explicitly flagged. |
| Retain payments with missing HCPCS | Missing procedure codes should not erase financial activity; procedure-based analyses have narrower coverage. |
| Keep two attribution methods | Makes provider-panel sensitivity measurable rather than assuming one definition is authoritative. |
| Rank before intersecting providers | Preserves each method's reference population; common-provider comparisons then have explicit denominators. |
| Adjust cost only | The implemented expected-cost model is descriptive; observed readmissions are not mislabeled as risk-standardized. |
| Use aggregate dashboard exports | Public browsing requires neither database credentials nor model calls. |
| Host a separate 1,000-member fixture | Fits constrained hosting resources; live answers must be labeled separately from the full dashboard. |
| Separate query and budget roles | Read-only analytics and fixed-function spend reservations follow distinct privilege boundaries. |
| Reserve API allowance before dispatch | A shared PostgreSQL lock protects against concurrent overspend; conservative failed-call reservations reduce available usage. |
| Keep fixed-set evaluation evidence | Reproducible comparisons reveal regression behavior; a new held-out set is still needed for generalization claims. |

See [measure definitions](../assistant/measure_definitions.md), [findings](../analysis/findings.md) and [evaluation results](../eval/results/summary.md) for implementation detail and evidence.
