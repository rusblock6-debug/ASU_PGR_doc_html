# Prometheus, Grafana, and Node Exporter Monitoring Stack

This directory contains the configuration for the monitoring stack added to the dispatching system.

## Services Added

### 1. Prometheus (v3.0.0)
- **Container**: `dispatching-prometheus`
- **Port**: `9090` (configurable via `PROMETHEUS_PORT` env var)
- **Purpose**: Metrics collection and alerting system
- **Access**: http://localhost:9090

### 2. Grafana (v11.3.0)
- **Container**: `dispatching-grafana`
- **Port**: `3002` (configurable via `GRAFANA_PORT` env var)
- **Purpose**: Metrics visualization and dashboards
- **Access**: http://localhost:3002
- **Default Credentials**: 
  - Username: `admin` (configurable via `GRAFANA_ADMIN_USER`)
  - Password: `admin` (configurable via `GRAFANA_ADMIN_PASSWORD`)

### 3. Node Exporter (v1.8.2)
- **Container**: `dispatching-node-exporter`
- **Port**: `9100` (configurable via `NODE_EXPORTER_PORT` env var)
- **Purpose**: Exports hardware and OS metrics
- **Access**: http://localhost:9100/metrics

### 4. Postgres Exporter (v0.15.0)
- **Container**: `dispatching-postgres-exporter`
- **Port**: `9187` (configurable via `POSTGRES_EXPORTER_PORT` env var)
- **Purpose**: Exports PostgreSQL database metrics
- **Access**: http://localhost:9187/metrics

### 5. Redis Exporter (v1.62.0)
- **Container**: `dispatching-redis-exporter`
- **Port**: `9121` (configurable via `REDIS_EXPORTER_PORT` env var)
- **Purpose**: Exports Redis cache metrics
- **Access**: http://localhost:9121/metrics

### 6. NanoMQ (built-in Prometheus endpoint)
- **Container**: `dispatching-nanomq`
- **Endpoint**: `/api/v4/prometheus` on port `8081`
- **Purpose**: MQTT broker metrics (connections, sessions, topics)
- **Access**: http://localhost:8081/api/v4/prometheus

## Quick Start

1. Start the monitoring stack along with other services:
   ```bash
   docker compose -f docker-compose.bort.yaml up -d prometheus grafana node-exporter
   ```

2. Access Grafana at http://localhost:3002
   - Login with `admin/admin`
   - The Prometheus datasource is automatically configured
   - Node Exporter dashboard is pre-loaded in the "Monitoring" folder

3. Access Prometheus at http://localhost:9090
   - View metrics and run PromQL queries
   - Check targets at http://localhost:9090/targets

## Configuration

### Prometheus Configuration
The main configuration file is located at:
- `./config/prometheus/prometheus.yml`

Current scrape jobs:
- `prometheus` - Prometheus self-monitoring
- `node-exporter` - System metrics from Node Exporter
- `postgres` - PostgreSQL database metrics from Postgres Exporter
- `redis` - Redis cache metrics from Redis Exporter
- `nanomq` - NanoMQ MQTT broker metrics (built-in endpoint)

To add more scrape targets, edit the `prometheus.yml` file and reload Prometheus:
```bash
docker compose -f docker-compose.bort.yaml restart prometheus
```

### Grafana Auto-Provisioning
Grafana is configured with automatic provisioning:
- **Datasource**: `./config/grafana/provisioning/datasources/prometheus.yml`
- **Dashboards**: `./config/grafana/provisioning/dashboards/`

Pre-installed dashboards:
- **Node Exporter Quickstart** (ID: 13978, 24KB) - Ultra-minimal, fastest to load
- **Node Exporter Simple** (ID: 405, 39KB) - Classic compact view
- **Node Exporter Full** (ID: 1860, 667KB) - Comprehensive system metrics for deep analysis
- **PostgreSQL Database** (ID: 9628) - PostgreSQL performance and health metrics
- **Redis Cache Monitoring** (custom) - Redis performance, memory, hit rate, evictions, network I/O, latency
- **NanoMQ MQTT Broker** (custom) - MQTT broker metrics with 17 panels

### Dashboard Details

#### Node Exporter Quickstart (⚡ Ultra-Minimal)
**File**: `node-exporter-quickstart-13978.json` (24KB)
**Best for**: Quick health checks, fastest to load

Essential metrics in a minimal layout:
- CPU usage and load
- Memory usage
- Disk space
- Network traffic
- Basic system info

