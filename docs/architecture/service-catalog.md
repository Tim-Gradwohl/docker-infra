# Service catalog generator

## Purpose

Generate a shared service catalog from Cloudflare Tunnel remote-managed ingress rules.

This keeps Cloudflare API credentials out of application stacks and produces a local JSON artifact that the landing stack and other apps can read safely.

## Design

Flow:

Cloudflare Tunnel API -> `bin/generate-service-catalog` -> `~/stacks/shared/service-catalog/services.json` -> landing page and other consumers

Authoritative ownership:

- Cloudflare = which public services are published
- repo metadata file = how services are presented to humans
- consumer apps = read-only consumers of the generated artifact

## Script location

- `bin/generate-service-catalog`

## Output location

Default:

- `~/stacks/shared/service-catalog/services.json`

Override with:

- `CF_SERVICE_CATALOG_OUTPUT`

## Metadata location

Recommended source-controlled metadata path:

- `apps/landing/services.meta.json`

Default metadata lookup:

- `~/stacks/apps/landing/services.meta.json`

Override with:

- `CF_SERVICE_CATALOG_META`

## Required environment

By default, the script loads missing variables from:

- `shared/.env.secrets`

Override that env file path with:

- `CF_SERVICE_CATALOG_ENV_FILE`

Explicit process environment variables still win over values loaded from the env file.

Required variables:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Optional:

- `CF_SERVICE_CATALOG_ENV_FILE` -> path to an env file used to populate missing variables
- `CF_SERVICE_CATALOG_CHANGE_LOG` -> path to an append-only change log for added/removed hostnames
- `CF_SERVICE_CATALOG_META` -> path to metadata JSON keyed by hostname
- `CF_SERVICE_CATALOG_OUTPUT` -> output path for generated catalog
- `CF_SERVICE_CATALOG_TIMEOUT` -> request timeout in seconds

## Example metadata file

Use a separate metadata file to curate labels, icons, grouping, and sort order without putting presentation concerns into Cloudflare.

```json
{
  "grafana.example.com": {
    "name": "Grafana",
    "description": "Metrics and dashboards",
    "icon": "grafana",
    "category": "observability",
    "order": 30
  },
  "immich.example.com": {
    "name": "Immich",
    "description": "Photos and videos",
    "icon": "camera",
    "category": "media",
    "order": 40
  }
}
```

## Cron example

Run every 10 minutes as the same operator account that already manages the repo checkout:

```cron
*/10 * * * * mkdir -p /home/tim/stacks/state/logs && cd /home/tim/stacks && /usr/bin/env \
  CF_SERVICE_CATALOG_META=/home/tim/stacks/apps/landing/services.meta.json \
  CF_SERVICE_CATALOG_OUTPUT=/home/tim/stacks/shared/service-catalog/services.json \
  /usr/bin/python3 /home/tim/stacks/bin/generate-service-catalog \
  >> /home/tim/stacks/state/logs/service-catalog.log 2>&1
```

This relies on the script's default `shared/.env.secrets` lookup. If secrets live elsewhere, set `CF_SERVICE_CATALOG_ENV_FILE` in the cron environment.
The script skips rewriting the JSON file when the catalog content is unchanged.
When the catalog changes, it appends a hostname-level summary to `state/logs/service-catalog-changes.log` by default.

## Consumer mount example

Mount the shared directory read-only into the landing stack or any other consumer:

```yaml
services:
  landing:
    volumes:
      - /home/tim/stacks/shared/service-catalog:/shared/service-catalog:ro
```

The consumer then reads:

- `/shared/service-catalog/services.json`

## JSON contract

Example output:

```json
{
  "generated_at": "2026-03-21T12:00:00+00:00",
  "source": "cloudflare_tunnel_remote_config",
  "account_id": "...",
  "service_count": 2,
  "tunnel_count": 1,
  "services": [
    {
      "id": "grafana-example-com",
      "name": "Grafana",
      "hostname": "grafana.example.com",
      "url": "https://grafana.example.com",
      "service": "https://traefik:443",
      "tunnel_id": "...",
      "tunnel_name": "homelab",
      "tunnel_status": "healthy",
      "source": "cloudflare",
      "published": true,
      "description": "Metrics and dashboards",
      "icon": "grafana",
      "category": "observability",
      "order": 30,
      "tags": [],
      "notes": null
    }
  ],
  "errors": []
}
```

## Why this model

This pattern avoids a live dependency on the Cloudflare API inside the landing app and gives you a stable, inspectable last-known-good artifact in a shared location.

## Practical next steps

1. Add `apps/landing/services.meta.json` for curated titles, icons, categories, and order.
2. Mount `/home/tim/stacks/shared/service-catalog` read-only into the landing stack.
3. Make the landing UI read `/shared/service-catalog/services.json`.
4. Add a small freshness warning in the UI using `generated_at`.
5. Later, enrich the generator with DNS validation.
6. After that, add a Traefik cross-check so you can detect published routes that do not have a matching router.
