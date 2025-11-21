# Scalability Guide for Mini Bitly

This document outlines architectural decisions and strategies for scaling the Mini Bitly URL shortener to handle high traffic and distributed deployments.

---

## Problem 1: Heavy Visit Logging Operations

### Problem Statement
When visit logging becomes too heavy (e.g., sending logs to external services, multiple database writes, ...), it can significantly impact the main redirect service performance and increase response times.

### Solutions

#### 1.1 Message Queue (Recommended)
**Architecture: Async Event-Driven Logging**

```
User Request → FastAPI → Redis/RabbitMQ → Worker Processes → External Service/DB
                ↓
            Instant Redirect
```

**Implementation:**
- Use **Redis** (with Redis Streams) or **RabbitMQ** for message queuing or **Kafka**
- FastAPI publishes visit events to queue and immediately returns redirect
- Separate worker processes consume events and perform heavy logging
- **Benefits:**
  - Zero impact on redirect latency
  - Failed logs can be retried
  - Can process logs in batches for efficiency

**Technologies:**
- Redis + `arq` for Python
- RabbitMQ + `celery`
- Kafka for very high volume



---

#### 1.2 Database Optimization Strategies

**A. Batched Inserts:**
```python
# Instead of one insert per visit
visits = []
for visit_data in queue:
    visits.append(URLVisit(**visit_data))

# Bulk insert every 100 records or 1 second
await db.bulk_insert_mappings(URLVisit, visits)
```

**B. Separate Write Database:**
- Use database replication: Write to replica, read from primary
- Async replication reduces load on main database

**C. Time-Series Database:**

- Use InfluxDB, or ClickHouse for visit logs
- Optimized for high-volume time-series data
- Much faster inserts than traditional RDBMS

#### 1.3 Fire-and-Forget with Background Tasks
**For lighter loads:**

```python
from fastapi import BackgroundTasks

@router.get("/{short_code}")
async def redirect(short_code: str, background_tasks: BackgroundTasks):
    url = await get_url(short_code)
    
    # Schedule logging in background
    background_tasks.add_task(log_visit_heavy, url.id, client_ip)
    
    # Return immediately
    return RedirectResponse(url.original_url)
```

**Limitations:**
- No retry mechanism
- Lost if server crashes
- Not suitable for critical logging

---

### Recommended Solution Stack

**For Medium Traffic (< 10k req/s):**
- Redis + Background workers
- Batch inserts every 1-2 seconds

**For High Traffic (10k-100k req/s):**
- Kafka + Multiple consumer groups
- ClickHouse for log storage
- Separate analytics pipeline

**For Very High Traffic (> 100k req/s):**
- Kafka + Stream processing (Flink/Spark)
- Multi-region data centers
- Eventual consistency model

---

## Problem 2: Multi-Instance Deployment (Horizontal Scaling)

### Problem Statement
When deploying multiple FastAPI instances across multiple servers, what needs to change to maintain consistency and reliability?

### Components That Need to Be External/Shared

#### 2.1 Database (Already External)
**Current:** PostgreSQL in Docker
**Production Changes:**
- Enable connection pooling at database level (PgBouncer)
- Configure per-instance connection limits: `DB_POOL_SIZE = 10-20 per instance`
- Use read replicas for stats queries

```
                    ┌──> FastAPI Mini Bitly Instance 1 ──┐
                    │                                    │ 
Load Balancer ──────┼──> FastAPI Mini Bitly Instance 2 ──┼──> PostgreSQL Primary
                    │                                    │
                    └──> FastAPI Mini Bitly Instance 3 ──┘        └──> Read Replicas
```

---

#### 2.2 Distributed Caching (New Requirement)
**Problem:** Short code lookups hit database on every request

**Solution:** Implement Redis for caching

```python
# Cache URL lookups
async def get_url_by_short_code(db, short_code: str):
    # Try cache first
    cached = await redis.get(f"url:{short_code}")
    if cached:
        return URLObject.parse(cached)
    
    # Database fallback
    url = await db.query(URL).filter_by(short_code=short_code).first()
    
    # Cache for 1 hour
    await redis.setex(f"url:{short_code}", 3600, url.json())
    return url
```

