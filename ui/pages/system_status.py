"""
Page 5: System Status & Diagnostic Health Monitor.
Verifies database integrity, YAML configuration health, and source route permission gates.
"""
import streamlit as st
import sqlite3
import pandas as pd
from core.database_manager import get_database_manager
from core.config_loader import get_config_loader
from ui.navigation import render_header

def render():
    render_header(
        "System Diagnostics & Governance Status",
        "Live telemetry on local database connections, configuration integrity, and data source permission gates."
    )

    db_manager = get_database_manager()
    config_loader = get_config_loader()

    # 1. Database Health Check
    st.subheader("1. Local Database Subsystem")
    health = db_manager.check_health()
    
    col_db1, col_db2, col_db3, col_db4, col_db5, col_db6 = st.columns(6)
    with col_db1:
        st.metric("Database Status", health["status"])
    with col_db2:
        st.metric("Engine", f"SQLite {sqlite3.sqlite_version}")
    with col_db3:
        st.metric("Registered Apps", health["registered_apps"])
    with col_db4:
        st.metric("Genuine Reviews", health.get("genuine_reviews", 0))
    with col_db5:
        st.metric("Synthetic Demo", health.get("demo_reviews", 0))
    with col_db6:
        st.metric("Total Records", health.get("total_records", 0))

    st.caption(f"**Database Storage File:** `{health['database_path']}`")

    st.markdown("---")

    # 2. Configuration Validation Status
    st.subheader("2. Configuration Manifest Health")
    configs_to_check = [
        ("apps.yml", "Candidate App Registry", config_loader.get_apps_config),
        ("source_access.yml", "Source Access & Permission Register", config_loader.get_source_access_config),
        ("review_taxonomy.yml", "Multilingual Classification Taxonomy", config_loader.get_review_taxonomy_config)
    ]

    cfg_rows = []
    for fname, desc, getter in configs_to_check:
        try:
            data = getter()
            cfg_rows.append({
                "Configuration File": fname,
                "Description": desc,
                "Status": "VALID ✅",
                "Details": f"Loaded {len(data)} top-level sections"
            })
        except Exception as exc:
            cfg_rows.append({
                "Configuration File": fname,
                "Description": desc,
                "Status": "ERROR ❌",
                "Details": str(exc)
            })

    st.dataframe(pd.DataFrame(cfg_rows), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 3. Source Access & Permission Gate Status (Phase 2 Two-Store Matrix)
    st.subheader("3. Data Collection Route Permission Gates (Phase 2 Source Matrix)")
    st.caption("Policy Invariant: Every connector is governed by explicit permission states. Scraping competitor Google Play HTML is strictly forbidden.")

    all_sources = config_loader.get_all_sources()
    db_sources = {s["source_id"]: s for s in db_manager.source_repo.list_all()}
    
    source_table = []
    for src in all_sources:
        sid = src.get("source_id")
        db_s = db_sources.get(sid, {})
        status_label = src.get("permission_status")
        tech_avail = src.get("technical_availability")
        
        # Check if enabled dynamically in DB or YAML
        is_enabled = bool(db_s.get("enabled", src.get("enabled", False)))
        route_code = src.get("route_code") or sid

        if status_label == "REJECTED":
            op_state = "🛑 REJECTED (Paywalled)"
        elif status_label == "UNAVAILABLE":
            op_state = "🔒 LOCKED (Owner Auth Required)"
        elif is_enabled:
            op_state = "🟢 ENABLED (Active Ingestion)"
        else:
            op_state = "⚪ READY (Admin Gated)"

        source_table.append({
            "Route": route_code,
            "Route ID": sid,
            "Route Name": src.get("source_name"),
            "Store": src.get("source_family", "").replace("_", " ").title(),
            "Method": src.get("collection_method"),
            "Technical Status": tech_avail,
            "Permission Status": status_label,
            "Operational State": op_state,
            "Last Verified": src.get("last_verification_date") or "-"
        })

    st.dataframe(pd.DataFrame(source_table), use_container_width=True, hide_index=True)

    # Interactive Route Activation Controls
    with st.expander("⚙️ Manage Route Activation (SQLite In-Memory / Local DB)"):
        st.caption("Administrators may dynamically enable or disable approved collection routes in the database:")
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            route_a = db_sources.get("apple_app_store_public_rss", {})
            a_enabled = bool(route_a.get("enabled", 0))
            new_a = st.toggle("Enable Route A (Apple RSS)", value=a_enabled, key="toggle_route_a")
            if new_a != a_enabled:
                db_manager.source_repo.set_enabled("apple_app_store_public_rss", new_a)
                st.success(f"Route A set to {'ENABLED' if new_a else 'DISABLED'} in database.")
                st.rerun()

        with col_ctrl2:
            route_b = db_sources.get("manual_review_csv_import", {})
            b_enabled = bool(route_b.get("enabled", 0))
            new_b = st.toggle("Enable Route B (Manual CSV)", value=b_enabled, key="toggle_route_b")
            if new_b != b_enabled:
                db_manager.source_repo.set_enabled("manual_review_csv_import", new_b)
                st.success(f"Route B set to {'ENABLED' if new_b else 'DISABLED'} in database.")
                st.rerun()

    # Governance Notice regarding AppFollow
    st.warning(
        "**Governance Sign-off:** AppFollow has been permanently rejected and disabled across all runtime components. "
        "Route A (Apple RSS) and Route B (Google Play Manual CSV) constitute the complete Phase 2 Two-Store Ingestion MVP."
    )

    st.markdown("---")

    # 4. Version & Build Information
    st.subheader("4. Build & Environment Information")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown("**Application:** Growww Discovery Engine")
        st.markdown("**Version:** `1.2.0-phase2 (Two-Store Ingestion MVP)`")
    with b2:
        st.markdown("**Python Runtime:** `3.9+`")
        st.markdown("**UI Framework:** `Streamlit 1.50`")
    with b3:
        st.markdown("**Active Governance Policy:** `1.0.0`")
        st.markdown("**Primary Case Study:** `Groww (com.nextbillion.groww)`")
