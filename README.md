# Phonon

**Turn old Android phones into private AI inference infrastructure.**

Phonon is an open-source system that turns a fleet of Android phones into a local AI inference cluster. The hardware you already own — or the phones gathering dust in a drawer — becomes a private, NPU-accelerated inference pool.

## What it is

A single Go coordinator binary runs on any Linux device on your network. One or more Android phones with the Phonon sidecar APK connect to the coordinator and form an inference pool. The coordinator serves an OpenAI-compatible API — point any agent framework at it and get local, private inference.

## State

**Alpha.** The coordinator runs, phones pair, and inference happens. We need testers, phones, and contributors to get it to beta. Everything is open source and self-hosted.

## Quick start

1. Pull the Docker image for the coordinator
2. Install the APK on one or more Android phones
3. Pair phones to the coordinator via mDNS
4. Point your agents at the API

Full setup takes about 15 minutes.

## License

MIT — fully permissive. Self-hosted is free, always, with no feature limitations. No CLA, no friction.