**Benefits:**
- 10-100x faster lookups (< 1ms vs 10-50ms)
- Reduces database load by 80-90%
- Handles traffic spikes

**Architecture:**
```
FastAPI Instances → Redis Cluster → PostgreSQL
                    (Cache)         (Source of truth)
```

---


#### 2.5 Short Code Generation (Collision Handling)

**Problem:** Multiple instances might generate the same short code simultaneously

**Solutions:**

**A. Database-Level Uniqueness (Current)**
- Unique constraint on `short_code` column handles collisions
- Works but requires database round-trip

**B. Distributed ID Generation:**
```python
# For Example Twitter Snowflake algorithm
# Format: [timestamp][machine_id][sequence]
# Guarantees uniqueness across instances

from snowflake import SnowflakeGenerator

generator = SnowflakeGenerator(instance_id=1)  # Unique per instance
short_id = generator.next_id()
short_code = base62_encode(short_id)
```

**C. Redis-based Counter:**
```python
# Atomic increment
counter = await redis.incr("short_code_counter")
short_code = base62_encode(counter)
```

---

### Deployment Architecture Changes

#### Before (Single Instance):
```
Docker Compose → PostgreSQL
     ↓
  FastAPI App
```

#### After (Multi-Instance):
```
                        ┌─> FastAPI Pod 1 ─┐
                        │                   │
Internet → Load Balancer┼─> FastAPI Pod 2   ──> Redis Cluster
         (Nginx)        │                   │   (Cache + Queue)
                        └─> FastAPI Pod 3 ─┘        ↓
                                                PostgreSQL Primary
                                                     │
                                                Read Replicas
```

#### Required Infrastructure:

1. **Load Balancer:**
   - Nginx, HAProxy
   - Health check endpoint: `GET /health`
   - Session affinity: Not needed (stateless)

2. **Container Orchestration:**
   - **Kubernetes** (recommended)
   - **Docker Swarm** (simpler alternative)


---

### Configuration Changes Needed

**docker-compose.yml → docker-compose.prod.yml:**

```yaml
services:
  app:
    deploy:
      replicas: 3  # Multiple instances
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    environment:
      - DB_POOL_SIZE=10  # Reduced per instance
      - REDIS_URL=redis://redis-cluster:6379
```

**Add Redis:**
```yaml
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
```

---

## Problem 3: High Traffic Scenarios (Ad Campaign)

### Problem Statement
A marketing campaign brings **thousands of requests per second**. How do we maintain uptime and prevent service degradation?

---

### 3.1 Immediate Response: Rate Limiting

**Protect the service from overload**

#### Application-Level Rate Limiting:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/{short_code}")
@limiter.limit("100/minute")  # Per IP
async def redirect(short_code: str, request: Request):
    # Your code
```

#### Redis-Based Distributed Rate Limiting:
```python
# Works across all instances
async def rate_limit(client_ip: str, limit: int = 100) -> bool:
    key = f"ratelimit:{client_ip}"
    current = await redis.incr(key)
    
    if current == 1:
        await redis.expire(key, 60)  # 1 minute window
    
    return current <= limit
```

#### API Gateway Level:
- **Cloudflare:** DDoS protection + rate limiting
- **Traefik:** Self-hosted API gateway

---

### 3.2 Caching Strategy (Critical!)

**Goal: Serve 90%+ of requests from cache**

#### Multi-Layer Caching:

**Layer 1: CDN (Edge Caching)**
```
User → Cloudflare/CloudFront → Origin
       (Cached for 60s)
```

- Cache redirect responses at CDN level
- Set `Cache-Control: public, max-age=60` headers
- Reduces load by 70-90%

**Layer 2: Application Cache (Redis)**
```python
@router.get("/{short_code}")
async def redirect(short_code: str):
    # L1: Redis cache
    cached_url = await redis.get(f"url:{short_code}")
    if cached_url:
        return RedirectResponse(cached_url, status_code=301)
    
    # L2: Database
    url = await db.get_url(short_code)
    await redis.setex(f"url:{short_code}", 3600, url.original_url)
    
    return RedirectResponse(url.original_url)
