# Attribution sensitivity — measured findings

Sample 1, performance years 2009 and 2010. All figures describe synthetic data;
the size of the effect, not the direction for any real provider, is the point.
Provider identifiers are synthetic and do not establish real provider identity or
specialty. Default panel threshold is 20 attributed eligible member-years.

1. **88.0% in 2009 and 85.9% in 2010** of members attributed under both methods
   changed providers (50,366/57,247 and 39,381/45,834). Coverage increased from
   **78.8% to 86.4%** in 2009 and **72.4% to 82.5%** in 2010 when switching
   from office-visit plurality A to professional-allowed-amount B. Coverage uses
   all 72,692 and 63,345 eligible members, respectively.
2. **0.412 and 0.017** were the A/B medical-PMPM Spearman correlations in 2009
   and 2010 across 105 and 82 common qualifying providers. **37/105 (35.2%)**
   and **42/82 (51.2%)** moved at least three deciles. Common-cohort top-decile
   Jaccard was **12.5% (2/16)** and **8.3% (1/12)**; 7 of 9 and 6 of 7
   Method A high-cost providers in that cohort were not high-cost under B.
3. **0.252/0.412/0.414 in 2009**, versus **0.149/0.017/0.073 in 2010**, were
   PMPM correlations at minimum panels of 10/20/30. Common cohorts changed
   from 187/105/79 providers and 142/82/67 providers. Threshold sensitivity
   changes who is compared as well as each provider's reference distribution;
   it is not a confidence interval or evidence that one threshold is correct.
4. **0.616/0.529 in 2009 and 0.736/0.769 in 2010** were raw-PMPM versus O/E
   correlations under A/B. Corresponding high-cost overlaps were
   **33.3%/15.8% and 33.3%/42.9%**. Adjustment changed ranking, but this
   concurrent descriptive GLM overpredicts aggregate costs by roughly 10–15%
   and is not clinically validated. It cannot establish which ranking is better.
5. **0.267 and 0.174** were A/B readmission-rate correlations across 105 and
   81 common providers with nonzero index denominators in 2009/2010.
   Top-decile Jaccard was **6.25% and 14.29%**. A 20-member panel does not
   guarantee a reliable readmission rate; index counts can be small, and tied
   rates are split by synthetic NPI for operational deciles. The audit waterfall
   retained **25,062 of 64,560 episodes**, across all audit years, after ordered
   exclusions; 2008/out-of-window episodes are intentionally visible.

## Why one provider moved

**9 deciles, from 1 to 10:** synthetic NPI `2392775208`, Sample 1, 2009,
is the largest absolute PMPM-decile mover, with absolute rank movement used to
break ties, then sample/year/NPI. It moved from rank 11/121 under A to 116/117
under B. PMPM increased from **$393.92 to $813.82**.

Both methods produced a 24-member panel, but only **3 members remained**;
**21 left and 21 entered**. Thus equal panel sizes conceal extensive cohort
replacement. Outgoing members accounted for $93,740 over 250 member-months;
incoming members accounted for $215,460 over 252 member-months. Retained
members contributed $18,920 over 36 months to both panels. These reconcile to
$112,660/286 months under A and $234,380/288 months under B.

| Medical paid component | Outgoing A-only | Incoming B-only | Change |
|---|---:|---:|---:|
| Inpatient | $25,000 | $125,000 | +$100,000 |
| Outpatient | $15,620 | $39,610 | +$23,990 |
| Professional | $53,120 | $50,850 | −$2,270 |
| Total | $93,740 | $215,460 | +$121,720 |

**$100,000 (82.2%)** of the medical-paid increase came from inpatient spending
among the incoming versus outgoing members. This is a cohort-composition
explanation, not evidence of a clinical cause or of services delivered by the
attributed provider. Medical PMPM includes all these members' medical services
regardless of rendering provider; Rx gross cost is excluded.

The professional-service export groups every traced cohort's lines by HCPCS,
without exporting member identifiers. For incoming members, `99213` accounts
for **75 lines/$4,770 paid** and `99214` for **61 lines/$2,850 paid**; missing
HCPCS accounts for **52 lines/$2,370 paid**. Professional paid actually falls
by $2,270 overall, so the office-service codes do not explain the PMPM increase.
The exported allowed amounts support auditing Method B's different selection
basis; paid and allowed amounts are not interchangeable. No diagnoses,
specialties, or clinical narratives are inferred from this trace.

## Inspect and reproduce

`make compare verify-comparison` after Step 10's mart build. Policies and evidence:
[Step 11 notes](../docs/steps/11-comparison.md).

- [Aggregate comparisons](output/method_comparison.csv)
- [Provider pairs](output/provider_comparison.csv)
- [Mover panel cohorts](output/mover_cohorts.csv)
- [Mover professional service codes](output/mover_services.csv)
- [Independent verification](output/verification.json)

![PMPM rank comparison](output/pmpm_rank_scatter.png)
![Absolute decile movements](output/decile_movement.png)
![Ordered readmission exclusions](output/readmission_waterfall.png)
