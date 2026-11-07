# GROWWW – AI-POWERED INVESTOR DISCOVERY ENGINE
# SECURITY & COMPLIANCE CHECKLIST
## Verified Controls, RBAC Matrix, Sanitization Standards, and Hardening Sign-Off

**Version:** 1.0.0 (Phase 7 Hardened)  
**Verification Date:** 2026-11-07  
**Status:** **AUDITED & COMPLIANT**

---

## 1. Role-Based Access Control (RBAC) Matrix

The system enforces strict server-side capability checking via `core/auth.py` (`AuthService.has_permission`).

| Operation / Capability | ADMIN | RESEARCHER | VIEWER | AUDITOR | Enforcement Mechanism |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Manage Ingestion Routes & Credentials** | ✅ ALLOW | ❌ DENY | ❌ DENY | ❌ DENY | `Permission.MANAGE_SOURCES` |
| **Manage Route Permissions** | ✅ ALLOW | ❌ DENY | ❌ DENY | ❌ DENY | `Permission.MANAGE_PERMISSIONS` |
| **Human Adjudication Workbench** | ✅ ALLOW | ✅ ALLOW | ❌ DENY | ❌ DENY | `Permission.ADJUDICATE_REVIEWS` |
| **Update Opportunity Status & Lifecycle** | ✅ ALLOW | ✅ ALLOW | ❌ DENY | ❌ DENY | `Permission.UPDATE_OPPORTUNITIES` |
| **Export Raw Customer Review Datasets** | ✅ ALLOW | ✅ ALLOW | ❌ DENY | ✅ ALLOW | `Permission.EXPORT_RAW_DATA` |
| **Export Aggregate Analytics & PDF Dossiers** | ✅ ALLOW | ✅ ALLOW | ✅ ALLOW | ✅ ALLOW | `Permission.EXPORT_REPORTS` |
| **View Audit Trail & AI Evidence Log** | ✅ ALLOW | ✅ ALLOW | ❌ DENY | ✅ ALLOW | `Permission.VIEW_AUDIT_LOGS` |
| **View Discovery Dashboards & Analytics** | ✅ ALLOW | ✅ ALLOW | ✅ ALLOW | ✅ ALLOW | `Permission.VIEW_ANALYTICS` |

---

## 2. Input Sanitization & Vulnerability Mitigation

### 2.1 SQL Injection Protection
- **Rule:** Zero string concatenation or f-string interpolation for database values.
- **Implementation:** 100% of review search and dynamic filters bind values using parameterized SQLite placeholders (`?`).
- **Audit Verification:** Tested against 5 injection payloads (`' OR '1'='1`, `'; DROP TABLE reviews; --`, `UNION SELECT`). Database tables remained fully intact with zero syntax exceptions.

### 2.2 Cross-Site Scripting (XSS) Prevention
- **Rule:** All untrusted customer review text, review titles, and verbatim quotes must be HTML-escaped before interpolation into Streamlit's `unsafe_allow_html=True` markdown containers.
- **Implementation:** `html.escape(str(text))` applied across `review_explorer_ui.py`, `ai_evidence_log_ui.py`, and `opportunity_detail.py`.
- **Audit Verification:** Tested against `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>`, `<svg/onload=alert('xss')>`, and `<a href='javascript:...'>`. All angle brackets and quotes escaped safely.

### 2.3 Path Traversal Prevention
- **Rule:** Export endpoints must sanitize user-supplied file names to prevent reading or writing outside approved directories.
- **Implementation:** Path separators normalized via `path.replace('\\', '/')` and sanitized using `os.path.basename()`.
- **Audit Verification:** Tested against `../../etc/passwd`, `../../../etc/shadow`, and Windows traversal paths. All neutralized safely.

---

## 3. Privacy, Author Anonymity & Data Retention

### 3.1 PII Scrubbing Rules (`core/csv_validator.py`)
- Disallowed author identification headers (`user_name`, `author_name`, `email`, `phone_number`) are permanently stripped at ingestion.
- Inline text scrubbing automatically redacts sensitive Indian personal identifiers:
  - Phone numbers: `(\+91[\-\s]?)?[6-9]\d{9}` -> `[PHONE_REDACTED]`
  - Email addresses: `[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+` -> `[EMAIL_REDACTED]`
  - PAN cards: `[A-Z]{5}[0-9]{4}[A-Z]{1}` -> `[PAN_REDACTED]`
  - UPI IDs: `[\w\.\-_]+@[\w]+` -> `[UPI_REDACTED]`
- **Audit Verification:** Zero unredacted PII patterns detected across all 3,798 stored reviews and 21 published export artifacts.

### 3.2 Demographic Neutrality
- Reviewer demographic dimensions (gender, age, ethnicity, religion, income band) are absent from the canonical schema.
- System strictly defaults demographic attributes to `UNKNOWN` and prohibits ML inferencing of reviewer personal attributes from text.

---

## 4. Database & Secret Hygiene

- **Database File Permissions:** `growww_discovery.db` set to `0o644` (rw-r--r--, non-world-writable).
- **Referential Integrity:** `PRAGMA foreign_keys = ON;` enforced on all SQLite connection initializers. Verified 0 foreign key check violations.
- **Quarantine Enforcement:** 8 synthetic demo reviews strictly isolated; verified 0 presence in production analytics or AI evidence logs.
- **Secret Management:** Automated repository scan confirmed zero API keys, JWT tokens, AWS credentials, or private keys committed to source control.
