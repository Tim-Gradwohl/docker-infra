# Cloudflared (Cloudflare Tunnel)

## Purpose

Provides **secure external access** to services without exposing ports.

Responsibilities:

* establish outbound tunnel to Cloudflare
* route public traffic to Traefik
* eliminate need for port forwarding

---

## Architecture

Traffic flow:

Internet
→ Cloudflare Edge
→ Cloudflare Tunnel
→ `cloudflared` container
→ Traefik (`gateway_traefik`)
→ service

Key property:

* **no inbound ports required on router**

---

## Container

* `cloudflared`

Network:

* `proxy`

---

## Mode

Token-based tunnel (remote-managed)

Startup command:

```text id="l9s1h4"
tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
```

---

## Configuration

### Location

```text id="gsy6n3"
/home/tim/stacks/apps/cloudflared/
```

Files:

* `compose.yml`
* `config.yml` (may be legacy / partially used)
* `credentials.json` (if present)
* `cert.pem`

---

## Ingress Model

Managed in **Cloudflare Zero Trust dashboard**.

Each public service requires:

1. Cloudflare DNS record
2. Tunnel ingress rule
3. Matching Traefik router

Default behavior:

* deny all (404)

---

## Origin Target

Cloudflared forwards to:

```text id="dyb09k"
https://gateway_traefik:443
```

Notes:

* runs inside Docker network (`proxy`)
* uses internal TLS

Important:

* `noTLSVerify=true` is used to allow Traefik default cert internally

---

## Headers

Cloudflared injects:

```text id="p3o5hp"
X-Forwarded-Proto: https
```

This is critical for:

* Authentik
* correct redirect behavior

---

## Operations

### Deploy / restart

```bash id="jrl22l"
stack up cloudflared
```

Force recreate:

```bash id="4i4y58"
docker compose -f ~/stacks/apps/cloudflared/compose.yml up -d --force-recreate
```

### Logs

```bash id="1lq4o2"
docker logs cloudflared --tail=200
```

---

## Debugging

### Tunnel not working

Check logs:

```bash id="j6m0l9"
docker logs cloudflared | grep -i error
```

Look for:

* connection failures
* authentication errors

---

### Service not reachable externally

Check:

1. Cloudflare DNS record exists
2. Tunnel ingress rule exists
3. Traefik router exists
4. service reachable internally

---

### Internal connectivity test

```bash id="tq4r2u"
docker run --rm -it --network proxy curlimages/curl:8.12.1 \
  curl -vk https://gateway_traefik:443 -H "Host: <hostname>"
```

---

## Security Model

* outbound-only tunnel (no open ports)
* Cloudflare handles edge TLS
* access control enforced via:

  * Authentik (Traefik)
  * Cloudflare (optional)

---

## Failure Modes

### Tunnel connected but routing fails

Likely:

* missing ingress rule
* wrong hostname
* missing Traefik router

---

### Auth issues (400 / redirect loop)

Cause:

* HTTP/HTTPS mismatch

Fix:

* enable Cloudflare “Always Use HTTPS”

---

## Notes

* Cloudflare dashboard is **source of truth for ingress**
* Local config.yml may be partially unused
* Tunnel uses allowlist model (explicit hostnames only)

---

## References

* Gateway → `gateway/README.md`
* Auth → `docs/architecture/authentik.md`
* Ingress → `docs/architecture/ingress-cloudflare-traefik.md`
* Debug → `docs/runbooks/`
* System context → `ai-context.md`

