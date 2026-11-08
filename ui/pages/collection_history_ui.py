"""
Collection History and Connector Audit (Page 3 - Phase 6)
Audit log for automated and manual review ingestion runs with filtering and diagnostic inspection.
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
from core.database_manager import get_database_manager
from core.auth import AuthService
from ui.navigation import render_header

def render():
    render_header(
        "Ingestion Runs & History",
        "Historical audit trail of all automated batch collection and manual CSV import sessions."
    )

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT app_id FROM ingestion_runs ORDER BY app_id")
        apps = ["ALL"] + [r[0] for r in cursor.fetchall()]
        sel_app = st.selectbox("Application", options=apps)
    with col2:
        cursor.execute("SELECT DISTINCT run_status FROM ingestion_runs ORDER BY run_status")
        statuses = ["ALL"] + [r[0] for r in cursor.fetchall()]
        sel_status = st.selectbox("Run Status", options=statuses)
    with col3:
        cursor.execute("SELECT DISTINCT collection_method FROM ingestion_runs ORDER BY collection_method")
        methods = ["ALL"] + [r[0] for r in cursor.fetchall()]
        sel_method = st.selectbox("Collection Method", options=methods)

    query = "SELECT * FROM ingestion_runs WHERE 1=1"
    params = []
    if sel_app != "ALL":
        query += " AND app_id = ?"
        params.append(sel_app)
    if sel_status != "ALL":
        query += " AND run_status = ?"
        params.append(sel_status)
    if sel_method != "ALL":
        query += " AND collection_method = ?"
        params.append(sel_method)

    query += " ORDER BY started_at DESC"
    df = pd.read_sql_query(query, conn, params=params)

    st.markdown(f"**Found {len(df)} Ingestion Runs**")

    if not df.empty:
        # Display table
        table_cols = [
            "run_id", "app_id", "store", "collection_method", "started_at",
            "received_count", "accepted_count", "duplicate_count", "rejected_count", "run_status"
        ]
        st.dataframe(df[table_cols], use_container_width=True)

        # CSV Download if permitted
        if AuthService.can_export_reports():
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Export Run History (CSV)",
                data=csv,
                file_name="groww_ingestion_runs_history.csv",
                mime="text/csv",
            )

        st.markdown("---")
        st.subheader("Run Diagnostic Inspector")
        sel_run_id = st.selectbox("Select Run ID to Inspect", options=df["run_id"].tolist())
        run_record = df[df["run_id"] == sel_run_id].iloc[0]

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.write(f"**Application:** {run_record['app_id']}")
            st.write(f"**Store:** {run_record['store']}")
            st.write(f"**Collection Method:** {run_record['collection_method']}")
            st.write(f"**Start Time:** {run_record['started_at']}")
            st.write(f"**Completion Time:** {run_record['completed_at']}")
        with col_r2:
            st.write(f"**Reviews Received:** {run_record['received_count']}")
            st.write(f"**Accepted Records:** {run_record['accepted_count']}")
            st.write(f"**Duplicates Detected:** {run_record['duplicate_count']}")
            st.write(f"**Rejected Records:** {run_record['rejected_count']}")
            st.write(f"**Run Status:** `{run_record['run_status']}`")

        if run_record["error_summary"]:
            st.error(f"Error Diagnostic: {run_record['error_summary']}")
    else:
        st.info("No ingestion runs recorded matching filter criteria.")

    conn.close()
