# Phonon Architecture

## Components

### Coordinator (Go binary)
- HTTP server serving OpenAI-compatible API
- mDNS discovery for phone registration
- YAML-based declarative configuration
- Embedded web UI
- OIDC authentication
- Health monitoring and Prometheus metrics
- SQLite event log
- Model cache and distribution

### Phone Sidecar (Kotlin APK)
- Foreground service with persistent notification
- Inference engine via LiteRT-LM (NPU-accelerated)
- Heartbeat and health reporting to coordinator
- Model download and cache management
- Battery and thermal state reporting

### Visualization Engine
- Each phone screen is a live telemetry display
- Theme pack system — community-contributed Kotlin files
- Renders device state (inference load, battery, temperature, processing mode)
- Packs receive a VizState snapshot every frame
- Packs: Synthwave, Honeycomb, Veil, Cyber HUD, Neon Ring, Matrix Rain, Bioluminescent, LCARS

## Modes

### Pool Mode (available now)
Each phone runs independently. Coordinator load-balances requests round-robin. All phones work in parallel.

### Shard Mode (in development)
Multiple phones collectively run one large model via pipelined-ring parallelism. Coordinator routes to the group as a single logical device.
