# Phonon Roadmap

## Phase 1 — Pool Mode (Alpha) *[Current — v0.0.1]*

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
  - [ ] Credits for accepted themes
  - [ ] Future: marketplace

## Phase 3 — Home Assistant Integration

- [ ] Home Assistant discovers coordinator via mDNS
- [ ] Each phone exposed as a device with sensors: temperature, battery, inference load, model, state
- [ ] Coordinator exposes Prometheus metrics endpoint consumable by HA
- [ ] Automations: route around overheating phones, disable non-critical routing off-hours, notify on error states
- [ ] No phononai.org account required — purely local

## Phase 4 — Business Model & Infrastructure

- [ ] **phononai.org website** — Static site: project explainer, donation model, subscription tiers
- [ ] **Donation pipeline** — Intake, testing, commissioning, credit issuance
  - [ ] Fair market value via Swappa/eBay comps
  - [ ] Per-phone case-by-case credit assignment
  - [ ] Credit offsets usage overage (monthly subscription still due)
- [ ] **Public pool metering** — Authentik multi-tenancy + token tracking + Stripe billing
  - [ ] Flat $9/month Basic tier
  - [ ] Overage at cost+margin
  - [ ] Priority scheduling for donors
- [ ] **Phonon + Methexis integration** — Inference layer + knowledge infrastructure, fully self-hosted
- [ ] **Hardware kits** — Cooling racks, power hubs, USB-C ethernet — everything but the phones

## Phase 5 — Shard Mode

- [ ] prima.cpp integration for CPU-based pipeline parallelism
- [ ] Multi-phone model sharding (30B+ models across the pool)
- [ ] Dynamic pool↔shard mode switching

## Phase 6 — NPU-Accelerated Sharding (The Moat)

- [ ] Cross-phone NPU graph slicing
- [ ] KV cache distribution across phones
- [ ] Activation serialization between NPU memory spaces
- [ ] Production-ready distributed NPU inference

---

*Self-hosted pool is always free. phononai.org funds development and operations.*
