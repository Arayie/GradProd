# GROWWW INVESTOR DISCOVERY ENGINE – PRODUCTION PERFORMANCE REPORT
**Execution Date:** 2026-11-07T16:50:17Z  
**Benchmarking Environment:** Local Production Runtime / macOS Darwin  
**Verdict:** ALL PERFORMANCE BUDGETS SATISFIED  

---

## 1. PERFORMANCE BUDGET SCORECARD

| Metric | Measured Value | Budget / SLA | Margin | Status |
| :--- | :--- | :--- | :--- | :--- |
| **App Cold Start** | 0.001 s | < 5.0 s | 5.00 s | **PASS** |
| **Mean Analytical Query Latency** | 0.35 ms | < 50.0 ms | 49.65 ms | **PASS** |
| **Max Analytical Query Latency** | 0.78 ms | < 100.0 ms | 99.22 ms | **PASS** |
| **CSV Export (1,000 Records)** | 1.73 ms | < 1,000 ms | 998.27 ms | **PASS** |
| **PDF Digest Generation** | 2.21 ms | < 2,000 ms | 1997.79 ms | **PASS** |
| **Concurrent Throughput (10 Users)** | 1088.0 QPS | > 20 QPS | +1068.0 QPS | **PASS** |
| **P95 Latency Under Load** | 11.71 ms | < 50.0 ms | 38.29 ms | **PASS** |
| **Process Memory RSS** | 128.61 MB | < 512 MB | 383.4 MB | **PASS** |

---

## 2. DETAILED QUERY LATENCY BREAKDOWN

```json
{
  "overview_metrics": 0.64,
  "sip_pain_point_breakdown": 0.17,
  "app_comparison_aggregates": 0.78,
  "opportunity_radar_fetch": 0.01,
  "verbatim_evidence_search": 0.14
}
```

---

## 3. CONCURRENCY & MULTI-USER BENCHMARK RESULTS

- **Simulated Concurrent Researchers:** 10 threads
- **Total Executed Queries:** 200
- **Successful Responses:** 200 (100.0%)
- **Failed Queries / Timeouts:** 0 (0.0%)
- **Mean Response Time:** 8.96 ms
- **95th Percentile (P95):** 11.71 ms
- **Database Engine:** SQLite 3.35+ (WAL Journal Mode)
