# MeTube

## Purpose

MeTube provides a **web UI for yt-dlp**.

Allows:

* downloading videos/audio via browser
* simple URL → download workflow

---

## Container

* `metube`

Image:

* `ghcr.io/alexta69/metube:latest`

---

## Networking

Network:

* `proxy`

Rules:

* no direct port exposure
* all access via Traefik

---

## Routing

Defined via Traefik labels.

Example:

```text id="u7d6ac"
Host(metube.${BASE_DOMAIN})
```

Access:

* LAN: http://metube.${BASE_DOMAIN}
* WAN (if enabled): https://metube.${BASE_DOMAIN}

---

## Service Port

Internal container port:

```text id="nt5c0n"
8081
```

Traefik forwards traffic to this port.

---

## Storage

Bind mount:

```text id="f7bgx2"
/mnt/d/Docker/metube/downloads → /downloads
```

* downloads stored on Windows disk (`D:`)
* persists outside container lifecycle

---

## Operations

### Deploy / update

```bash id="4cf3pd"
stack up metube
```

### Logs

```bash id="9h8x0q"
stack logs metube
```

---

## Exposure Model

* no host ports exposed
* routed via Traefik only
* optional WAN exposure via Cloudflare Tunnel

---

## Security

Recommended:

* apply LAN-only middleware if not needed externally
* optionally protect with Authentik

Example:

```text id="h8x4rj"
${TRAEFIK_AUTH_MIDDLEWARE}
```

---

## Debugging

### Not reachable

Check:

* container running
* attached to `proxy` network
* Traefik labels correct

---

### Downloads fail

Check:

* output directory writable
* disk space available
* yt-dlp upstream issues

---

## Failure Modes

### Accessible externally when not intended

Cause:

* WAN routing enabled
* no middleware restriction

Fix:

* remove Cloudflare DNS / tunnel entry
* or apply LAN-only middleware

---

## Notes

* stateless service (safe to redeploy)
* depends on external sites (YouTube, etc.)
* behavior may change due to upstream changes

---

## References

* Gateway → `gateway/README.md`
* Ingress → `docs/architecture/ingress-cloudflare-traefik.md`
* Auth → `docs/architecture/authentik.md`
* System context → `ai-context.md`

