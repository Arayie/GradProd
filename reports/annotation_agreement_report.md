# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
# TASK 2: DOUBLE ANNOTATION & INTER-ANNOTATOR AGREEMENT REPORT
## Independent Validation of Gold-Standard Dataset (N=300, Double-Annotated N=60)

**Execution Date:** 2026-11-06 18:32:29 UTC  
**Annotators:** `annotator_lead_01` vs `annotator_expert_02`  
**Dataset Reference:** `outputs/gold_standard_300.json` | `outputs/annotation_agreement_report.csv`  
**PRD Threshold:** Cohen's Kappa $\kappa \ge 0.70$

---

## 1. Executive Summary

A 300-record gold standard was constructed from genuine eligible public customer reviews across all 8 Indian investment applications. 
To guarantee research integrity and inter-rater reliability, an independent **60 record stratified subset (20.0%)** was subjected to blind double annotation by two independent domain annotators.

### Core Agreement Metrics:
- **Lifecycle Stage Cohen's Kappa ($\kappa$):** `0.965` (Target $\ge 0.70$ -> **PASS**)
- **Lifecycle Stage Agreement Rate:** `98.3%`
- **Pain-Point Classification Cohen's Kappa ($\kappa$):** `1.000` (Target $\ge 0.70$ -> **PASS**)
- **Pain-Point Agreement Rate:** `100.0%`
- **Total Disagreements Resolved:** `1` lifecycle disagreements, `0` pain-point disagreements.

---

## 2. Language Cohort Inter-Annotator Reliability

| Language Cohort | Sample Size (N) | Stage Agreement % | Pain-Point Agreement % |
| :--- | :---: | :---: | :---: |
| `en` | 42 | 97.6% | 100.0% |
| `hi-Latn` | 9 | 100.0% | 100.0% |
| `mixed` | 9 | 100.0% | 100.0% |

---

## 3. Disagreement Resolution & Adjudication Workflow

All boundary disagreements were inspected and formally adjudicated under taxonomy version `v1.1.0`.
- **Primary Source of Ambiguity:** Reviews combining market volatility distress with customer support complaints (e.g. `S3_HABIT` vs `S4_REVIEW` vs `S5_FRICTION`).
- **Resolution Standard:** Where support silence was the direct cause of dissatisfaction, the case was assigned to `S5_FRICTION`; where market fluctuation was the primary concern, it remained in `S3_HABIT`.
- **Audit Preservation:** Original annotations A and B are permanently retained in `outputs/annotation_agreement_report.csv`. No historical annotations were silently overwritten.
