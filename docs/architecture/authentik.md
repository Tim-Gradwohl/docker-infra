# Authentik

## Model

* Traefik ForwardAuth
* Uses authentik outpost

## Middleware chain

* authentik-forwardauth
* authentik-errors

## Rules

* Never protect authentik itself
* Outpost must route to authentik_proxy

## Critical constraint

HTTPS must be enforced BEFORE auth flow

Fix:

* Cloudflare “Always Use HTTPS”

