# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
## Page Functionality Matrix & Capability Specifications

---

| Page # | Page Name | Section | Backing Data Sources | Interactive Filters & Controls | Output Visualizations | RBAC Restrictions |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `Executive Overview` | Overview | SQLite `reviews`, `opportunities`, `outputs/*.csv` | Quick-jump buttons to S0-S7 stages, Opportunity dossiers | Metric cards, Coverage indicators, Top pain-point cards | None (All roles) |
| **2** | `Source Manager` | Data & Sources | `config/app_registry.json`, Ingestion logs | Route enable/disable toggles, Store registry filters | Registry status table, Route status badges | Route toggling restricted to `ADMIN` |
| **3** | `Collection History` | Data & Sources | SQLite `ingestion_runs`, `reviews` | Filter by App, Store, Status; Run inspector | Run log table, Diagnostic payload inspector | None (All roles) |
| **4** | `Review Explorer` | Data & Sources | SQLite `reviews` (3,790 eligible records) | Text search, App filter, Rating, Relevance, Stage, Pagination | Paginated review cards, Verbatim span highlight, CSV export | CSV export restricted to `ADMIN`, `RESEARCHER`, `AUDITOR` |
| **5** | `SIP Journey Explorer`| Research & Insights | `outputs/lifecycle_journey_analytics.csv`, SQLite | Selectbox for S0-S7 stages, App selector | Longitudinal stage cards, Friction density chart, Verbatim quote box | None (All roles) |
| **6** | `Investor Behaviour` | Research & Insights | `ai_evidence_log`, SQLite | Dimension selector (Motivations, Expectations, Triggers, Workarounds) | Distribution bar charts, Grounded behavioural cards | None (All roles) |
| **7** | `Theme Explorer` | Research & Insights | `outputs/theme_frequencies.csv`, SQLite | Domain filter, Theme selector dropdown | Theme dossier, Cross-app prevalence comparison chart, Review snippets | None (All roles) |
| **8** | `App Comparison` | Research & Insights | `outputs/cross_app_benchmarks.csv` | App selector checkboxes, RPPI metric toggles | Comparative benchmark table, Multi-app bar chart, Sentiment scatter | None (All roles) |
| **9** | `Opportunity Radar` | Opportunity Discovery| SQLite `opportunities` table | Filter by Stage, App, Status; Text search; Dossier button | 2D Strategic Matrix (Severity vs Actionability), Leaderboard table | None (All roles) |
| **10**| `Opportunity Detail` | Opportunity Discovery| SQLite `opportunities`, `opportunity_audits` | Opportunity selector dropdown, Status update form, Rationale | Dossier specification cards, Multi-factor score cards, Audit table | Status updates restricted to `ADMIN` and `RESEARCHER` |
| **11**| `AI Evidence Log` | AI & Validation | SQLite `ai_evidence_log`, `reviews` | Search ID/Text, App filter, Confidence tier, Routing decision | Paginated log table, Provenance inspector, SHA-256 prompt hash | None (All roles) |
| **12**| `Model Validation` | AI & Validation | `outputs/model_evaluation_metrics.json` | Cohort view toggles (Multilingual, App cohorts) | PRD Quality Gate cards, Cohort tables, Per-class F1 tables | None (All roles) |
| **13**| `Human Validation` | AI & Validation | `HumanReviewService`, SQLite `human_adjudications` | Queue selector, Accept/Correct/Reject radio, Rationale input | Adjudication form, Predicted vs corrected labels, Audit history | Form submission restricted to `ADMIN` and `RESEARCHER` |
| **14**| `Exports & Reports` | Reports & Exports | `outputs/*.csv`, `services/pdf_export_service.py` | CSV download buttons, PDF download buttons, Filtered review export | File metadata cards, Download buttons, Role permission indicator | Raw review export restricted to `ADMIN`, `RESEARCHER`, `AUDITOR` |
