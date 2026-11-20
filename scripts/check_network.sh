#!/usr/bin/env bash
# =============================================================
#  Pothole Pi - connectivity check. Run from any machine on the LAN
#  (the Pi, the Linux PC, a laptop) to see what can reach what.
#
#     bash scripts/check_network.sh --car 192.168.1.50 --server 192.168.1.100
#  Either option can be omitted. Needs curl.
# =============================================================
set -uo pipefail
CAR=""; SERVER=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --car) CAR="${2:?}"; shift ;;
    --server) SERVER="${2:?}"; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done
[[ -z "$CAR$SERVER" ]] && { sed -n '2,8p' "$0"; exit 1; }

ok()   { printf '  \033[32m✔\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✘\033[0m %s\n' "$1"; FAILED=1; }
FAILED=0

check() {   # name url
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 4 "$2")
  if [[ "$code" == "200" ]]; then ok "$1  ($2)"; else fail "$1  ($2) -> ${code/000/no answer}"; fi
}

if [[ -n "$SERVER" ]]; then
  echo "Server $SERVER:8000"
  check "API"        "http://$SERVER:8000/api/stats"
  check "map page"   "http://$SERVER:8000/"
  live=$(curl -s --max-time 4 "http://$SERVER:8000/api/telemetry/latest" || true)
  if echo "$live" | grep -q '"online":true'; then ok "car is sending telemetry to the server"
  else fail "no live telemetry from the car (car off, wrong POTHOLEPI_SERVER_URL, or firewall)"; fi
fi

if [[ -n "$CAR" ]]; then
  echo "Car $CAR:8080"
  check "health"     "http://$CAR:8080/health"
  check "snapshot"   "http://$CAR:8080/snapshot.jpg"
  status=$(curl -s --max-time 4 "http://$CAR:8080/api/status" || true)
  if [[ -n "$status" ]]; then
    echo "$status" | grep -q '"fix":true'       && ok "GPS fix"             || fail "no GPS fix (normal indoors)"
    echo "$status" | grep -q '"reachable":true' && ok "car -> server OK"    || fail "car cannot reach the server"
    echo "$status" | grep -q '"source":"picamera2"\|"source":"opencv"\|"source":"test-pattern"' \
      && ok "camera running" || fail "camera not running (see /api/status camera.error)"
  fi
fi

echo
if [[ $FAILED -eq 0 ]]; then echo "All checks passed."; else
  echo "Some checks failed. 'no answer' usually means a wrong IP, the service not running,"
  echo "a firewall, or Wi-Fi client isolation (devices can't see each other). See docs/SETUP.md."
fi
exit $FAILED
