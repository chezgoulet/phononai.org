# Phonon Architecture

## Components

### Coordinator (Go binary)
- HTTP server serving OpenAI-compatible API
- mDNS discovery for phone registration
- YAML-based declarative configuration
- Embedded React web UI
- OIDC authentication (Authentik)
- Health monitoring and Prometheus metrics
- SQLite event log
- Model cache and distribution

### Phone Sidecar (Kotlin APK)
- Foreground service with persistent notification
- Inference engine via LiteRT-LM (NPU-accelerated)
- Heartbeat and health reporting to coordinator
- Model download and cache management
- Battery and thermal state reporting

### Modes

**Pool Mode (Phase 1):** Each phone runs independently. Coordinator load-balances requests round-robin. All phones work in parallel. Best for fast, high-throughput inference.

**Shard Mode (Phase 2+):** Multiple phones collectively run one large model via pipelined-ring parallelism. Coordinator routes to the group. Best for running models larger than any single phone can handle.

## Public Pool Architecture

The public Phonon pool extends the coordinator with:

- **Authentik** — Multi-tenant authentication and authorization
- **Metering service** — Token usage tracking per account
- **Stripe integration** — Billing and credit management
- **Phone procurement** — Donation intake, testing, and commissioning pipeline
- **Priority scheduling** — Donors get priority access to the pool
