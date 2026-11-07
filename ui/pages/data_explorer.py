"""
Page 4: Data Explorer for Growww Discovery Engine.
Provides interactive browsing, search, and multidimensional filtering over canonical reviews.
"""
import streamlit as st
import pandas as pd
from database.connection import get_db
from database.repositories import ReviewRepository
from services.app_registry_service import get_app_registry_service
from ui.navigation import render_header

def render():
    render_header(
        "Canonical Review Explorer",
        "Inspect, search, and filter sanitized public customer reviews across Indian investment applications."
    )

    db = get_db()
    review_repo = ReviewRepository(db)
    app_service = get_app_registry_service()
    registered_apps = app_service.get_all_apps()

    # Filter Sidebar / Controls
    st.subheader("Filter & Search Criteria")
    f1, f2, f3, f4 = st.columns(4)

    app_choices = [("ALL", "All Applications")] + [(a["internal_app_id"], a["app_name"]) for a in registered_apps]
    with f1:
        selected_app = st.selectbox(
            "Filter by App",
            options=[c[0] for c in app_choices],
            format_func=lambda x: next(c[1] for c in app_choices if c[0] == x)
        )

    with f2:
        selected_store = st.selectbox(
            "Filter by Store",
            options=["ALL", "apple_app_store", "google_play"],
            format_func=lambda x: {"ALL": "All Platforms", "apple_app_store": "Apple App Store", "google_play": "Google Play"}.get(x, x)
        )

    with f3:
        selected_rating = st.selectbox(
            "Filter by Rating",
            options=["ALL", 1, 2, 3, 4, 5],
            format_func=lambda x: "All Star Ratings" if x == "ALL" else f"{x} Stars"
        )

    with f4:
        selected_eligibility = st.selectbox(
            "Filter by Eligibility",
            options=["ALL", "ELIGIBLE", "PENDING", "SYNTHETIC_DEMO", "REJECTED"],
            format_func=lambda x: "All Categories" if x == "ALL" else x
        )

    search_kw = st.text_input("🔍 Search within Review Text or Title", placeholder="e.g. autopay, bounce, mandate, KYC, Hindi text")

    # Pagination controls
    p1, p2, p3 = st.columns([1, 1, 3])
    with p1:
        page_size = st.selectbox("Page Size", options=[15, 30, 50, 100], index=0)
    
    # Query database
    app_arg = None if selected_app == "ALL" else selected_app
    store_arg = None if selected_store == "ALL" else selected_store
    rating_arg = None if selected_rating == "ALL" else int(selected_rating)
    elig_arg = None if selected_eligibility == "ALL" else selected_eligibility

    reviews, total_count = review_repo.query_reviews(
        app_id=app_arg,
        store=store_arg,
        rating=rating_arg,
        eligibility=elig_arg,
        search_query=search_kw if search_kw.strip() else None,
        limit=page_size,
        offset=0
    )

    st.markdown(f"**Found {total_count} matching reviews.** (Displaying {min(len(reviews), page_size)} items)")

    if not reviews:
        st.info("No reviews match your current filter selections. If database is empty, load demo records from Overview or upload a CSV in Data Import.")
        return

    # Render table
    table_rows = []
    for r in reviews:
        table_rows.append({
            "App": r.get("app_name") or r.get("app_id"),
            "Store": "Apple" if r.get("store") == "apple_app_store" else "Google Play",
            "Rating": f"{'⭐' * int(r['star_rating'])} ({r['star_rating']})",
            "Date": str(r.get("review_created_at"))[:10],
            "Version": r.get("app_version") or "-",
            "Eligibility": r.get("eligibility_status"),
            "Title": r.get("review_title") or "(No Title)",
            "Snippet": (r.get("review_text")[:100] + "...") if len(r.get("review_text", "")) > 100 else r.get("review_text")
        })

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    # Detailed Review Inspector
    st.markdown("##### Detailed Review Text & Provenance Inspector")
    for r in reviews:
        stars = "⭐" * int(r['star_rating'])
        is_demo = r.get("eligibility_status") == "SYNTHETIC_DEMO"
        header = f"{'🧪 [DEMO] ' if is_demo else ''}{r.get('app_name')} | {stars} | {str(r.get('review_created_at'))[:10]} | {r.get('review_title') or 'Review'}"
        
        with st.expander(header):
            st.markdown(f"**Review Content:**")
            st.markdown(f"> *{r['review_text']}*")

            col_meta1, col_meta2 = st.columns(2)
            with col_meta1:
                st.caption(f"**Evidence ID:** `{r.get('evidence_id')}`")
                st.caption(f"**Store:** `{r.get('store')}` (Storefront: `{r.get('storefront')}`)")
                st.caption(f"**Version:** `{r.get('app_version') or 'N/A'}`")
            with col_meta2:
                st.caption(f"**Eligibility Status:** `{r.get('eligibility_status')}`")
                st.caption(f"**Redaction Status:** `{r.get('redaction_status')}`")
                st.caption(f"**Collection Method:** `{r.get('collection_method')}`")