👉 **Start here** if you need fastest dashboard loading and basic overview.

#### Node Exporter Simple (📊 Classic Compact)
**File**: `node-exporter-simple-405.json` (39KB)
**Best for**: Daily monitoring with classic view

Classic server metrics layout:
- CPU usage and load average
- Memory and swap usage
- Disk I/O and space
- Network I/O
- System uptime and processes

👉 **Recommended** for regular daily monitoring with traditional server metrics view.

#### Node Exporter Full (🔍 Deep Analysis)
**File**: `node-exporter-full.json` (667KB)
**Best for**: Troubleshooting and detailed system analysis

Comprehensive metrics across multiple panels:
- Detailed CPU statistics (per core, modes, temperature)
- Memory breakdown (buffers, cache, swap)
- Disk I/O latency and IOPS
- Network errors and dropped packets
- System processes and interrupts
- Hardware sensors

👉 **Switch to this** when you need detailed insights for troubleshooting.

## Environment Variables

Add these to your `.env` file if you want to customize:

```bash
# Prometheus
PROMETHEUS_PORT=9090

# Grafana
GRAFANA_PORT=3002
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# Node Exporter
NODE_EXPORTER_PORT=9100

# Postgres Exporter
POSTGRES_EXPORTER_PORT=9187

# Redis Exporter
REDIS_EXPORTER_PORT=9121
```

## Data Retention

Prometheus is configured with:
- **Retention Time**: 15 days
- **Storage Path**: Docker volume `prometheus-data`

To change retention, edit the Prometheus command in `docker-compose.bort.yaml`:
```yaml
- '--storage.tsdb.retention.time=15d'  # Change this value
```

## Monitoring Other Services

To monitor additional services in your stack:

1. Edit `./config/prometheus/prometheus.yml`
2. Add a new scrape config:
   ```yaml
   - job_name: 'service-name'
     static_configs:
       - targets: ['service-name:port']
   ```
3. Restart Prometheus

## Useful Prometheus Queries

### System Metrics
- CPU usage: `rate(node_cpu_seconds_total{mode!="idle"}[5m])`
- Memory usage: `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100`
- Disk usage: `node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100`
- Network traffic: `rate(node_network_receive_bytes_total[5m])`

### PostgreSQL Metrics
- Active connections: `pg_stat_activity_count`
- Database size: `pg_database_size_bytes`
- Transaction rate: `rate(pg_stat_database_xact_commit[5m])`
- Cache hit ratio: `rate(pg_stat_database_blks_hit[5m]) / (rate(pg_stat_database_blks_hit[5m]) + rate(pg_stat_database_blks_read[5m]))`
- Locks: `pg_locks_count`
- Replication lag: `pg_replication_lag`

### Redis Metrics
- Connected clients: `redis_connected_clients`
- Memory usage: `redis_memory_used_bytes`
- Operations per second: `rate(redis_commands_processed_total[5m])`
- Hit rate: `rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))`
- Evicted keys: `rate(redis_evicted_keys_total[5m])`

### NanoMQ Metrics
- Active connections: `nanomq_connections_count`
- Active sessions: `nanomq_sessions_count`
- Topics count: `nanomq_topics_count`
- Messages sent rate: `rate(nanomq_messages_sent[5m])`
- Messages received rate: `rate(nanomq_messages_received[5m])`
- Messages dropped rate: `rate(nanomq_messages_dropped[5m])`
- Capacity utilization: `(nanomq_connections_count / nanomq_connections_max) * 100`
- Drop ratio: `(rate(nanomq_messages_dropped[5m]) / (rate(nanomq_messages_sent[5m]) + rate(nanomq_messages_received[5m]))) * 100`
- Memory usage: `nanomq_memory_usage / 1024 / 1024` (MB)
- CPU usage: `nanomq_cpu_usage` (%)

## Troubleshooting

### Prometheus can't reach targets
Check that all services are on the `dispatching-network`:
```bash
docker network inspect dispatching-network
```

### Grafana dashboard not showing
1. Verify Prometheus datasource: http://localhost:3002/datasources
2. Check Prometheus is collecting data: http://localhost:9090/targets

### Node Exporter not collecting metrics
Node Exporter requires host PID namespace access. This is configured in the docker-compose file with `pid: host`.

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Node Exporter Documentation](https://github.com/prometheus/node_exporter)

