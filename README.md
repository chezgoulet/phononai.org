# Phonon AI

**Turn old phones into AI infrastructure. Zero e-waste. Zero cloud dependency.**

Phonon is an open-source system that turns a handful of old Android phones into a private, local AI inference cluster. Donate your old phone, earn token credits. Run your own pool. Or both.

## The Problem

AI inference is expensive, centralized, and generates e-waste. Every year, millions of perfectly capable smartphones end up in drawers or landfills — each one containing an NPU, GPU, and 6–12 GB of RAM that could be running AI models.

## The Solution

Phonon installs on a small coordinator (a Raspberry Pi, an Odroid, or anything on your network) and a fleet of Android phones. The phones self-organize into an inference pool. Your agent frameworks — Hermes, OpenClaw, anything that speaks the OpenAI API — point at Phonon and get local, private, zero-cost inference.

## Three Ways to Use Phonon

### 1. Run Your Own Pool (Free, Always)
Install the coordinator and APK on your own phones. Point your agents at the endpoint. Zero cost, zero cloud dependency, full privacy. Everything is open-source — you own your infrastructure.

### 2. Donate Phones, Earn Credits
Send us your old phone. We wipe it, test it, and add it to the public Phonon pool. You get token credits proportional to the phone's compute value. Use those credits for inference on the public pool — or redeem them for hardware, cooling racks, and cluster kits.

### 3. Subscribe to the Public Pool
Need inference but don't have phones to donate? Pay a flat monthly rate plus metered usage. Significantly cheaper than any cloud AI provider because our hardware is recycled phones that cost us pennies to operate.

## Business Model

- **Self-hosted pool:** Always free, always open-source (Apache 2.0)
- **Phone donation credits:** Fair market value via Swappa/eBay comps, redeemable for compute or hardware
- **Public pool subscription:** Flat monthly rate + metered usage, cheaper than any cloud provider
- **Hardware kits:** Cooling racks, power hubs, USB-C ethernet adapters — everything but the phones
- **E-waste reduction:** Every phone that runs AI instead of filling a landfill is a win

## Cross-Pollination with Methexis

Phonon is the inference layer. [Methexis](https://methexis.app) is the connected knowledge infrastructure for AI agents. Together they form the complete stack:
- Methexis stores your agent's knowledge (facts, memories, context)
- Phonon runs the inference that queries and updates that knowledge
- Both run entirely on your hardware

## License

Apache 2.0 — do what you want with it. The software is free. The hardware is where we make our living.

---

*Built by [Chez LLC](https://chezgoulet.org). Reduce e-waste. Run your own AI.*
