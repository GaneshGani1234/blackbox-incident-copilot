"""
Generates the synthetic dataset for Blackbox.

Outputs (in this folder):
  incidents.json       -> past incidents that get retained into Hindsight (the "6 months of history")
  demo_incidents.json  -> live incidents used in the demo (NOT seeded, so they are genuinely new)
  eval_set.json        -> held-out incidents with the expected cluster, used by scripts/eval_learning_curve.py

Run:  python data/generate_incidents.py

The incidents are organised into clusters (recurring failure modes) so that recall and reflect
have real patterns to find. Edit freely: the more realistic the logs and names, the better the demo.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent


def inc(id, date, service, cluster, title, sev, symptoms, error, steps, root_cause, fix, owner, mins, deploy=None):
    return {
        "id": id,
        "date": date,  # ISO date-time, UTC
        "service": service,
        "cluster": cluster,
        "title": title,
        "severity": sev,
        "symptoms": symptoms,
        "error_signature": error,
        "diagnostic_steps": [{"action": a, "result": r} for a, r in steps],
        "root_cause": root_cause,
        "fix": fix,
        "owner": owner,
        "minutes_to_resolve": mins,
        "deploy_related": deploy,
    }


INCIDENTS = [
    # ---------------- Cluster 1: DB connection pool exhaustion after deploys (checkout) ----------------
    inc("INC-0012", "2026-01-16T17:12:00Z", "checkout-service", "db-pool-exhaustion",
        "Checkout p99 latency 9s and 502s at the ingress", "SEV1",
        "p99 latency on POST /checkout jumped from 300ms to 9s. Ingress returning 502s. Order conversion dropped 40%.",
        "HikariPool-1 - Connection is not available, request timed out after 30000ms",
        [("Checked CPU and memory on checkout pods", "Normal, ruled out resource starvation"),
         ("Checked Postgres CPU", "Low, database itself was healthy"),
         ("Looked at Hikari pool metrics", "Active connections pinned at max (20/20), 140 threads waiting")],
        "The 16:45 deploy added a code path that opened a DB connection in the coupon lookup and never released it on the error branch. The pool leaked until exhausted.",
        "Rolled back the 16:45 deploy. Follow-up patch used try-with-resources in the coupon lookup. Pool size raised from 20 to 40 as a safety margin.",
        "priya.nair", 47, "Deploy at 16:45 on a Friday"),
    inc("INC-0019", "2026-02-20T16:58:00Z", "checkout-service", "db-pool-exhaustion",
        "Cart and checkout requests timing out, thread pool saturated", "SEV2",
        "Checkout API responding slowly, then timing out. Alerts on request queue depth. Started about 10 minutes after the weekly release.",
        "Timeout waiting for connection from pool; pool stats: active=20 idle=0 waiting=212",
        [("Restarted two checkout pods", "Relief for about 4 minutes, then the problem returned"),
         ("Checked for slow queries in pg_stat_activity", "No long running queries"),
         ("Diffed the release against the previous version", "New retry wrapper around the payment call holds a connection during retries")],
        "A new retry wrapper kept a DB transaction open while retrying the payment provider call, so connections were held for up to 20 seconds each.",
        "Rolled back the release. Moved the payment call outside the DB transaction, then re-released. Added a pool saturation alert at 80 percent.",
        "priya.nair", 62, "Weekly release, Friday afternoon"),
    inc("INC-0027", "2026-03-27T17:31:00Z", "orders-service", "db-pool-exhaustion",
        "Order confirmation emails delayed, API latency climbing", "SEV2",
        "Order confirmation API slow, 504s from the gateway. Customers report spinner on the order page.",
        "psycopg2.pool.PoolError: connection pool exhausted",
        [("Scaled orders-service from 6 to 12 pods", "Made it worse, more pods meant more connections and Postgres hit max_connections"),
         ("Checked deploy history", "Deploy went out 25 minutes before the first alert"),
         ("Compared connection counts per pod", "Each pod held its full pool of 15 even when idle")],
        "A new ORM version changed the default so idle connections were never returned to the pool. Scaling out multiplied the problem.",
        "Rolled back the ORM upgrade, then pinned pool_recycle and max_overflow explicitly. Reduced replicas back to 6.",
        "daniel.okafor", 71, "Dependency upgrade shipped on Friday"),
    inc("INC-0041", "2026-05-08T16:40:00Z", "checkout-service", "db-pool-exhaustion",
        "Intermittent 500s on checkout after feature flag rollout", "SEV2",
        "Roughly 15 percent of checkout requests failing with 500. Started when the new loyalty points flag reached 50 percent of traffic.",
        "HikariPool-1 - Connection is not available, request timed out after 30000ms",
        [("Checked recent flag changes", "Loyalty points flag ramped from 10 to 50 percent at 16:30"),
         ("Disabled the flag", "Errors stopped within 2 minutes"),
         ("Reviewed loyalty code", "Runs a synchronous lookup that holds a connection for the whole request")],
        "The loyalty lookup borrowed a connection and held it across a slow external call, exhausting the pool as traffic to the flag increased.",
        "Kept the flag off. Refactored the lookup to release the connection before the external call, then re-ramped the flag.",
        "priya.nair", 38, "Flag rollout on a Friday afternoon"),

    # ---------------- Cluster 2: Cache stampede after cache flush (search / catalog) ----------------
    inc("INC-0015", "2026-02-03T09:20:00Z", "search-api", "cache-stampede",
        "Search API latency spike and Elasticsearch CPU at 100 percent", "SEV2",
        "Search latency went from 80ms to 6s. Elasticsearch cluster CPU pinned. Redis hit ratio dropped to near zero.",
        "redis.hit_ratio=0.02 es.search.queue_size=1000 rejected_execution_exception",
        [("Checked Elasticsearch shard health", "Green, no unassigned shards"),
         ("Checked recent infra changes", "Redis cluster was flushed at 09:12 during a maintenance task"),
         ("Looked at request patterns", "Thousands of identical popular queries all missing cache at once")],
        "Redis was flushed during maintenance. All keys had the same 10 minute TTL, so everything expired together and every request hit Elasticsearch at once (cache stampede).",
        "Enabled request coalescing on the search cache layer and warmed the top 500 queries. Changed TTLs to a base value plus random jitter of 20 percent.",
        "mei.tanaka", 55, None),
    inc("INC-0030", "2026-04-02T11:05:00Z", "catalog-service", "cache-stampede",
        "Catalog pages slow after Redis failover", "SEV2",
        "Product pages taking 5 to 8 seconds. Database read replica CPU at 95 percent. Cache hit rate collapsed after a Redis failover.",
        "cache_miss_rate=0.97 replica_cpu=95 slow query: SELECT * FROM products WHERE category_id = ?",
        [("Checked the read replica", "Overloaded with identical category queries"),
         ("Confirmed Redis failover", "Primary failed over at 10:58 and the new primary started empty"),
         ("Checked TTL configuration", "All catalog keys share a fixed 15 minute TTL with no jitter")],
        "After the Redis failover the cache was empty and every request went to the read replica at the same time. Fixed TTLs made the recovery wave repeat every 15 minutes.",
        "Temporarily rate limited the catalog endpoints and warmed the cache from a script. Added TTL jitter and single-flight locking for cache fills.",
        "mei.tanaka", 44, None),
    inc("INC-0046", "2026-06-11T14:47:00Z", "search-api", "cache-stampede",
        "Search latency degraded again after cache key format change", "SEV3",
        "Search p95 rose to 3s. Cache hit rate fell from 92 percent to 11 percent right after the 14:30 deploy.",
        "redis.hit_ratio=0.11 after deploy sha 9c1e4ab",
        [("Checked Elasticsearch", "Elevated load but healthy"),
         ("Diffed the deploy", "Cache key builder now included a request id, so no two requests shared a key")],
        "A refactor accidentally added a per-request id to the cache key so the cache never hit. Similar load pattern to a stampede, but self inflicted.",
        "Reverted the cache key change and added a unit test asserting key stability. Warmed the cache after revert.",
        "sam.reyes", 29, "Deploy at 14:30"),

    # ---------------- Cluster 3: Kafka poison message / consumer lag (notifications) ----------------
    inc("INC-0022", "2026-03-06T02:14:00Z", "notification-service", "kafka-poison-message",
        "Notification emails and push messages delayed by hours", "SEV2",
        "Consumer lag on the order-events topic climbing past 400k. No notifications sent since 01:50.",
        "org.apache.kafka.common.errors.SerializationException: Error deserializing Avro message for id 7311; consumer group rebalancing repeatedly",
        [("Restarted consumers", "Lag kept growing, consumers crashed again within seconds"),
         ("Checked consumer logs", "Same offset failing repeatedly, then the group rebalanced"),
         ("Inspected the message at that offset", "Produced with a schema version that the consumer did not have")],
        "One message written with an incompatible Avro schema version blocked a partition. The consumer crashed on it, restarted, and reprocessed the same offset forever.",
        "Skipped the poisoned offset manually, then deployed a dead letter queue handler so undeserializable messages are parked instead of blocking. Added schema compatibility checks in CI.",
        "daniel.okafor", 96, None),
    inc("INC-0035", "2026-04-23T03:40:00Z", "notification-service", "kafka-poison-message",
        "Order events consumer stuck, lag growing on partition 3", "SEV2",
        "Lag on partition 3 of order-events at 250k while other partitions are healthy. Customers not receiving shipping updates.",
        "JsonParseException: Unexpected character at offset 1889231, partition 3; consumer group rebalance loop",
        [("Compared lag across partitions", "Only partition 3 was stuck"),
         ("Checked the consumer error rate", "Exactly one message failing over and over"),
         ("Looked at the producer of that message", "A partner webhook sent malformed JSON that was passed through unvalidated")],
        "A malformed payload from a partner webhook was published to Kafka without validation and the consumer had no dead letter handling for parse errors.",
        "Skipped the offset, replayed the affected window after fixing the payload, and added validation at the producer plus a dead letter topic for parse errors.",
        "daniel.okafor", 58, None),
    inc("INC-0049", "2026-07-02T01:55:00Z", "billing-service", "kafka-poison-message",
        "Invoice generation stalled overnight", "SEV3",
        "Invoice events not being processed, lag at 90k. Finance noticed missing invoices in the morning.",
        "SerializationException at offset 552108; consumer restarted 63 times in 40 minutes",
        [("Checked consumer restart count", "Crash looping"),
         ("Checked the offset", "One event with a null required field")],
        "A single event with a null required field crashed the consumer on every retry and blocked the partition.",
        "Skipped the offset, backfilled the invoice manually, and enabled the shared dead letter handler library in billing-service.",
        "sam.reyes", 41, None),

    # ---------------- Cluster 4: Memory leak / OOMKilled after dependency upgrade (payments) ----------------
    inc("INC-0018", "2026-02-13T13:22:00Z", "payments-gateway", "oom-memory-leak",
        "Payments gateway pods restarting repeatedly", "SEV1",
        "Pods OOMKilled every 20 to 30 minutes. Payment success rate dipping during each restart. Memory graph shows a steady climb.",
        "OOMKilled exit code 137, container memory limit 2Gi, heap growth ~40MB/min",
        [("Raised memory limit from 2Gi to 3Gi", "Only delayed the restarts"),
         ("Took a heap dump from a pod before it died", "Millions of unreleased HTTP client connection objects"),
         ("Checked what changed this week", "HTTP client library upgraded from 4.5 to 5.2")],
        "The upgraded HTTP client library created a new connection manager per request because of a changed default, leaking connection objects.",
        "Pinned the HTTP client back to 4.5 and shipped a shared client instance in the following release. Added a memory growth alert.",
        "lena.fischer", 84, "Dependency upgrade earlier in the week"),
    inc("INC-0037", "2026-05-01T10:09:00Z", "payments-gateway", "oom-memory-leak",
        "Payments gateway OOMKilled again after logging change", "SEV2",
        "Restarts every 45 minutes, heap steadily rising. Similar shape to the February incident.",
        "OOMKilled exit code 137, heap growth ~25MB/min, top allocation: LogEvent buffers",
        [("Checked whether the HTTP client was still pinned", "Yes, pinned, so not the same cause"),
         ("Heap dump", "Large retained set of log event buffers"),
         ("Reviewed the new async log appender config", "Unbounded queue size")],
        "A new async logging appender was configured with an unbounded queue. Under load the queue grew without limit and consumed the heap.",
        "Set a bounded queue with a discard policy for debug logs and rolled out the fix. Added a check for unbounded queues in config review.",
        "lena.fischer", 66, "Config change on Thursday"),
    inc("INC-0052", "2026-08-05T09:33:00Z", "reporting-service", "oom-memory-leak",
        "Reporting service pods OOMKilled during month end exports", "SEV3",
        "Pods restarting during large CSV exports. Memory spikes to the limit within minutes of an export starting.",
        "OOMKilled exit code 137 during GET /exports/monthly",
        [("Checked which endpoint was active", "Monthly export"),
         ("Reviewed the export code", "Loads the full result set into memory before writing the file")],
        "The export loaded the entire result set into memory instead of streaming it.",
        "Switched to streaming with a cursor and chunked writes. Set a memory limit alert.",
        "sam.reyes", 52, None),

    # ---------------- Cluster 5: Expired TLS cert on internal mTLS (auth) ----------------
    inc("INC-0024", "2026-03-13T06:03:00Z", "auth-service", "tls-cert-expiry",
        "Widespread 503s across services, login failing", "SEV1",
        "Login and token refresh failing everywhere. Downstream services returning 503 upstream connect error.",
        "x509: certificate has expired or is not yet valid: current time 2026-03-13T06:03:11Z is after 2026-03-13T06:00:00Z",
        [("Checked auth-service pods", "Healthy and running"),
         ("Checked service mesh logs", "mTLS handshake failures to auth-service"),
         ("Inspected the certificate", "Internal CA issued cert expired at 06:00 UTC")],
        "The internal mTLS certificate for auth-service expired. The renewal job had been failing silently for two weeks because of a permissions change.",
        "Manually issued and rotated a new certificate. Fixed the renewal job permissions and added an alert for certificates expiring within 14 days.",
        "amir.haddad", 33, None),
    inc("INC-0044", "2026-06-05T05:58:00Z", "gateway", "tls-cert-expiry",
        "Partner API calls failing with TLS handshake errors", "SEV2",
        "Several partners reported TLS handshake failures against the public API gateway. Internal traffic unaffected.",
        "SSL_ERROR_BAD_CERT_DOMAIN; certificate expired 2026-06-05T05:00:00Z",
        [("Verified from an external host", "Handshake fails, cert expired"),
         ("Checked cert-manager", "Renewal challenge failing because a DNS record changed")],
        "The public certificate could not renew because the ACME DNS challenge record was removed during a DNS cleanup.",
        "Restored the DNS challenge record, forced renewal, and added the challenge record to the DNS cleanup allowlist. Alerting now covers all cert-manager certificates.",
        "amir.haddad", 27, None),

    # ---------------- Singletons: one-off incidents with no repeating cluster ----------------
    inc("INC-0033", "2026-04-14T15:26:00Z", "platform", "dns-throttling",
        "Intermittent DNS resolution failures across services", "SEV2",
        "Random name resolution errors, mostly from high traffic services. Retries succeeded.",
        "getaddrinfo EAI_AGAIN; CoreDNS dropped packets, conntrack table full on node",
        [("Checked CoreDNS pods", "CPU throttled"),
         ("Checked node conntrack", "Table near full on busy nodes")],
        "CoreDNS was CPU throttled and the node conntrack table filled up under peak load.",
        "Increased CoreDNS replicas and CPU limits, enabled NodeLocal DNSCache, and raised the conntrack limit.",
        "amir.haddad", 74, None),
    inc("INC-0039", "2026-05-15T22:10:00Z", "logging-pipeline", "disk-full",
        "Logs missing from dashboards, ingest nodes unhealthy", "SEV3",
        "Log ingestion lagging and then dropping. Dashboards empty for the last 40 minutes.",
        "No space left on device: /var/lib/logstore",
        [("Checked node disk", "100 percent used on the log volume"),
         ("Checked retention", "Retention job had been paused during a migration")],
        "The retention cleanup job was paused during a migration and never resumed, so the log volume filled.",
        "Resumed the cleanup job, freed space, and added a disk usage alert at 80 percent.",
        "lena.fischer", 36, None),
    inc("INC-0047", "2026-07-09T12:41:00Z", "web-frontend", "bad-feature-flag",
        "Homepage blank for users on Safari", "SEV2",
        "Homepage rendering blank for about 20 percent of users, all on Safari. No backend errors.",
        "TypeError: undefined is not a function (evaluating 'arr.at(-1)') in bundle.js",
        [("Checked backend dashboards", "All normal"),
         ("Checked frontend error tracking", "Errors only on older Safari versions"),
         ("Checked flags", "New homepage flag enabled 15 minutes earlier")],
        "The new homepage code used a JavaScript method unsupported by older Safari and the flag exposed it to all users at once.",
        "Turned the flag off. Added a polyfill and a Safari browser check to the release checklist.",
        "sam.reyes", 22, "Flag rollout"),
]


# ---------------- Live demo incidents: NOT seeded, these are what you trigger on stage ----------------
DEMO = [
    {
        "id": "DEMO-A",
        "label": "1. Checkout is slowing down (the recurring one)",
        "date": "2026-09-25T16:52:00Z",
        "service": "checkout-service",
        "severity": "SEV1",
        "title": "Checkout API latency climbing, 502s from ingress",
        "symptoms": "p99 latency on POST /checkout went from 280ms to 7s in ten minutes. Ingress returning 502s. A deploy went out at 16:41.",
        "error_signature": "HikariPool-1 - Connection is not available, request timed out after 30000ms",
        "expected_cluster": "db-pool-exhaustion",
    },
    {
        "id": "DEMO-B",
        "label": "2. Search is crawling after a cache flush",
        "date": "2026-09-26T10:15:00Z",
        "service": "search-api",
        "severity": "SEV2",
        "title": "Search latency spike, Elasticsearch CPU pinned",
        "symptoms": "Search results taking 5 to 7 seconds. Redis hit ratio near zero right after a maintenance flush. Elasticsearch rejecting queries.",
        "error_signature": "redis.hit_ratio=0.03 rejected_execution_exception",
        "expected_cluster": "cache-stampede",
    },
    {
        "id": "DEMO-C",
        "label": "3. Something the team has never seen",
        "date": "2026-09-27T20:05:00Z",
        "service": "inventory-service",
        "severity": "SEV2",
        "title": "Inventory counts drifting negative for a subset of SKUs",
        "symptoms": "A few hundred SKUs show negative stock. No errors in logs. Only affects SKUs in the EU warehouse.",
        "error_signature": "none, invariants check failing: stock_on_hand < 0",
        "expected_cluster": "none",
    },
    {
        "id": "DEMO-D",
        "label": "4. Same pattern, different service (generalisation)",
        "date": "2026-09-28T17:05:00Z",
        "service": "inventory-service",
        "severity": "SEV2",
        "title": "Inventory API timeouts after Friday release",
        "symptoms": "Inventory reads timing out about 12 minutes after the 16:50 release. Pods look healthy. Threads waiting.",
        "error_signature": "Timeout waiting for connection from pool; active=25 idle=0 waiting=180",
        "expected_cluster": "db-pool-exhaustion",
    },
]

# Held-out incidents used to measure retrieval quality with and without memory
EVAL = [
    {"id": "EVAL-1", "service": "checkout-service", "title": "Checkout slow after evening release",
     "symptoms": "502s at ingress, latency 8s, deploy 20 minutes ago.",
     "error_signature": "Connection is not available, request timed out after 30000ms", "expected_cluster": "db-pool-exhaustion"},
    {"id": "EVAL-2", "service": "orders-service", "title": "Order API 504s, DB connections maxed",
     "symptoms": "Pool exhausted, threads waiting, started after dependency bump.",
     "error_signature": "connection pool exhausted", "expected_cluster": "db-pool-exhaustion"},
    {"id": "EVAL-3", "service": "search-api", "title": "Search slow after Redis restart",
     "symptoms": "Cache empty after restart, Elasticsearch overloaded by identical queries.",
     "error_signature": "hit_ratio=0.01 rejected_execution_exception", "expected_cluster": "cache-stampede"},
    {"id": "EVAL-4", "service": "notification-service", "title": "Push notifications stopped, lag growing",
     "symptoms": "One partition stuck, consumer crash looping on the same offset.",
     "error_signature": "SerializationException at offset", "expected_cluster": "kafka-poison-message"},
    {"id": "EVAL-5", "service": "payments-gateway", "title": "Pods keep restarting with exit 137",
     "symptoms": "Heap climbs steadily until OOMKilled, restarts every half hour.",
     "error_signature": "OOMKilled exit code 137", "expected_cluster": "oom-memory-leak"},
    {"id": "EVAL-6", "service": "auth-service", "title": "Login failing, handshake errors between services",
     "symptoms": "mTLS failures to auth-service, sudden and cluster wide.",
     "error_signature": "x509: certificate has expired", "expected_cluster": "tls-cert-expiry"},
]

if __name__ == "__main__":
    (HERE / "incidents.json").write_text(json.dumps(INCIDENTS, indent=2))
    (HERE / "demo_incidents.json").write_text(json.dumps(DEMO, indent=2))
    (HERE / "eval_set.json").write_text(json.dumps(EVAL, indent=2))
    clusters = {}
    for i in INCIDENTS:
        clusters.setdefault(i["cluster"], []).append(i["id"])
    print(f"Wrote {len(INCIDENTS)} incidents, {len(DEMO)} demo incidents, {len(EVAL)} eval incidents")
    for c, ids in clusters.items():
        print(f"  {c}: {', '.join(ids)}")
