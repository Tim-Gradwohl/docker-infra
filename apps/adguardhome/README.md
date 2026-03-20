# AdGuard Home

## Purpose

AdGuard Home provides:

* network-wide DNS filtering
* authoritative DNS for LAN
* internal domain resolution (split DNS)

It is the **DNS authority for all LAN traffic**.

---

## Architecture

LAN clients
→ AdGuard (DNS)
→ resolve `*.${LAN_DOMAIN}` → host IP
→ Traefik
→ service

Key property:

* enables **internal routing via hostnames**
* avoids direct IP-based access

---

## Container

* `adguardhome`

---

## Ports (host)

Exposed directly on host:

* 53/tcp
* 53/udp

Important:

* DNS cannot be proxied through Traefik
* must be reachable directly

---

## Security Model

* Port 53 restricted to LAN:

  * `192.168.188.0/24`
* No WAN exposure
* Controlled via Windows Firewall

---

## DNS Configuration

### Internal zone

```text id="g3b4ff"
*.${LAN_DOMAIN} → 192.168.188.23
```

Result:

* all internal services resolve to host
* Traefik handles routing

---

### Router setup

* IPv4 DNS → AdGuard (correct)
* IPv6 DNS → FRITZ!Box (not yet aligned)

TODO:

* align IPv6 DNS to AdGuard

---

## Admin Interface

Access via Traefik:

```text id="avavbh"
http://adguard.${LAN_DOMAIN}
```

Routing:

* defined via container labels
* no separate helper container

---

## Storage

Bind mounts:

```text id="q4zq2p"
/home/tim/stacks/apps/adguardhome/data/work
/home/tim/stacks/apps/adguardhome/data/conf
```

Mapped to:

* `/opt/adguardhome/work`
* `/opt/adguardhome/conf`

---

## Operations

### Deploy / update

```bash id="8g8k0c"
stack up adguardhome
```

### Logs

```bash id="5mtt6y"
stack logs adguardhome
```

---

## Debugging

### DNS not resolving

Check:

* container running
* port 53 reachable
* client DNS set to host IP
* firewall allows LAN access

---

### Service hostname not working

Check:

* DNS rewrite exists
* hostname resolves to correct IP:

```bash id="z8q0zk"
nslookup <service>.${LAN_DOMAIN}
```

---

### Routing works but DNS fails

Cause:

* DNS misconfiguration, not Traefik

---

## Failure Modes

### DNS bypass

Symptom:

* some clients resolve externally instead of AdGuard

Cause:

* IPv6 DNS still pointing to router

Fix:

* configure router to use AdGuard for IPv6

---

### Wrong IP resolution

Cause:

* incorrect rewrite rule

Fix:

* verify wildcard rule

---

## Notes

* AdGuard is **critical for internal routing**
* If DNS fails → entire system appears broken
* Always debug DNS before Traefik for hostname issues

---

## References

* Gateway → `gateway/README.md`
* Networking → `docs/architecture/networking.md`
* Ingress → `docs/architecture/ingress-cloudflare-traefik.md`
* Debug → `docs/runbooks/`
* System context → `ai-context.md`

