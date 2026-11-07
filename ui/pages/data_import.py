"""
Page 3: Two-Store Ingestion MVP Interface for Growww Discovery Engine.
Provides unified collection workflows:
- Route A: Apple App Store Public RSS Automated Collector
- Route B: Google Play Manual CSV Import (Competitor & Fallback)
- Route C & D: Google Play Developer API & Console CSV (Owner Stubs)
- Run History, Audit Logs, and Checkpoint Management
"""
import time
import os
import streamlit as st
import pandas as pd
from typing import Dict, Any

from core.database_manager import get_database_manager
from core.config_loader import get_config_loader
from core.csv_validator import REQUIRED_COLUMNS, OPTIONAL_COLUMNS
from services.import_service import get_import_service
from services.app_registry_service import get_app_registry_service
from services.ingestion_service import get_common_ingestion_service
from ui.navigation import render_header

def render():
    render_header(
        "Two-Store Ingestion Interface (Phase 2 MVP)",
        "Unified public review collection engine for Apple App Store (RSS) and Google Play (Sanitized CSV)."
    )

    db_manager = get_database_manager()
    config_loader = get_config_loader()
    ingestion_service = get_common_ingestion_service()
    app_service = get_app_registry_service()
    import_service = get_import_service()

    registered_apps = app_service.get_all_apps()
    app_lookup = {app["internal_app_id"]: app for app in registered_apps}

    tab_apple, tab_csv, tab_owner, tab_history = st.tabs([
        "🍏 Route A: Apple App Store RSS",
        "📥 Route B: Manual CSV Import",
        "🔒 Route C & D: Owner APIs (Stubs)",
        "📜 Run History & Checkpoints"
    ])

    # =========================================================================
    # TAB 1: Route A - Apple App Store RSS
    # =========================================================================
    with tab_apple:
        st.subheader("Route A: Automated Apple Customer Reviews RSS Feed")
        st.markdown(
            "Collects public reviews syndication from the official Apple iTunes RSS endpoint for India (`storefront: IN`). "
            "Enforces a 10-page / 500-review ceiling, rate-limit backoff, author PII stripping, and checkpoint deduplication."
        )

        col_a1, col_a2 = st.columns([2, 1])

        apple_apps = [a for a in registered_apps if a.get("apple_app_id")]
        app_names_apple = {a["internal_app_id"]: f"{a['app_name']} (App ID: {a['apple_app_id']})" for a in apple_apps}

        with col_a1:
            selected_apple_app = st.selectbox(
                "Select Candidate Application",
                options=list(app_names_apple.keys()),
                format_func=lambda x: app_names_apple.get(x, x),
                key="apple_rss_app_select"
            )

        with col_a2:
            max_pages = st.slider(
                "Max RSS Pages to Crawl (50 rev/page)",
                min_value=1,
                max_value=10,
                value=10,
                step=1,
                help="Apple imposes a strict 10-page hard ceiling (500 reviews max). Page 11 returns HTTP 400."
            )

        # Checkpoint Status Display
        active_checkpoint = db_manager.checkpoint_repo.get_checkpoint(
            app_id=selected_apple_app,
            storefront="IN",
            collection_method="apple_app_store_rss"
        )

        col_chk, col_btn_reset = st.columns([3, 1])
        with col_chk:
            if active_checkpoint:
                st.info(
                    f"📌 **Active Checkpoint Found:** Last collection retrieved page "
                    f"**{active_checkpoint.get('last_successful_page')}** on `{active_checkpoint.get('last_retrieval_timestamp')}`. "
                    f"Top Review ID: `{active_checkpoint.get('last_seen_review_id')}`. "
                    f"Subsequent runs will stop incrementally when encountering existing reviews."
                )
            else:
                st.caption("ℹ️ No prior collection checkpoint found for this app. Will perform initial full crawl.")

        with col_btn_reset:
            if active_checkpoint:
                if st.button("🔄 Reset Checkpoint", help="Clears the checkpoint to force a complete re-fetch from page 1"):
                    db_manager.checkpoint_repo.reset_checkpoint(
                        app_id=selected_apple_app,
                        storefront="IN",
                        collection_method="apple_app_store_rss"
                    )
                    st.success("Checkpoint reset! Next run will start from page 1.")
                    st.rerun()

        # Ingestion Trigger Buttons
        if "is_collecting" not in st.session_state:
            st.session_state.is_collecting = False

        chk_col1, chk_col2 = st.columns([2, 1])
        with chk_col1:
            use_incremental = st.checkbox(
                "Incremental mode: Stop when previously seen reviews are reached",
                value=False,
                key="apple_rss_incremental_toggle",
                help="When unchecked (default for backfill), crawls up to the specified max pages and deduplicates against the database."
            )

        c_trigger1, c_trigger2 = st.columns([1.5, 2])
        with c_trigger1:
            start_btn = st.button(
                "🚀 Collect Selected App",
                type="primary",
                disabled=st.session_state.is_collecting,
                key="btn_start_apple_rss"
            )
        with c_trigger2:
            start_all_btn = st.button(
                "⚡ Ingest All 8 Applications",
                type="secondary",
                disabled=st.session_state.is_collecting,
                key="btn_start_all_apple_rss",
                help="Sequentially crawls Apple RSS feeds for all 8 candidate applications."
            )

        if start_btn:
            st.session_state.is_collecting = True
            with st.spinner(f"Connecting to Apple RSS feed for {app_lookup[selected_apple_app]['app_name']}..."):
                try:
                    result = ingestion_service.ingest_apple_rss(
                        app_id=selected_apple_app,
                        max_pages=max_pages,
                        stop_on_checkpoint=use_incremental,
                        admin_override=True
                    )

                    st.session_state.is_collecting = False
                    st.success(f"🎉 Ingestion Run Complete! Run ID: `{result['run_id']}` (Status: {result['status']})")

                    # Metric Summary
                    m1, m2, m3, m4, m5 = st.columns(5)
                    with m1:
                        st.metric("Pages Retrieved", f"{result['pages_retrieved']} / {max_pages}")
                    with m2:
                        st.metric("Reviews Fetched", result["reviews_received"])
                    with m3:
                        st.metric("New Inserted", result["accepted_count"])
                    with m4:
                        st.metric("Duplicates Skipped", result["duplicate_count"])
                    with m5:
                        st.metric("Coverage (Days)", f"{result['coverage_duration_days']} d")

                    # Date Range Details
                    if result["newest_review_date"] or result["oldest_review_date"]:
                        st.markdown(
                            f"**Coverage Window:** `{result['oldest_review_date']}` to `{result['newest_review_date']}` "
                            f"({result['coverage_duration_days']} days spanned)"
                        )

                    if result["hit_checkpoint"]:
                        st.info("🛑 Checkpoint boundary reached: collection stopped early because previously seen reviews were encountered.")

                    if result["errors"]:
                        with st.expander(f"⚠️ {len(result['errors'])} HTTP Warnings / Notices"):
                            for err in result["errors"]:
                                st.warning(err)

                    # Export notices
                    st.caption("Logs automatically synced to `outputs/ingestion_runs.csv` and `outputs/collection_errors.csv`.")

                except Exception as e:
                    st.session_state.is_collecting = False
                    st.error(f"❌ Collection failed: {str(e)}")

        if start_all_btn:
            st.session_state.is_collecting = True
            with st.spinner("Executing batch Apple RSS ingestion across all 8 applications..."):
                try:
                    batch_res = ingestion_service.ingest_all_apple_apps(
                        max_pages=max_pages,
                        stop_on_checkpoint=use_incremental,
                        admin_override=True,
                        delay_between_apps=0.5
                    )
                    st.session_state.is_collecting = False
                    st.success(
                        f"🎉 Batch Ingestion Finished! Processed {batch_res['total_apps']} applications: "
                        f"{batch_res['total_received']} reviews fetched, {batch_res['total_accepted']} new inserted, "
                        f"{batch_res['total_duplicates']} duplicates skipped."
                    )

                    # Show summary table
                    rows = []
                    for a_id, summary in batch_res["app_summaries"].items():
                        rows.append({
                            "App": a_id,
                            "Status": summary.get("status", "UNKNOWN"),
                            "Pages": summary.get("pages_retrieved", 0),
                            "Fetched": summary.get("reviews_received", 0),
                            "Inserted": summary.get("accepted_count", 0),
                            "Duplicates": summary.get("duplicate_count", 0),
                            "Coverage Days": summary.get("coverage_duration_days", 0),
                            "Date Range": f"{summary.get('oldest_review_date', '')[:10]} - {summary.get('newest_review_date', '')[:10]}"
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

                    if batch_res.get("errors"):
                        with st.expander(f"⚠️ {len(batch_res['errors'])} Batch Warnings / Notices"):
                            for err in batch_res["errors"]:
                                st.warning(err)
                except Exception as e:
                    st.session_state.is_collecting = False
                    st.error(f"❌ Batch collection failed: {str(e)}")

    # =========================================================================
    # TAB 2: Route B - Manual CSV Import
    # =========================================================================
    with tab_csv:
        st.subheader("Route B: Google Play & Manual CSV Import")
        st.markdown(
            "Accepts customer review datasets for Google Play competitor analysis and historical backfills. "
            "Enforces strict data provenance confirmation, schema verification, and Indian PII regex redaction."
        )

        # Step 1: Governance & Scope Context
        st.markdown("##### 1. Target Application & Legal Provenance")
        c1, c2, c3 = st.columns(3)

        app_options_csv = {app["internal_app_id"]: f"{app['app_name']} ({app['internal_app_id']})" for app in registered_apps}
        with c1:
            selected_csv_app = st.selectbox(
                "Target Application",
                options=list(app_options_csv.keys()),
                format_func=lambda x: app_options_csv.get(x, x),
                key="csv_target_app"
            )

        with c2:
            selected_store = st.selectbox(
                "Platform Storefront",
                options=["google_play", "apple_app_store"],
                format_func=lambda x: "Google Play Store (Route B)" if x == "google_play" else "Apple App Store",
                key="csv_store_select"
            )

        with c3:
            permission_status = st.selectbox(
                "Permission Status",
                options=["APPROVED", "PENDING_VERIFICATION", "REJECTED"],
                index=0,
                help="Select APPROVED only if the dataset has verified research eligibility."
            )

        source_description = st.text_input(
            "Data Provenance / Source Description",
            placeholder="e.g. Kaggle Public Stock Trading App Reviews Archive 2026 / Internal Customer Feedback Dump",
            key="csv_source_desc"
        )

        # Step 2: File Upload
        st.markdown("##### 2. Upload Customer Review CSV")
        col_upload, col_template = st.columns([3, 1])
        with col_upload:
            uploaded_file = st.file_uploader(
                "Choose a CSV file",
                type=["csv"],
                help="Must contain review_text, review_date, and rating columns.",
                key="csv_uploader"
            )

        with col_template:
            st.markdown("**Canonical Columns:**")
            st.code(",".join(REQUIRED_COLUMNS + ["review_title", "review_id"]), language="text")

        if uploaded_file:
            # Step 3: Preview & Mapping
            st.markdown("##### 3. CSV Inspection & Column Mapping")
            preview_res = import_service.preview_csv(uploaded_file, nrows=5)

            if not preview_res["success"]:
                st.error(f"Failed to parse uploaded CSV: {preview_res['error']}")
            else:
                df_preview = preview_res["preview_df"]
                inspection = preview_res["inspection"]

                st.markdown(f"**Preview of First {len(df_preview)} Rows (Total File Columns: {len(inspection['columns'])}):**")
                st.dataframe(df_preview, use_container_width=True)

                if inspection["disallowed_columns"]:
                    st.error(
                        f"🚨 **Privacy Violation Detected:** The CSV contains disallowed personal identification column(s): "
                        f"**{', '.join(inspection['disallowed_columns'])}**. "
                        "Our data governance policy forbids ingesting reviewer usernames or contact details. "
                        "Please remove these columns before proceeding."
                    )
                else:
                    st.markdown("###### Verify Column Mappings:")
                    col_names = list(df_preview.columns)
                    mapping_suggestions = inspection.get("mapping_suggestions", {})
                    
                    mapping_inputs = {}
                    m1, m2, m3 = st.columns(3)
                    
                    with m1:
                        default_text_col = next((c for c in col_names if mapping_suggestions.get(c) == "review_text" or c.lower() == "review_text"), col_names[0])
                        mapping_inputs["review_text"] = st.selectbox(
                            "Review Text Column (Required)*",
                            options=col_names,
                            index=col_names.index(default_text_col) if default_text_col in col_names else 0
                        )
                    with m2:
                        default_date_col = next((c for c in col_names if mapping_suggestions.get(c) == "review_date" or c.lower() == "review_date"), col_names[min(1, len(col_names)-1)])
                        mapping_inputs["review_date"] = st.selectbox(
                            "Review Date Column (Required)*",
                            options=col_names,
                            index=col_names.index(default_date_col) if default_date_col in col_names else 0
                        )
                    with m3:
                        default_rating_col = next((c for c in col_names if mapping_suggestions.get(c) == "rating" or c.lower() == "rating"), col_names[min(2, len(col_names)-1)])
                        mapping_inputs["rating"] = st.selectbox(
                            "Star Rating Column (Required)*",
                            options=col_names,
                            index=col_names.index(default_rating_col) if default_rating_col in col_names else 0
                        )

                    with st.expander("Optional Metadata Mappings (Title, Review ID, Version)"):
                        opt_cols = ["None"] + col_names
                        om1, om2, om3 = st.columns(3)
                        with om1:
                            title_match = next((c for c in col_names if mapping_suggestions.get(c) == "review_title" or c.lower() == "review_title"), "None")
                            title_sel = st.selectbox("Review Title", options=opt_cols, index=opt_cols.index(title_match))
                            if title_sel != "None":
                                mapping_inputs["review_title"] = title_sel
                        with om2:
                            id_match = next((c for c in col_names if mapping_suggestions.get(c) == "review_id" or c.lower() == "review_id"), "None")
                            id_sel = st.selectbox("Review ID", options=opt_cols, index=opt_cols.index(id_match))
                            if id_sel != "None":
                                mapping_inputs["review_id"] = id_sel
                        with om3:
                            ver_match = next((c for c in col_names if mapping_suggestions.get(c) == "app_version" or c.lower() == "app_version"), "None")
                            ver_sel = st.selectbox("App Version", options=opt_cols, index=opt_cols.index(ver_match))
                            if ver_sel != "None":
                                mapping_inputs["app_version"] = ver_sel

                    final_column_mapping = {file_col: can_col for can_col, file_col in mapping_inputs.items()}

                    st.markdown("---")
                    st.markdown("##### 4. Legal Provenance Confirmation & Execution")
                    provenance_confirmed = st.checkbox(
                        "I certify that this review dataset originates from legitimate public sources and contains zero confidential customer records.",
                        value=False,
                        key="csv_prov_check"
                    )
                    is_synthetic_toggle = st.checkbox(
                        "Mark as SYNTHETIC_DEMO (Quarantines records from production analytics)",
                        value=False,
                        key="csv_synth_check"
                    )

                    if st.button("🚀 Ingest & Persist Review Dataset (Route B)", type="primary", disabled=not provenance_confirmed):
                        with st.spinner("Validating schema, executing PII regex redaction, and persisting to SQLite..."):
                            try:
                                res = ingestion_service.ingest_manual_csv(
                                    file_or_path=uploaded_file,
                                    filename=uploaded_file.name,
                                    app_id=selected_csv_app,
                                    store=selected_store,
                                    provenance_confirmed=provenance_confirmed,
                                    permission_status=permission_status,
                                    source_description=source_description,
                                    column_mapping=final_column_mapping,
                                    is_synthetic=is_synthetic_toggle
                                )

                                st.success(f"🎉 **Batch Successfully Ingested!** Run ID: `{res['run_id']}` | Batch ID: `{res['batch_id']}`")

                                r1, r2, r3, r4 = st.columns(4)
                                with r1:
                                    st.metric("Total Rows", res["total_rows"])
                                with r2:
                                    st.metric("Accepted & Persisted", res["accepted_count"])
                                with r3:
                                    st.metric("Duplicates Skipped", res["duplicate_count"])
                                with r4:
                                    st.metric("Rejected / Invalid", res["rejected_count"])

                                st.info(f"Research eligibility tag: **`{res['eligibility_status']}`**")

                                if res["rejected_rows_details"]:
                                    with st.expander(f"⚠️ View {len(res['rejected_rows_details'])} Rejected Rows"):
                                        st.dataframe(pd.DataFrame([
                                            {"Row #": rej["row_number"], "Errors": ", ".join(rej["errors"]), "Raw": str(rej["raw_data"])[:120]}
                                            for rej in res["rejected_rows_details"]
                                        ]), use_container_width=True)

                            except Exception as e:
                                st.error(f"❌ Ingestion failed: {e}")

    # =========================================================================
    # TAB 3: Route C & D - Future Owner Stubs
    # =========================================================================
    with tab_owner:
        st.subheader("Route C & D: Google Play Authorized Ingestion Routes")
        st.markdown(
            "These routes are designed for authorized application owners. Under our data governance charter, "
            "Google Play competitor review scraping is **strictly prohibited**."
        )

        col_c, col_d = st.columns(2)

        with col_c:
            st.markdown("#### 🔒 Route C: Android Publisher API v3")
            st.markdown("**Status:** `UNAVAILABLE` (Pending Owner Credentials)")
            st.markdown("""
            - **Scope:** First-party owned applications only.
            - **Authentication:** Google Cloud Service Account with Google Play Developer Console permissions.
            - **Capability:** Automated retrieval of customer reviews and developer responses.
            - **Implementation:** Connector stub `GooglePlayPublisherConnector` is implemented in `ingestion/manual_review_csv.py` ready for credential injection.
            """)
            st.button("🔑 Configure Publisher Credentials", disabled=True, help="Requires authorized Groww Play Console service account credentials.")

        with col_d:
            st.markdown("#### 🔒 Route D: Play Console CSV Export")
            st.markdown("**Status:** `UNAVAILABLE` (Pending Internal Console Dump)")
            st.markdown("""
            - **Scope:** First-party owned applications only.
            - **Authentication:** Manual export downloaded by authorized Play Console administrator.
            - **Capability:** Ingestion of official Google Play bulk review dumps with device metadata.
            - **Implementation:** Parser stub `GooglePlayConsoleCSVParser` is prepared in `ingestion/manual_review_csv.py`.
            """)
            st.button("📁 Upload Official Play Console CSV", disabled=True, help="Activate once authorized Play Console bulk exports are provided.")

        st.markdown("---")
        st.markdown("#### 🛑 Provider Policy Notice: AppFollow")
        st.warning(
            "**AppFollow is PERMANENTLY REJECTED from the active architecture.** "
            "Manual account testing confirmed that competitor review feeds and exports require a paid enterprise subscription ($143+/month). "
            "In adherence to our free-tier research mandate, AppFollow has been removed from active collection."
        )

    # =========================================================================
    # TAB 4: Run History & Checkpoint Audit
    # =========================================================================
    with tab_history:
        st.subheader("Ingestion Run Audit & Checkpoint State")
        st.markdown("Complete audit trail of automated and manual review ingestion sessions across all candidate applications.")

        # Filters for Runs
        hf1, hf2, hf3 = st.columns(3)
        with hf1:
            filter_app = st.selectbox(
                "Filter by App",
                options=["ALL"] + [a["internal_app_id"] for a in registered_apps],
                format_func=lambda x: "All Applications" if x == "ALL" else app_lookup.get(x, {}).get("app_name", x),
                key="hist_filter_app"
            )
        with hf2:
            filter_store = st.selectbox(
                "Filter by Store",
                options=["ALL", "apple_app_store", "google_play"],
                format_func=lambda x: {"ALL": "All Platforms", "apple_app_store": "Apple App Store", "google_play": "Google Play"}.get(x, x),
                key="hist_filter_store"
            )
        with hf3:
            filter_status = st.selectbox(
                "Filter by Run Status",
                options=["ALL", "COMPLETED", "FAILED", "RUNNING"],
                key="hist_filter_status"
            )

        app_arg = None if filter_app == "ALL" else filter_app
        store_arg = None if filter_store == "ALL" else filter_store
        status_arg = None if filter_status == "ALL" else filter_status

        recent_runs = db_manager.run_repo.list_runs(
            app_id=app_arg,
            store=store_arg,
            status=status_arg,
            limit=50
        )

        if recent_runs:
            st.markdown(f"##### Ingestion Run Log ({len(recent_runs)} sessions found)")
            run_table = []
            for r in recent_runs:
                run_table.append({
                    "Run ID": r["run_id"],
                    "Application": r.get("app_name") or r.get("app_id"),
                    "Store": "Apple RSS" if r["store"] == "apple_app_store" else "Google Play",
                    "Method": r["collection_method"],
                    "Status": r["run_status"],
                    "Started At (UTC)": str(r.get("started_at"))[:19],
                    "Received": r.get("received_count", 0),
                    "Accepted": r.get("accepted_count", 0),
                    "Duplicates": r.get("duplicate_count", 0),
                    "Oldest Date": r.get("coverage_start") or "-",
                    "Newest Date": r.get("coverage_end") or "-"
                })
            st.dataframe(pd.DataFrame(run_table), use_container_width=True, hide_index=True)

            # Error Drill-Down Expander
            with st.expander("🔍 Collection Errors Drill-Down"):
                recent_errors = db_manager.run_repo.list_errors(limit=50)
                if recent_errors:
                    err_table = []
                    for e in recent_errors:
                        err_table.append({
                            "Error ID": e["id"],
                            "Run ID": e.get("run_id") or "N/A",
                            "Source": e["source_name"],
                            "Type": e["error_type"],
                            "Message": e["error_message"],
                            "Occurred At": e["occurred_at"],
                            "Status": e["resolution_status"]
                        })
                    st.dataframe(pd.DataFrame(err_table), use_container_width=True, hide_index=True)
                else:
                    st.info("No collection errors recorded in SQLite.")
        else:
            st.info("No ingestion runs recorded matching the selected criteria.")

        # Checkpoints Table
        st.markdown("---")
        st.markdown("##### Persistent Incremental Checkpoints")
        checkpoints = db_manager.checkpoint_repo.list_checkpoints()
        if checkpoints:
            chk_table = []
            for c in checkpoints:
                chk_table.append({
                    "Application": c.get("app_name") or c.get("app_id"),
                    "Storefront": c["storefront"],
                    "Method": c["collection_method"],
                    "Last Successful Page": c.get("last_successful_page"),
                    "Top Review ID": c.get("last_seen_review_id") or "-",
                    "Last Retrieval": str(c.get("last_retrieval_timestamp"))[:19],
                    "Newest Review Date": c.get("newest_review_date") or "-",
                    "Oldest Review Date": c.get("oldest_review_date") or "-",
                    "Total Cumulative": c.get("total_reviews_collected", 0)
                })
            st.dataframe(pd.DataFrame(chk_table), use_container_width=True, hide_index=True)
        else:
            st.caption("No persistent collection checkpoints recorded yet.")
