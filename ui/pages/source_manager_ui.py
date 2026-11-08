"""
Source Manager and Route Governance (Page 2 - Phase 6)
Configures and monitors public and owner review collection routes under strict free-tier governance.
"""

import streamlit as st
import pandas as pd
import sqlite3
import yaml
import os
from core.database_manager import get_database_manager
from core.auth import AuthService

def render():
    st.markdown("""
        <div>
            <div class="groww-brand-title">GROWWW</div>
            <div class="groww-brand-subtitle">AI-Powered Investor Discovery Engine • Source Manager</div>
            <h2 style="color: #0F172A; font-weight: 700; margin-top: 0.5rem; margin-bottom: 0.2rem;">Source Configuration & Route Governance</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem;">
                Monitoring approved free-tier collection channels across Apple App Store RSS and verified Google Play CSV imports.
            </p>
        </div>
    """, unsafe_allow_html=True)

    db_mgr = get_database_manager()
    conn = db_mgr.get_connection()
    cursor = conn.cursor()

    is_admin = AuthService.can_manage_sources()
    if not is_admin:
        st.info("🔒 Source configuration changes require ADMIN role permissions. Currently operating in view-only inspection mode.")

    # Tabs for Sources
    tab_apple, tab_google, tab_routes = st.tabs(["Apple App Store RSS (Approved)", "Google Play (Manual Import)", "Source Route Registry"])

    with tab_apple:
        st.subheader("Apple App Store India (`IN`) Public Feeds")
        st.caption("Active free-tier syndication channel. Maximum 500 reviews per application without authentication credentials.")

        query = """
        SELECT 
            a.internal_app_id, a.app_name, a.apple_app_id, a.apple_listing_url,
            COUNT(r.id) as reviews_stored,
            MIN(r.review_created_at) as oldest_review,
            MAX(r.review_created_at) as newest_review
        FROM apps a
        LEFT JOIN reviews r ON a.internal_app_id = r.app_id AND r.store = 'apple_app_store'
        GROUP BY a.internal_app_id, a.app_name, a.apple_app_id, a.apple_listing_url
        ORDER BY reviews_stored DESC
        """
        cursor.execute(query)
        apple_data = cursor.fetchall()

        apple_rows = []
        for r in apple_data:
            apple_rows.append({
                "App ID": r["internal_app_id"],
                "Application Name": r["app_name"],
                "Apple ID": r["apple_app_id"],
                "Reviews Stored": r["reviews_stored"],
                "Oldest Review": str(r["oldest_review"])[:10] if r["oldest_review"] else "N/A",
                "Newest Review": str(r["newest_review"])[:10] if r["newest_review"] else "N/A",
                "Permission Status": "APPROVED",
                "Feed State": "ONLINE",
            })
        st.dataframe(pd.DataFrame(apple_rows), use_container_width=True)

    with tab_google:
        st.subheader("Google Play Store Channel Status")
        st.caption("Commercial scrapers (AppFollow) are permanently excluded. Operating on verified manual CSV imports.")

        cursor.execute("SELECT internal_app_id, app_name, google_play_package FROM apps")
        gplay_data = cursor.fetchall()
        gplay_rows = []
        for r in gplay_data:
            gplay_rows.append({
                "App ID": r["internal_app_id"],
                "Application Name": r["app_name"],
                "Package Name": r["google_play_package"],
                "Manual CSV Route": "ENABLED",
                "Owner API": "UNAVAILABLE",
                "Permission Status": "APPROVED_FOR_CSV",
            })
        st.dataframe(pd.DataFrame(gplay_rows), use_container_width=True)

    with tab_routes:
        st.subheader("Registered Source Routes")
        routes_df = pd.read_sql_query("SELECT source_id, source_name, store, collection_method, permission_status, enabled FROM source_routes", conn)
        st.dataframe(routes_df, use_container_width=True)

        if is_admin:
            st.markdown("### Administrator Route Controls")
            sel_route = st.selectbox("Select Route to Configure", options=routes_df["source_id"].tolist())
            route_info = routes_df[routes_df["source_id"] == sel_route].iloc[0]

            new_enabled = st.toggle("Enable Route for Ingestion", value=bool(route_info["enabled"]))
            if st.button("Apply Route Configuration"):
                cursor.execute("UPDATE source_routes SET enabled = ? WHERE source_id = ?", (1 if new_enabled else 0, sel_route))
                conn.commit()
                st.success(f"Route '{sel_route}' status updated to {'ENABLED' if new_enabled else 'DISABLED'}!")
                st.rerun()

    conn.close()
