# Data sources and acquisition decisions

Verified on 2026-10-08. Exact acquisition URLs are in `ingest/urls.yaml`;
`data/manifest.csv` records source and resolved URLs, byte counts, SHA-256 hashes,
UTC download timestamps, and archive-to-extracted-file relationships.

## CMS DE-SynPUF Sample 1

The [CMS Sample 1 page](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf/de10-sample-1)
is the source index for the eight files. Seven archives were downloaded from
current CMS endpoints. Carrier and prescription links on that page use HTTP;
the corresponding HTTPS endpoints were tested and used successfully.

The page's 2010 Sample 1 beneficiary link actually targets a filename ending
`sample_20.zip`. We rejected that mismatch. Checking the Sample 20 page did not
provide a replacement, and the expected Sample 1 paths on current CMS servers
returned HTTP 404.

The replacement is a [2017-05-29 archive capture of the original CMS file](https://web.archive.org/web/20170529061306id_/https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads/DE1_0_2010_Beneficiary_Summary_File_Sample_1.zip).
The archive serves the original ZIP bytes. We verified its member name, ZIP CRC,
CSV header, and SHA-256, then confirmed all 112,754 beneficiary IDs belong to the
2008 Sample 1 population. The capture timestamp was located via a public
[acquisition script](https://github.com/Exios66/claims-data-eda/blob/main/scripts/acquire_synpuf.py);
we downloaded the data from the archived CMS URL, not from that repository,
and did not execute its code.

These are locally calculated hashes, not checksums published by CMS. They
support repeatability and change detection; archive metadata and beneficiary
linkage provide additional provenance evidence, not a cryptographic publisher
signature. The current live URL failures are retained here rather than hidden
behind an automatic source substitution.

CMS's [DE-SynPUF overview](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf)
explains the synthetic nature of the data and its limited inferential research
value. This project demonstrates analytical methods; it does not assess actual
providers or represent contemporary Medicare performance.

The user guide, codebook, and FAQ are stored under
`data/reference/documentation/`, using the links from the Sample 1 page.

## AHRQ CCS reference

Downloaded the single-level 2015 ZIP from the [official AHRQ CCS page](https://hcup-us.ahrq.gov/toolssoftware/ccs/ccs.jsp).
All four source CSVs are preserved unchanged under `data/reference/ccs_2015/`.
The ICD-9 mapping matches the project's historical coding period; AHRQ limits
these ICD-9 tools to discharges before October 1, 2015.

The diagnosis file includes an explanatory first line, quoted/padded fields,
and one blank-code placeholder. Acquisition validation found 15,072 unique
nonblank diagnosis codes. Parsing, category policy, and diagnosis coverage
against claims belong to Step 8; the raw source files are not cleaned here.

## Office E&M code list

`data/reference/em_office_visit_codes.csv` is a project-authored list of 10
historical codes: 99201–99205 for new patients and 99211–99215 for established
patients. The [CMS 2008 QIO statement of work](https://www.cms.gov/Medicare/Quality-Initiatives-Patient-Assessment-Instruments/QualityImprovementOrgs/Downloads/9thSOWBaseContract_C_08-01-2008_2_.pdf)
identifies these office-visit ranges. Our descriptions are short project labels,
not copied full CPT descriptors.

The initial attribution candidate set excludes consultation, home, nursing
facility, and wellness codes. Office E&M activity does not establish primary
care specialty: providers outside primary care can bill these services.
Attribution methodology and visit deduplication will be defined in Step 7.
