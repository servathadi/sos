# Changelog

All notable changes to SOS (Sovereign Operating System) will be documented here.

## [0.1.0] - 2026-02-03

### Added
- **CLI**: `mumega` command with doctor, chat, start, status, version
- **Engine**: Multi-model support (Gemini, Claude, GPT, Grok, Ollama)
- **Resilience**: Circuit breakers, rate limiting, failover router
- **Autonomy**: Dream synthesis, pulse scheduling, coordinator
- **Memory**: Tiered storage with Cloudflare backends
- **Identity**: QNFT system, capability-based access control
- **Errors**: Protocol-level error codes (1xxx-8xxx ranges)
- **Config**: Validation system with `.env.example`
- **Tests**: Unit tests for resilience, CLI, autonomy, dreams
- **Security**: Hardened docker-compose, secret scanning
- **Docs**: OpenClaw learnings, plugin model

### Infrastructure
- PyPI package name: `mumega`
- Python 3.10+ required
- Optional dependencies: gemini, openai, local, full

## [0.1.1] - 2026-02-03

### Added
- **Security**: SSRF protection for external API calls (#47)
- **Security**: Scope-based authorization system (#50)
- **Security**: Ed25519 capability signature verification (#1)
- **Observability**: Prometheus metrics for circuit breakers, rate limiters, dreams, autonomy (#18)
- **Reliability**: Gateway failover with circuit breaker persistence (#15)
- **Testing**: Load tests for rate limiter and circuit breaker (#20)
- **Ops**: Prometheus alerting rules for SOS services (#23)

## [Unreleased]

### Pending
- Additional model provider integrations
