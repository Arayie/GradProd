# GROWWW INVESTOR DISCOVERY ENGINE – MONITORING & ALERTING GUIDE
**Document Version:** 1.0  
**Phase:** 8 Production Operations  

---

## 1. PRODUCTION MONITORING METRICS & SLAS

The platform defines strict Service Level Objectives (SLOs) across system availability, database latency, data integrity, and compliance:

| Metric | Target / SLA | Warning Threshold | Critical Threshold | Check Frequency |
| :--- | :--- | :--- | :--- | :--- |
| **Streamlit Web Uptime** | 99.9% availability | HTTP 5xx > 1% in 5m | Container down / non-responsive | 30 seconds |
| **Database Query Latency** | < 10 ms | Latency > 50 ms | Latency > 200 ms or connection timeout | 60 seconds |
| **Foreign Key Violations** | Exactly 0 | N/A | $\ge 1$ violation | Daily |
| **Synthetic Quarantine** | Exactly 8 quarantined, 0 leaked | Leaked $> 0$ | Leaked $> 0$ | Hourly |
| **Data Freshness** | Weekly refresh completed | Age > 10 days | Age > 14 days | Daily |
| **Container Memory (RSS)** | < 256 MB (budget: 512 MB) | RSS > 400 MB | RSS > 480 MB | 60 seconds |
| **Free Disk Storage** | > 10 GB | Free < 2 GB | Free < 500 MB | 5 minutes |

---

## 2. HEALTH CHECK CLI & CONTAINER INTEGRATION

The platform provides an automated health diagnostics endpoint via `scripts/health_check.py`:

```bash
# Human-readable output
PYTHONPATH=.:./lib python3 scripts/health_check.py

# Machine-readable JSON output for monitoring daemons
PYTHONPATH=.:./lib python3 scripts/health_check.py --json
```

### Docker Healthcheck Definition
Configured in `Dockerfile` and `docker-compose.yml`:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1
```

---

## 3. ALERT DEFINITIONS & ROUTING MATRIX

| Alert Name | Severity | Condition | Action / Notification Channel |
| :--- | :--- | :--- | :--- |
| `DBIntegrityViolation` | **CRITICAL** | `foreign_key_violations > 0` | PagerDuty / Slack `#alerts-growww-core` |
| `QuarantineLeakDetected`| **CRITICAL** | `leaked_into_eligible > 0` | Immediate rollback + email to Data Lead |
| `DatabaseHighLatency` | **WARNING** | `query_latency_ms > 50` | Slack `#alerts-growww-ops` |
| `IngestionRunFailure` | **WARNING** | Weekly refresh failed for any app | Create Jira / Linear ticket + retry |
| `MemoryLeakWarning` | **WARNING** | `process_memory_mb > 400` | Automated container restart |
| `StorageNearCapacity` | **CRITICAL** | `free_disk_space_gb < 1.0` | Expand cloud persistent disk volume |

---

## 4. PROMETHEUS & CLOUDWATCH INTEGRATION

### AWS CloudWatch Metric Filter Example
Forward stdout/stderr from Docker container to CloudWatch Logs:

```json
{
  "logGroupName": "/aws/ecs/growww-discovery-engine",
  "metricFilters": [
    {
      "filterName": "IngestionErrors",
      "filterPattern": "[timestamp, level = ERROR*, msg]",
      "metricTransformations": [
        {
          "metricName": "IngestionFailureCount",
          "metricNamespace": "Growww/DiscoveryEngine",
          "metricValue": "1"
        }
      ]
    }
  ]
}
```

### Prometheus Blackbox Exporter Configuration
```yaml
scrape_configs:
  - job_name: 'growww_engine_probe'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - https://discovery.growww-research.internal/_stcore/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - target_label: instance
        replacement: growww_production
      - target_label: __address__
        replacement: blackbox-exporter:9115
```
