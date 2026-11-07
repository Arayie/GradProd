"""
Page 2: Application Registry for Growww Discovery Engine.
Displays registered target and competitor applications with live database/config synchronization.
"""
import streamlit as st
import pandas as pd
from services.app_registry_service import get_app_registry_service
from ui.navigation import render_header

def render():
    render_header(
        "Candidate Application Registry",
        "Official verified listings, package names, Apple App IDs, and storefront availability in India."
    )

    registry_service = get_app_registry_service()
    stats = registry_service.get_app_stats()

    # Summary Stats Row
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("Total Applications", stats["total_apps"])
    with s2:
        st.metric("Primary Research Target", stats["primary_apps"])
    with s3:
        st.metric("Competitor Benchmarks", stats["competitor_apps"])
    with s4:
        st.metric("Store Verification", "100% India (IN)")

    st.markdown("---")

    # Search & Filter Controls
    col_search, col_role, col_store = st.columns([2, 1, 1])
    with col_search:
        search_query = st.text_input("🔍 Search by App, Developer, or Package Name", placeholder="e.g. Zerodha, com.nextbillion, Groww")
    with col_role:
        role_filter = st.selectbox(
            "Filter by Role",
            options=["ALL", "primary_case_study", "competitor_mutual_funds", "competitor_discount_broker", "competitor_full_service_broker", "competitor_wealth_tracker", "competitor_ecosystem"],
            format_func=lambda x: "All Roles" if x == "ALL" else x.replace("_", " ").title()
        )
    with col_store:
        store_filter = st.selectbox(
            "Filter by Storefront",
            options=["ALL", "APPLE_ONLY", "GOOGLE_PLAY_ONLY"],
            format_func=lambda x: {"ALL": "All Platforms", "APPLE_ONLY": "Apple App Store", "GOOGLE_PLAY_ONLY": "Google Play Store"}.get(x, x)
        )

    # Fetch and filter
    apps = registry_service.search_apps(query=search_query, store_filter=store_filter, role_filter=role_filter)

    if not apps:
        st.warning("No applications matched your search criteria.")
        return

    # Render formatted table
    table_data = []
    for app in apps:
        table_data.append({
            "App Name": app.get("app_name"),
            "Role": app.get("app_role", "").replace("_", " ").title(),
            "Developer": app.get("developer_name"),
            "Apple App ID": app.get("apple_app_id") or "N/A",
            "Google Play Package": app.get("google_play_package") or "N/A",
            "Storefront": app.get("storefront", "IN"),
            "Status": app.get("verification_status", "VERIFIED")
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detailed expandable cards for deep inspection
    st.markdown("##### Detailed App Listing Metadata")
    for app in apps:
        is_primary = app.get("app_role") == "primary_case_study"
        label = f"{'⭐ PRIMARY: ' if is_primary else ''}{app.get('app_name')} ({app.get('internal_app_id')})"
        with st.expander(label, expanded=is_primary):
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(f"**Developer:** {app.get('developer_name')}")
                st.markdown(f"**Internal ID:** `{app.get('internal_app_id')}`")
                st.markdown(f"**Role:** `{app.get('app_role')}`")
                st.markdown(f"**Storefront:** {app.get('storefront', 'IN')}")
            with col_r:
                apple_id = app.get("apple_app_id")
                apple_url = app.get("apple_listing_url")
                if apple_id and apple_url:
                    st.markdown(f"**Apple Store:** [`id{apple_id}`]({apple_url})")
                else:
                    st.markdown(f"**Apple Store:** `{apple_id or 'None'}`")

                play_pkg = app.get("google_play_package")
                play_url = app.get("google_play_listing_url")
                if play_pkg and play_url:
                    st.markdown(f"**Google Play:** [`{play_pkg}`]({play_url})")
                else:
                    st.markdown(f"**Google Play:** `{play_pkg or 'None'}`")

                st.markdown(f"**Verification:** `{app.get('verification_status')}`")
