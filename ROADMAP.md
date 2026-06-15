# Phonon Roadmap

## Phase 1 — Pool Mode (Alpha) *[Current]*

- [x] Coordinator Go binary — HTTP server, mDNS discovery, YAML config, web UI
- [x] Phone sidecar Kotlin APK — foreground service, heartbeat, inference via LiteRT-LM
- [x] Real inference routing to phones (placeholder mock replaced)
- [x] Model download HTTP endpoint
- [x] Battery depletion handling
- [x] TLS/HTTPS for production deployment
- [x] Docker Compose orchestration
- [x] CI pipeline with NDK caching and APK signing
- [x] GitHub Releases on version tags
- [ ] First Phone APK — installable sidecar with pool mode integration
- [ ] OIDC authentication for coordinator API
- [ ] Pre-flight readiness check before group activation
- [ ] Alpha release documentation (setup, hardware guide, model selection, battery safety)

## Phase 2 — Phonon Visual Identity *[Next]*

- [ ] **Phone display visualization engine** — Telemetry-driven, content-agnostic animation framework on the sidecar
  - [ ] Outputs: phone state, token rate, temperature, battery, load
  - [ ] Theme pack contract defined
  - [ ] Engine is workload-aware (state/temperature/rate) NOT information-aware (never sees prompts or responses)
- [ ] **Base theme (solarpunk/Borg fusion)** — Ships with coordinator and APK
  - [ ] Idle: slow breathing pulse, temperature gradient (cool blue→warm orange)
  - [ ] Prefill: sharp brief flash on incoming work
  - [ ] Inference: rhythmic generation pulses synced to token rate
  - [ ] MTP active: stroboscopic double-pulse
  - [ ] Error: red fire/crackle
  - [ ] Battery draining unplugged: amber dimming
  - [ ] Model loading: scanning/tiling progress
  - [ ] Pairing/commissioning: blue-white swirl resolves to steady glow
- [ ] **Web UI rack layout editor** — Drag-and-drop phone tiles to match physical placement
  - [ ] Canvas with grid/snap
  - [ ] Save layout to coordinator config YAML
- [ ] **Coordinated multi-phone visualizations**
  - [ ] Inference wave — ripple propagates across adjacent phones on request
  - [ ] Temperature heatmap — whole rack shows thermal profile at a glance
  - [ ] Error cascade awareness — neighboring phones acknowledge a downed peer
  - [ ] Token pulse sync — idle phones breathe in loose unison, busy phone breaks pattern
- [ ] **Community theme pack system**
  - [ ] Theme pack contract documented
  - [ ] PR-based submission

## Phase 3 — Home Assistant Integration

- [ ] Home Assistant discovers coordinator via mDNS
- [ ] Each phone exposed as a device with sensors: temperature, battery, inference load, model, state
- [ ] Coordinator exposes Prometheus metrics endpoint consumable by HA
- [ ] Automations: route around overheating phones, disable non-critical routing off-hours, notify on error states
- [ ] No account required — purely local

## Phase 4 — Shard Mode

- [ ] Multi-phone model sharding (running larger models across the pool)
- [ ] Dynamic pool/shard mode switching

## Phase 5 — NPU-Accelerated Sharding

- [ ] Cross-phone NPU graph slicing
- [ ] KV cache distribution across phones
- [ ] Activation serialization between NPU memory spaces
- [ ] Production-ready distributed NPU inference

---

*Self-hosted is always free. All software is open source (MIT).*
