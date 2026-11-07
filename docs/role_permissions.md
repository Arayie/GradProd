# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
## Role-Based Access Control (RBAC) & Governance Specification

---

## 1. Overview & Security Objectives

To ensure compliance with data governance, intellectual property protection, and customer review data privacy, the Growww Discovery Engine enforces server-side Role-Based Access Control (RBAC) via [`core/auth.py`](file:///Users/aradhyayadav/Downloads/GradProd/core/auth.py).

The RBAC system guarantees that:
1. **Raw Review Data Privacy:** Viewer roles cannot export unmasked raw customer reviews.
2. **Backlog Integrity:** Only authorized researchers and administrators can change opportunity lifecycle statuses or record human adjudication decisions.
3. **Audited Transparency:** Every privilege-bearing action creates an immutable log entry in SQLite tracking the actor ID, timestamp, and rationale.

---

## 2. Role Definitions

| Role | Target Persona | Scope of Authority |
| :--- | :--- | :--- |
| **`ADMIN`** | System Architect / Lead PM | Unrestricted access across data sources, permissions, adjudication, opportunity status, and data exports. |
| **`RESEARCHER`** | Product Researcher / Analyst | Full research access: can inspect reviews, update opportunity states, adjudicate AI predictions, and export raw/aggregate datasets. |
| **`VIEWER`** | Stakeholder / Business User | Read-only access to dashboards, analytics, and executive PDF reports. Cannot export raw reviews or alter opportunity states. |
| **`AUDITOR`** | Compliance / Governance Officer | Read-only access to analytics plus audit trail inspection and raw data export for regulatory verification. Cannot alter data or states. |

---

## 3. Strict Permission Matrix

| Capability / Permission | Admin | Researcher | Viewer | Auditor |
| :--- | :---: | :---: | :---: | :---: |
| **`MANAGE_SOURCES`** (Enable/disable store routes) | **YES** | NO | NO | NO |
| **`MANAGE_PERMISSIONS`** (Role assignment) | **YES** | NO | NO | NO |
| **`ADJUDICATE_REVIEWS`** (Label corrections) | **YES** | **YES** | NO | NO |
| **`UPDATE_OPPORTUNITIES`** (Backlog status changes) | **YES** | **YES** | NO | NO |
| **`EXPORT_RAW_DATA`** (Filtered customer reviews) | **YES** | **YES** | NO | **YES** |
| **`EXPORT_REPORTS`** (Executive PDFs & aggregate CSVs) | **YES** | **YES** | **YES** | **YES** |
| **`VIEW_AUDIT_LOGS`** (Inspect adjudication/status logs) | **YES** | **YES** | NO | **YES** |
| **`VIEW_ANALYTICS`** (Access dashboards & charts) | **YES** | **YES** | **YES** | **YES** |

---

## 4. Server-Side Enforcement Mechanisms

The RBAC enforcement is implemented directly within page logic and service calls:

- **Opportunity State Transitions:**
  [`OpportunityService.update_status()`](file:///Users/aradhyayadav/Downloads/GradProd/services/opportunity_service.py) requires an actor ID and rationale. The UI checks `AuthService.can_update_opportunities()`; if unauthorized, form controls are replaced with an informative read-only alert.
- **Human Review Adjudication:**
  [`ui/pages/human_validation_ui.py`](file:///Users/aradhyayadav/Downloads/GradProd/ui/pages/human_validation_ui.py) disables submission buttons when `AuthService.can_adjudicate()` returns `False`.
- **Raw Review Data Export:**
  [`ui/pages/exports_reports.py`](file:///Users/aradhyayadav/Downloads/GradProd/ui/pages/exports_reports.py) checks `AuthService.can_export_raw_data()`. Viewer users receive a warning banner and the download button is not rendered.