```

**Layer 3: In-Memory Cache (Per Instance)**
```python
from cachetools import TTLCache

# Per-instance memory cache
url_cache = TTLCache(maxsize=10000, ttl=60)

async def get_url(short_code: str):
    if short_code in url_cache:
        return url_cache[short_code]
    
    # Fallback to Redis → DB
    url = await redis_or_db_lookup(short_code)
    url_cache[short_code] = url
    return url
```

**Benefits:**
- **CDN:** 10-100ms latency worldwide
- **Redis:** 1-5ms latency
- **Memory:** < 0.1ms latency
- Combined: Can handle 100k+ req/s per instance

---

### 3.3 Database Optimization

#### Read Replicas for Analytics
```python
# Primary for writes
write_db = create_engine(PRIMARY_URL)

# Replicas for reads (stats queries)
read_db = create_engine(REPLICA_URL)

@router.get("/{short_code}/stats")
async def get_stats(short_code: str):
    # Use read replica - doesn't affect writes
    return await read_db.get_stats(short_code)
```

#### Connection Pooling Tuning
```python
# For high traffic
DB_POOL_SIZE = 50  # Per instance
DB_MAX_OVERFLOW = 20
DB_POOL_PRE_PING = True
```

#### Query Optimization
```python
# Use covering indexes
CREATE INDEX idx_url_visits_stats ON url_visits(url_id, visited_at) 
INCLUDE (visitor_ip);

# Stats query becomes index-only scan
SELECT COUNT(*) FROM url_visits WHERE url_id = 123;
```

---

### 3.4 Auto-Scaling Strategy

#### Kubernetes HPA (Horizontal Pod Autoscaler)

---

### 3.5 Circuit Breaker Pattern

**Prevent cascade failures**

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def log_visit_to_external_service(visit_data):
    # If this fails 5 times, circuit opens
    # Service continues without logging
    await external_service.log(visit_data)

@router.get("/{short_code}")
async def redirect(short_code: str):
    url = await get_url(short_code)
    
    try:
        await log_visit_to_external_service(visit_data)
    except CircuitBreakerError:
        # Circuit is open - skip logging
        # Main service stays up!
        pass
    
    return RedirectResponse(url.original_url)
```

---

### 3.6 Monitoring & Alerting

**Essential metrics to track:**

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram

redirect_counter = Counter('redirects_total', 'Total redirects')
redirect_latency = Histogram('redirect_latency_seconds', 'Redirect latency')

@router.get("/{short_code}")
async def redirect(short_code: str):
    with redirect_latency.time():
        redirect_counter.inc()
        # ... handle redirect
```

**Alert thresholds:**
- Response time > 100ms → Scale up
- Error rate > 1% → Investigate
- Database connection pool > 90% → Add replicas
- Redis memory > 80% → Scale cluster

---

## Complete High-Traffic Architecture

```
                        Cloudflare CDN
                        (Edge Cache)
                             ↓
                    ┌────────────────┐
                    │  Load Balancer │
                    │                │
                    └────────────────┘
                             ↓
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   FastAPI Pod 1       FastAPI Pod 2       FastAPI Pod 3
   (Auto-scaled 3-50 pods)
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ↓
                    ┌────────────────┐
                    │  Redis Cluster │
                    │  (Cache + Queue)│
                    └────────────────┘
                             ↓
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   PostgreSQL           Read Replica        Read Replica
   Primary (Writes)      
        │
        ↓
   Background Workers
   (Process Visit Logs)
```

---

## Summary of Changes by Scenario

### Heavy Logging:
- ✅ Add Redis/RabbitMQ message queue
- ✅ Implement background workers
- ✅ Use batched inserts
- ✅ Consider time-series DB for logs

### Multi-Instance:
- ✅ Add Redis for caching and coordination
- ✅ Use managed PostgreSQL with connection pooling
- ✅ Deploy with Kubernetes/orchestrator
- ✅ Add load balancer with health checks

### High Traffic:
- ✅ Enable multi-layer caching (CDN + Redis + Memory)
- ✅ Implement rate limiting
- ✅ Add auto-scaling (HPA)
- ✅ Use read replicas
- ✅ Implement circuit breakers
- ✅ Set up monitoring and alerts
