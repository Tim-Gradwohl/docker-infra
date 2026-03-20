# Immich

## Purpose

Self-hosted photo and video management service.

Provides:

* photo/video backup
* gallery UI
* AI-powered search (machine learning container)

---

## Components

* `immich_server`
* `immich_postgres`
* `immich_redis`
* `immich_machine_learning`

---

## Networking

Networks:

* `internal` → database + service communication
* `proxy` → Traefik routing

Rules:

* No ports exposed directly
* All access via Traefik

---

## Routing

Defined via Traefik labels on `immich_server`.

Example:

```text
Host(photos.${BASE_DOMAIN})
```

Access:

* LAN: http://photos.${BASE_DOMAIN}
* WAN (if enabled via Cloudflare): https://photos.${BASE_DOMAIN}

---

## Storage

Uses Docker named volumes:

* `immich_immich_data`
* `immich_immich_pgdata`
* `immich_model-cache`

Location:

* stored inside Docker disk (WSL2 → docker_data.vhdx)

---

## Environment

Requires secrets from:

```text
shared/.env.secrets
```

Critical variables:

* DB_USERNAME
* DB_PASSWORD
* DB_DATABASE_NAME

Compose uses fail-fast:

```text
${VAR:?set in shared/.env.secrets}
```

---

## Operations

### Deploy / update

```bash
stack up immich
```

### Logs

```bash
stack logs immich
```

---

## Exposure Model

* Port 2283 is NOT exposed
* All traffic flows through Traefik
* Host-based routing only

---

## Temporary Changes (known)

* Authentik middleware may be disabled temporarily for testing

Check:

* `apps/immich/compose.yml`

---

## Failure Modes

### Service not reachable

Check:

* container running
* attached to `proxy` network
* Traefik labels correct

---

### Database issues

Check:

* postgres container healthy
* env variables correctly injected

---

## Notes

* Immich is stateful → data integrity important
* Always backup before major changes:

  ```bash
  cd ~/stacks/apps/immich
  stackbackup
  ```

---

## References

* Gateway → `gateway/README.md`
* Auth → `docs/architecture/authentik.md`
* Deployment → `docs/runbooks/deployments.md`
* System context → `ai-context.md`

