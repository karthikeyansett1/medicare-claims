# Measure specification: 30-day all-cause readmission

Written before implementation of Step 9. Financial, identity, and attribution
rules remain canonical in [the shared definitions](../docs/measure_definitions.md).
This is a descriptive measure of historical synthetic DE-SynPUF claims, not an
endorsed CMS quality measure or evidence about real patients/providers.

## Episode construction and audit population

Partition by sample-aware member identity. Order valid inpatient claim intervals
by admission, discharge, and claim stay ID. Merge an interval when its admission
is on or before the running maximum discharge of ALL preceding intervals in its
current chain. This merges overlaps, nested intervals, and same-day transfers.
Use the minimum admission and maximum discharge, retain every contributing claim
ID, count, and paid amount. A conflicting canonical header still participates in
the dated chain, but taints the whole episode and excludes it from the denominator.
Invalid or missing intervals remain as individual auditable excluded episodes;
never discard their claims or money. They cannot establish temporal ordering.

## Index population, numerator and ordered exclusions

An index is a merged episode discharged in 2009 or 2010. Compute the next valid
episode admission across ALL dated episodes before applying denominator exclusions.
An excluded next episode still counts as an observed admission; a header conflict
on that next episode instead makes the candidate index uncertain and excludes it.
A member with ANY undated/invalid inpatient episode is conservatively excluded
from all index denominators because its next admission cannot be established.
Chained readmissions can themselves be index episodes.

Ordered, mutually exclusive first exclusion (retain independent flags too):

1. Invalid or missing episode dates.
2. A member has an invalid or missing dated claim episode.
3. Current or next dated episode has a conflicting canonical header.
4. Discharge is outside performance years 2009 and 2010.
5. Earliest known member death is on or before discharge.
6. Discharge + 30 days is after available-data end 2010-12-31. December 1 has a
   complete window; December 2 does not.
7. Death occurs within the following 30 days (exclude full window rather than
   assume observation after death; this is a conservative project policy).
8. Index-year annual FFS screen is not true.
9. Full-year FFS proxy is not true for every calendar year touched by the 30-day
   follow-up, including the discharge year and next year when crossed.

Annual Part A/B counts of 12 and HMO count of zero form the strict follow-up
proxy. Missing enrollment is ineligible. These counts do NOT verify continuous
or overlapping monthly enrollment. No death-adjusted partial year is claimed to
supply a complete follow-up window. This deliberately conservative denominator
may exclude truly eligible people. The index-year screen uses the existing
is_ffs_eligible proxy and the subsequent full-year proxy is stricter.

For each eligible index, numerator is a next dated admission 1 through 30 days
inclusive after discharge. 31 days is false. A same-day admission has already
merged. Overall rate is numerator / denominator, NULL for zero denominator.

## Provider reporting

Attach by sample/member/discharge year to each retrospective attribution method
(A_visits and B_allowed). Keep unattributed indices visible in coverage totals.
Provider numerator and denominator count index episodes, not unique members.
Publish provider rows only with at least 20 attributed member-years in that
method/year panel; preserve raw rates and the reporting flag for auditing. Panel
size counts the full attributed eligible population, not just hospitalized people.

## Limits

No discharge-status code; inferred transfers can join unrelated same-day claims.
No planned-readmission exclusion, no clinical adjudication, no risk adjustment in
this base measure, no claim of complete enrollment verification. Conflicting and
undated claims make temporal inference uncertain; exclusions expose that cost.
2008 stays contribute temporal history but cannot be performance-year indices.
