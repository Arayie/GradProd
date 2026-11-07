"""
Phase 3 Full Processing Script for Growww Discovery Engine.
Executes standardization, language detection, PII redaction, SIP relevance,
deduplication, retention, and quality grading across all stored reviews.
Generates research datasets and reports.
"""
import os
import sys
import json
import time

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(WORKSPACE_DIR, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from database.connection import get_db
from processing.pipeline import get_processing_pipeline

def main():
    print("=" * 80)
    print("GROWWW INVESTOR DISCOVERY ENGINE - PHASE 3 DATA PROCESSING PIPELINE")
    print("Executing Standardization, Multilingual NLP, PII Minimization, SIP Relevance & Quality")
    print("=" * 80)

    db = get_db()
    pipeline = get_processing_pipeline()

    print("\n[1/3] Processing all review records in SQLite database...")
    t0 = time.time()
    stats = pipeline.process_all_database_records()
    elapsed = time.time() - t0
    print(f"Completed processing {stats['total_processed']} records in {elapsed:.2f}s.")

    print("\nPROCESSING METRICS SUMMARY:")
    print("-" * 50)
    print(f" - Total Records Processed : {stats['total_processed']}")
    print(f" - Research-Eligible       : {stats['eligible']}")
    print(f" - Governance Blocked      : {stats['blocked']}")
    print(f" - High Quality Records    : {stats['high_quality']} ({stats['high_quality']/stats['total_processed']*100:.1f}%)")
    print(f" - Acceptable Quality      : {stats['acceptable_quality']} ({stats['acceptable_quality']/stats['total_processed']*100:.1f}%)")
    print(f" - Low Quality Records     : {stats['low_quality']} ({stats['low_quality']/stats['total_processed']*100:.1f}%)")
    print(f" - Redacted PII Instances  : {stats['redacted_pii_count']}")
    print(f" - Duplicates Detected     : {stats['duplicates_detected']}")

    print("\nSIP RELEVANCE SCREENING:")
    print("-" * 50)
    print(f" - DIRECT SIP Relevant     : {stats['direct_sip_relevant']}")
    print(f" - INDIRECT SIP Relevant   : {stats['indirect_sip_relevant']}")
    print(f" - Total SIP Relevant      : {stats['direct_sip_relevant'] + stats['indirect_sip_relevant']} ({(stats['direct_sip_relevant'] + stats['indirect_sip_relevant'])/stats['total_processed']*100:.1f}%)")
    print(f" - General Investment      : {stats['general_investment']}")
    print(f" - General App Feedback    : {stats['general_app']}")
    print(f" - Irrelevant Reviews      : {stats['irrelevant']}")

    print("\nLANGUAGE DISTRIBUTION:")
    print("-" * 50)
    for lang, count in sorted(stats['languages'].items(), key=lambda x: -x[1]):
        pct = count / stats['total_processed'] * 100
        print(f" - {lang:10s}: {count:5d} ({pct:5.1f}%)")

    print("\n[2/3] Exporting research-ready datasets...")
    export_paths = pipeline.export_research_datasets()
    for name, path in export_paths.items():
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            print(f" - {name:22s}: {path} ({size_kb:.1f} KB)")
        else:
            print(f" - {name:22s}: {path} (Not created)")

    print("\n[3/3] Application-Wise SIP Breakdown Query:")
    with db.get_connection() as conn:
        c = conn.cursor()
        query = """
        SELECT app_id,
               count(*) as total,
               sum(CASE WHEN sip_relevance_status = 'DIRECT_SIP_RELEVANT' THEN 1 ELSE 0 END) as direct_sip,
               sum(CASE WHEN sip_relevance_status = 'INDIRECT_SIP_RELEVANT' THEN 1 ELSE 0 END) as indirect_sip,
               sum(CASE WHEN sip_relevance_status = 'GENERAL_INVESTMENT_RELEVANT' THEN 1 ELSE 0 END) as general_inv,
               sum(CASE WHEN sip_relevance_status IN ('DIRECT_SIP_RELEVANT', 'INDIRECT_SIP_RELEVANT') THEN 1 ELSE 0 END) as total_sip
        FROM reviews
        WHERE eligibility_status = 'ELIGIBLE'
        GROUP BY app_id
        ORDER BY total_sip DESC;
        """
        rows = c.execute(query).fetchall()
        print("-" * 80)
        print(f"{'App ID':15s} | {'Total':6s} | {'Direct SIP':10s} | {'Indirect':8s} | {'Total SIP':10s} | {'SIP %':6s}")
        print("-" * 80)
        for r in rows:
            pct = (r['total_sip'] / r['total'] * 100) if r['total'] > 0 else 0
            print(f"{r['app_id']:15s} | {r['total']:6d} | {r['direct_sip']:10d} | {r['indirect_sip']:8d} | {r['total_sip']:10d} | {pct:5.1f}%")
        print("-" * 80)

    print("\nPhase 3 processing completed successfully.")

if __name__ == "__main__":
    main()
