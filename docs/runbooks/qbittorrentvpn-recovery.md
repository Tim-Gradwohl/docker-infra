# qBittorrentVPN Recovery

## Symptoms

* gluetun unhealthy
* DNS failures
* ping 1.1.1.1 fails
* WireGuard shows connected but no traffic

## Root cause

* stale wg0.conf

---

## Manual fix

stk down qbittorrentvpn
rm wireguard-pia/wg0.conf
regenerate config
stk up qbittorrentvpn

Validate:

docker exec qbittorrentvpn_gluetun ping -c1 1.1.1.1

---

## Automated fix

* qb-vpn-refresh
* qb-vpn-watchdog

Detection:

* unhealthy container
* log pattern
* failed connectivity

