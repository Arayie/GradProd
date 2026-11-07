"""
Page 1: Overview Dashboard for Growww Discovery Engine.
Displays system metrics, store distribution, app distribution, and import status.
Strictly separates genuine review evidence from quarantined synthetic demonstration data.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.connection import get_db
from database.repositories import ReviewRepository, ImportBatchRepository, IngestionRunRepository
from core.sample_data import SampleDataManager
from ui.navigation import render_header

def render():
    render_header(
        "Executive Research Overview",
        "High-level inventory of candidate applications, genuine review volumes, and data governance status."
    )

    db = get_db()
    review_repo = ReviewRepository(db)
    batch_repo = ImportBatchRepository(db)
    run_repo = IngestionRunRepository(db)
    sample_mgr = SampleDataManager(review_repo)

    metrics = review_repo.get_summary_metrics()

    genuine_count = metrics.get("genuine_reviews", 0)
    total_records = metrics.get("total_records", 0)
    demo_count = metrics.get("demo_reviews", 0)
    eligible_count = metrics.get("eligible_reviews", 0)
    pending_count = metrics.get("pending_reviews", 0)
    rejected_count = metrics.get("rejected_reviews", 0)

    # Demo Banner if synthetic records exist
    if demo_count > 0:
        st.markdown(f"""
            <div class="demo-banner">
                ⚠️ <strong>DEMONSTRATION RECORDS DETECTED:</strong> Exactly <strong>{demo_count}</strong> synthetic sample records 
                are currently stored in the database under <code>SYNTHETIC_DEMO</code>. 
                In strict compliance with our data integrity charter, these records are quarantined and 
                <strong>completely excluded</strong> from genuine review evidence and research analytics.
            </div>
        """, unsafe_allow_html=True)

    # Top KPI Metrics Row 1: App Inventory
    st.subheader("1. Candidate Application Registry")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Candidate Apps", metrics.get("total_apps", 0))
    with c2:
        st.metric("Apple Store Supported", metrics.get("apple_supported", 0))
    with c3:
        st.metric("Google Play Supported", metrics.get("google_play_supported", 0))
    with c4:
        st.metric("Primary Case Study", "Groww (Active)")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Top KPI Metrics Row 2: Review Volume & Governance Status (Strict Separation)
    st.subheader("2. Review Evidence & Data Governance Status")
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric(
            "Total Records Stored",
            total_records,
            help="Total review rows stored in SQLite across genuine, pending, and synthetic categories."
        )
    with k2:
        st.metric(
            "Genuine Review Records",
            genuine_count,
            help="Verified customer reviews collected from public stores. Strictly excludes synthetic data."
        )
    with k3:
        st.metric(
            "Eligible Research Evidence",
            eligible_count,
            help="Genuine reviews with verified legal research provenance and approved permission status."
        )

    k4, k5, k6 = st.columns(3)
    with k4:
        st.metric(
            "Pending Verification",
            pending_count,
            help="Reviews awaiting legal provenance sign-off or data custodian audit."
        )
    with k5:
        st.metric(
            "Rejected Records",
            rejected_count,
            help="Records rejected due to policy violations, unredacted PII, or data corruption."
        )
    with k6:
        st.metric(
            "Synthetic Demo Records",
            demo_count,
            help="Demonstration samples strictly quarantined under SYNTHETIC_DEMO status."
        )

    st.markdown("---")

    # 3. Interactive Visualizations / Empty State Handling
    st.subheader("3. Genuine Research Evidence Analytics")

    if genuine_count == 0:
        st.info(
            "ℹ️ **No Genuine Reviews Ingested Yet (Zero State):**\n\n"
            "The research repository currently contains **0 genuine customer reviews**. "
            "In accordance with our data integrity charter, synthetic demonstration records are quarantined and "
            "cannot be displayed on research distribution charts.\n\n"
            "To ingest genuine public reviews, navigate to **Data Ingestion** and trigger **Route A (Apple App Store RSS)** "
            "or upload a verified **Route B (Google Play Sourced CSV)**."
        )

        # If synthetic records exist, offer inspection in a separate segregated expander
        if demo_count > 0:
            with st.expander(f"🧪 Inspect {demo_count} Quarantined Synthetic Demonstration Records (Audit View)"):
                st.caption("These records are flagged with eligibility_status = 'SYNTHETIC_DEMO' and isolated from research analytics.")
                demo_reviews, _ = review_repo.query_reviews(eligibility="SYNTHETIC_DEMO", limit=50)
                if demo_reviews:
                    df_demo = pd.DataFrame([{
                        "Evidence ID": r["evidence_id"],
                        "App": r.get("app_name") or r.get("app_id"),
                        "Store": r.get("store"),
                        "Rating": f"{r['star_rating']} ⭐",
                        "Source Record ID": r.get("source_record_id"),
                        "Batch / Run ID": r.get("collection_run_id"),
                        "Eligibility": r["eligibility_status"],
                        "Review Text": r["review_text"][:90] + "..." if len(r["review_text"]) > 90 else r["review_text"]
                    } for r in demo_reviews])
                    st.dataframe(df_demo, use_container_width=True, hide_index=True)

    else:
        # Visualizations for Genuine Reviews Only
        col_chart_1, col_chart_2 = st.columns(2)

        with col_chart_1:
            st.markdown("##### Genuine Reviews by Storefront")
            store_dist = metrics.get("store_distribution", {})
            if store_dist:
                labels = [{"apple_app_store": "Apple App Store (Route A)", "google_play": "Google Play (Route B)"}.get(k, k) for k in store_dist.keys()]
                values = list(store_dist.values())
                fig_store = px.pie(
                    names=labels,
                    values=values,
                    hole=0.45,
                    color_discrete_sequence=["#00D09C", "#1E3A2F", "#3B82F6"]
                )
                fig_store.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=280,
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#1E293B", size=12)
                )
                st.plotly_chart(fig_store, use_container_width=True)
            else:
                st.caption("No genuine storefront distribution data.")

        with col_chart_2:
            st.markdown("##### Genuine Star Rating Distribution")
            rating_dist = metrics.get("rating_distribution", {})
            if rating_dist:
                all_ratings = [1, 2, 3, 4, 5]
                counts = [rating_dist.get(r, 0) for r in all_ratings]
                colors = ["#EF4444", "#F97316", "#FBBF24", "#34D399", "#10B981"]
                fig_rating = go.Figure(data=[
                    go.Bar(
                        x=[f"{r} Stars" for r in all_ratings],
                        y=counts,
                        marker_color=colors,
                        text=counts,
                        textposition="auto"
                    )
                ])
                fig_rating.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    height=280,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(title=dict(text="Star Rating", font=dict(color="#1E293B")), tickfont=dict(color="#1E293B")),
                    yaxis=dict(title=dict(text="Review Count", font=dict(color="#1E293B")), tickfont=dict(color="#1E293B"), gridcolor="#E2E8F0"),
                    font=dict(color="#1E293B")
                )
                st.plotly_chart(fig_rating, use_container_width=True)
            else:
                st.caption("No genuine rating distribution data.")

        # App Distribution Chart (Genuine reviews only)
        st.markdown("##### Genuine Reviews Ingested per Candidate Application")
        app_dist = metrics.get("app_distribution", {})
        if app_dist:
            df_app = pd.DataFrame([{"Application": k, "Genuine Reviews": v} for k, v in app_dist.items()])
            fig_app = px.bar(
                df_app,
                x="Genuine Reviews",
                y="Application",
                orientation="h",
                color="Genuine Reviews",
                color_continuous_scale=["#E2E8F0", "#00D09C", "#1E3A2F"]
            )
            fig_app.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickfont=dict(color="#1E293B"), gridcolor="#E2E8F0"),
                yaxis=dict(autorange="reversed", tickfont=dict(color="#1E293B")),
                font=dict(color="#1E293B")
            )
            st.plotly_chart(fig_app, use_container_width=True)

    # 4. Recent Ingestion Sessions
    st.markdown("---")
    st.subheader("4. Recent Ingestion Sessions (Audit Log)")
    recent_runs = run_repo.list_runs(limit=5)
    if recent_runs:
        df_runs = pd.DataFrame(recent_runs)[[
            "run_id", "started_at", "app_name", "store", "collection_method", "received_count", "accepted_count", "run_status"
        ]]
        df_runs.columns = ["Run ID", "Started (UTC)", "App", "Store", "Method", "Received", "Accepted", "Status"]
        st.dataframe(df_runs, use_container_width=True, hide_index=True)
    else:
        st.caption("No automated or manual ingestion sessions logged yet.")

    # 5. Database State & Demo Controls
    st.markdown("---")
    c_btn1, c_btn2, c_btn3 = st.columns([1.5, 1.5, 2])
    with c_btn1:
        if st.button("🔄 Refresh Telemetry"):
            st.rerun()

    with c_btn2:
        if demo_count > 0:
            if st.button("🧹 Clear Demo Records", type="secondary", help="Safely purges only SYNTHETIC_DEMO records"):
                deleted = sample_mgr.clear_demo_records()
                st.success(f"Purged {deleted} synthetic demo records from database.")
                st.rerun()
        else:
            if st.button("🚀 Load Sample Demo Data", help="Loads 35+ realistic synthetic demo records"):
                loaded = sample_mgr.load_demo_records()
                st.success(f"Loaded {loaded} synthetic demo records.")
                st.rerun()

    with c_btn3:
        if genuine_count > 0:
            if st.button("🗑️ Reset Genuine Reviews (Zero State)", help="Removes genuine reviews to test zero state without touching apps or config"):
                with db.get_cursor() as cur:
                    cur.execute("DELETE FROM reviews WHERE eligibility_status != 'SYNTHETIC_DEMO';")
                st.success("Cleared genuine reviews from database.")
                st.rerun()
