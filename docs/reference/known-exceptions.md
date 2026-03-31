# Known Exceptions

This file records intentional deviations from default repo policy.

Its purpose is to help humans and AI agents distinguish:
- intentional exceptions
- accidental drift
- likely policy violations

This file complements:
- `AGENTS.md`
- `docs/policies/compose-contract.md`
- `docs/policies/routing-contract.md`
- `docs/policies/env-contract.md`

---

## How to use this file

Before treating an unusual pattern as a bug or policy violation, check whether it appears here.

Examples of patterns that may be valid only by exception:

- direct `ports:` exposure
- Docker socket mounts
- `privileged: true`
- host networking
- `cap_add`
- services on `proxy` without user-facing routing
- public services without the shared auth middleware
- multiple routers/middleware chains for one stack

If a new exception is introduced, add it here and document it in the relevant stack README.

---

## Exception format

Use this format for each entry:

- stack or component
- exception type
- exact files involved
- why the exception exists
- what risk it introduces
- what guardrails still apply

---

## Current exceptions

#### Stack: adguardhome
- **Exception type:** direct host port exposure for DNS
- **Files:** `apps/adguardhome/compose.yml`, `apps/adguardhome/README.md`
- **Reason:** DNS uses `53/tcp` and `53/udp`, which Traefik does not proxy in the repo’s HTTP routing model
- **Risk:** host-level network exposure outside normal web ingress
- **Guardrails:** only DNS ports are exposed directly; the admin UI is still Traefik-routed; the README documents the DNS role and LAN restriction intent

#### Stack: syncthing
- **Exception type:** direct host port exposure for sync and discovery protocols
- **Files:** `apps/syncthing/compose.yml`, `apps/syncthing/README.md`
- **Reason:** Syncthing device sync and local discovery require real L4 ports that are not handled by Traefik in this setup
- **Risk:** host-level exposure beyond normal HTTP ingress
- **Guardrails:** only the required sync/discovery ports are exposed; the web UI remains Traefik-routed; the Compose file documents the reason and LAN restriction intent

#### Stack: qbittorrentvpn
- **Exception type:** elevated privileges, Docker socket access, and special networking
- **Files:** `apps/qbittorrentvpn/compose.yml`, `apps/qbittorrentvpn/README.md`, `docs/runbooks/qbittorrentvpn-recovery.md`
- **Reason:** VPN enforcement relies on `network_mode: service:gluetun`; WireGuard helpers require extra capabilities; port synchronization mounts the Docker socket for runtime updates
- **Risk:** larger blast radius than a normal app stack due to capability elevation, Docker socket exposure, and shared network namespace behavior
- **Guardrails:** qBittorrent shares the Gluetun network namespace to prevent bypass; the web UI remains Traefik-routed; recovery workflow and operational model are documented

#### Stack: authentik
- **Exception type:** public route without shared auth middleware
- **Files:** `apps/authentik/compose.yml`, `apps/authentik/README.md`
- **Reason:** Authentik must not protect itself with its own ForwardAuth middleware; the outpost path is routed separately to `authentik-proxy`
- **Risk:** auth bootstrap and callback flow can break if middleware is applied incorrectly
- **Guardrails:** the main Authentik route has no shared auth middleware; the outpost path has its own explicit router; the stack README documents this behavior

#### Stack: nextcloud
- **Exception type:** public route without shared auth middleware
- **Files:** `apps/nextcloud/compose.yml`, `apps/nextcloud/README.md`
- **Reason:** native Nextcloud clients and WebDAV need to authenticate against Nextcloud itself; Traefik ForwardAuth in front of the whole route breaks app-compatible login flows
- **Risk:** the public route is no longer protected by the repo-wide Authentik middleware chain at the proxy layer
- **Guardrails:** the route remains HTTPS-only behind Traefik; Nextcloud still requires its own application authentication; the stack README documents why the middleware is intentionally absent

#### Stack: homeassistant
- **Exception type:** public route without shared auth middleware
- **Files:** `apps/homeassistant/compose.yml`, `apps/homeassistant/README.md`
- **Reason:** Home Assistant companion apps, webhooks, and the WebSocket API need to authenticate directly against Home Assistant; Traefik ForwardAuth in front of the whole route would interfere with those client flows
- **Risk:** the public route is no longer protected by the repo-wide Authentik middleware chain at the proxy layer
- **Guardrails:** the route remains HTTPS-only behind Traefik; Home Assistant still requires its own application authentication; the stack README documents the required reverse-proxy `trusted_proxies` configuration

#### Stack: gateway
- **Exception type:** intentional published HTTP(S) ports and Docker socket access
- **Files:** `gateway/compose.yml`, `gateway/README.md`
- **Reason:** Gateway is the designated ingress component; Traefik must publish entrypoint ports and access the Docker provider
- **Risk:** this component has the highest exposure in the repo and broad visibility into routed services
- **Guardrails:** gateway is the only intended public HTTP(S) entrypoint; Docker socket access is read-only; the role and exposure model are documented

---

## Candidate exception categories

These are the most important categories to track.

### 1. Direct port exposure

Use only when:
- the service is intentionally not routed by Traefik
- the protocol is non-HTTP or otherwise intentionally host-exposed
- the reason is documented

Questions to answer:
- why can Traefik not be used?
- which exact ports are exposed?
- is the exposure LAN-only or broader?
- can the scope be narrowed?

### 2. Docker socket access

Use only when:
- the service genuinely needs Docker control or discovery

Questions to answer:
- why does the service need Docker socket access?
- is read-only sufficient?
- is there a lower-trust alternative?

### 3. Elevated privileges

Includes:
- `privileged: true`
- `cap_add`
- host devices
- root-only requirements

Questions to answer:
- what exact capability is needed?
- can the privilege be reduced?
- what is the blast radius?

### 4. Host networking

Use only when:
- there is a documented technical reason

Questions to answer:
- why can normal Docker networking not be used?
- what visibility/exposure changes result?
- what conflicts become possible?

### 5. Public exposure without shared auth

Use only when:
- the app is intentionally public without Authentik
- the reason is documented

Questions to answer:
- is the app meant to be openly accessible?
- is another auth/control mechanism being used?
- is the exposure limited to the intended hostname/path only?

### 6. Multiple routers / special middleware chains

Use only when:
- integration truly requires extra routers or path handling

Questions to answer:
- what router names exist?
- what middleware order matters?
- what breaks if simplified?

---

## Review rules

An exception should remain only if:

- it still has a real technical reason
- the reason is documented
- the risk is understood
- the exception is narrower than the obvious alternatives

If an exception no longer has a valid reason, remove it and align the stack with normal policy.

---

## Definition of done

A new exception is properly documented when:

- the exception type is clear
- exact files are named
- the reason is explicit
- the risk is described
- the remaining guardrails are stated
- the relevant stack README is updated
