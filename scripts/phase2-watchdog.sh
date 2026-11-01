#!/bin/bash
# phase2-watchdog.sh тАФ fallback ╨┤╨╗╤П ╨д╨░╨╖╤Л 2 (table 150, awg1 -> wg-home -> VPS)
#
# ╨Ч╨Р╨Ф╨Р╨з╨Р: ╨║╨╗╨╕╨╡╨╜╤В╤Л awg1 (10.13.13.0/24) ╤Е╨╛╨┤╤П╤В ╨▓ non-RU ╤З╨╡╤А╨╡╨╖
#   ip rule pref 32745 -> table 150 -> wg-home -> VPS.
# ╨Х╤Б╨╗╨╕ wg-home ╨┐╨╡╤А╨╡╤Б╤В╨░╤С╤В ╤А╨░╨▒╨╛╤В╨░╤В╤М, table 150 ╤Б╤В╨░╨╜╨╛╨▓╨╕╤В╤Б╤П ╤З╤С╤А╨╜╨╛╨╣ ╨┤╤Л╤А╨╛╨╣: ╨┐╨░╨║╨╡╤В╤Л
# ╤Г╤Е╨╛╨┤╤П╤В ╨▓ ╨╕╨╜╤В╨╡╤А╤Д╨╡╨╣╤Б ╨╕ ╨╝╨╛╨╗╤З╨░ ╤В╨╡╤А╤П╤О╤В╤Б╤П. Watchdog ╤Б╨╜╨╕╨╝╨░╨╡╤В ╨┐╤А╨░╨▓╨╕╨╗╨╛ тАФ ╨║╨╗╨╕╨╡╨╜╤В╤Л
# ╨▓╨╛╨╖╨▓╤А╨░╤Й╨░╤О╤В╤Б╤П ╨╜╨░ ╤Б╤В╨░╤А╤Л╨╣ ╨┐╤Г╤В╤М table vpn -> OpenWRT TPROXY -> gost -> SSH -> VPS.
#
# тФАтФА ╨Я╨Ю╨з╨Х╨Ь╨г ╨Ш╨Ь╨Х╨Э╨Э╨Ю ╨Ф╨Т╨Р ╨Я╨а╨Ю╨С╨Р (╨▓╨░╨╢╨╜╨╛╨╡, ╨╕╨╖ ╨╛╨┐╤Л╤В╨░ 2026-10-06) тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА
# 1) ╨Э╨Х╨Ы╨м╨Ч╨п ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╤В╤М ╨▓╨╛╨╖╤А╨░╤Б╤В `wg show latest-handshakes`. Keepalive (25 ╤Б╨╡╨║)
#    ╨Э╨Х ╨╛╨▒╨╜╨╛╨▓╨╗╤П╨╡╤В ╤Н╤В╨╛╤В timestamp тАФ ╨╛╨╜ ╨╛╨▒╨╜╨╛╨▓╨╗╤П╨╡╤В╤Б╤П ╤В╨╛╨╗╤М╨║╨╛ ╨┐╤А╨╕ ╨╛╨▒╨╝╨╡╨╜╨╡ ╨║╨╗╤О╤З╨░╨╝╨╕
#    (~120 ╤Б╨╡╨║) ╨╕╨╗╨╕ ╨┐╤А╨╕ ╨┐╨╡╤А╨╡╨┤╨░╤З╨╡ ╨┤╨░╨╜╨╜╤Л╤Е. ╨Э╨░ ╨┐╤А╨╛╤Б╤В╨╛╨╡ ╨╢╨╕╨▓╨╛╨╣ ╤В╤Г╨╜╨╜╨╡╨╗╤М ╨┤╨░╤С╤В "╤Б╤В╨░╤А╤Г╤О"
#    ╨╝╨╡╤В╨║╤Г. ╨Я╨╡╤А╨▓╨░╤П ╨▓╨╡╤А╤Б╨╕╤П ╤Б╨║╤А╨╕╨┐╤В╨░ ╨╜╨░ ╤Н╤В╨╛╨╝ ╨╛╤Б╨╜╨╛╨▓╨░╨╜╨╕╨╕ ╤Б╨╜╤П╨╗╨░ ╨╢╨╕╨▓╨╛╨╡ ╨┐╤А╨░╨▓╨╕╨╗╨╛.
#
# 2) ╨Э╨Х╨Ы╨м╨Ч╨п ╨┐╨╕╨╜╨│╨╛╨▓╨░╤В╤М 10.88.0.2 (╨░╨┤╤А╨╡╤Б VPS ╨▓ ╤В╤Г╨╜╨╜╨╡╨╗╨╡). ╨Ю╨╜ ╨┐╨╛╨║╤А╤Л╤В AllowedIPs
#    ╨▓╤Б╨╡╨│╨┤╨░, ╨┐╨╛╤Н╤В╨╛╨╝╤Г ╨┐╤А╨╛╨▒╨░ ╤Г╤Б╨┐╨╡╤И╨╜╨░ ╨┤╨░╨╢╨╡ ╨┐╤А╨╕ ╤Б╨╗╨╛╨╝╨░╨╜╨╜╨╛╨╣ ╨╝╨░╤А╤И╤А╤Г╤В╨╕╨╖╨░╤Ж╨╕╨╕ non-RU.
#
# 3) ╨Э╨Х╨Ы╨м╨Ч╨п ╨┐╨╛╨╗╨░╨│╨░╤В╤М╤Б╤П ╨в╨Ю╨Ы╨м╨Ъ╨Ю ╨╜╨░ ICMP. ╨Ш╨Э╨ж╨Ш╨Ф╨Х╨Э╨в 2026-10-06 14:02тАУ14:04:
#    ╨║╨░╨╜╨░╨╗ Beeline/KVANT тЖТ AEZA ╨┤╨░╨╗ ╨▓╤Б╨┐╨╗╨╡╤Б╨║ ╨┐╨╛╤В╨╡╤А╤М ~10% ╨╜╨░ 3 ╨╝╨╕╨╜╤Г╤В╤Л.
#    ╨з╨╡╤А╨╡╨╖ ╤В╤Г╨╜╨╜╨╡╨╗╤М ICMP ╤В╨╡╤А╤П╨╗ 40тАУ50% (╨┐╨░╨║╨╡╤В ╨┐╤А╨╛╤Е╨╛╨┤╨╕╤В ╤В╤Г╨┤╨░ ╨╕ ╨╛╨▒╤А╨░╤В╨╜╨╛, ╨┐╨╛╤В╨╡╤А╨╕
#    ╤Г╨┤╨▓╨░╨╕╨▓╨░╤О╤В╤Б╤П), ╨┐╤А╨╕ ╤Н╤В╨╛╨╝ TCP ╤А╨░╨▒╨╛╤В╨░╨╗: curl ╨╛╤В╨▓╨╡╤З╨░╨╗ HTTP 200/301.
#    ╨б╤В╨░╤А╤Л╨╣ watchdog ╨▓╨╕╨┤╨╡╨╗ "3 ╤Д╨╡╨╣╨╗╨░ ╨┐╨╛╨┤╤А╤П╨┤" ╨╕ ╤Б╨╜╤П╨╗ ╨┐╤А╨░╨▓╨╕╨╗╨╛, ╨▓╨╡╤А╨╜╤Г╨▓ ╨║╨╗╨╕╨╡╨╜╤В╨╛╨▓ ╨╜╨░
#    TCP-╨▓-TCP ╨┐╤Г╤В╤М тАФ ╤В╨╛ ╨╡╤Б╤В╤М ╤Г╤Е╤Г╨┤╤И╨╕╨╗ ╤Б╨╕╤В╤Г╨░╤Ж╨╕╤О ╨╜╨░ ╤А╨╛╨▓╨╜╨╛╨╝ ╨╝╨╡╤Б╤В╨╡.
#
#    ╨Я╨а╨Р╨Т╨Ш╨Ы╨м╨Э╨Р╨п ╨Ы╨Ю╨У╨Ш╨Ъ╨Р: ╤Б╨╜╨╕╨╝╨░╤В╤М ╨┐╤А╨░╨▓╨╕╨╗╨╛ ╤В╨╛╨╗╤М╨║╨╛ ╨╡╤Б╨╗╨╕ ╨Э╨Х ╨Я╨а╨Ю╨и╨Ы╨Ш ╨Ю╨С╨Р ╨Я╨а╨Ю╨С╨Р.
#    ICMP ╨┐╨╛╤В╨╡╤А╤П╨╗╤Б╤П тАФ ╨╜╨╡ ╨╖╨╜╨░╤З╨╕╤В ╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╝╤С╤А╤В╨▓ (╨║╨░╨╜╨░╨╗ ╨║╨░╤З╨░╨╡╤В╤Б╤П ╨┐╨╛╤В╨╡╤А╤М).
#    TCP ╨╛╤В╨▓╨╡╤З╨░╨╡╤В тАФ ╨╖╨╜╨░╤З╨╕╤В ╤В╤А╨░╤Д╨╕╨║ ╨╕╨┤╤С╤В, ╨▓╤Б╤С ╨▓ ╨┐╨╛╤А╤П╨┤╨║╨╡.
#
# 4) ╨Я╤А╨╛╨▒╨░ ╨Ю╨С╨п╨Ч╨Р╨в╨Х╨Ы╨м╨Э╨Ю ╤Б `-I wg-home` / `--interface wg-home`. ╨С╨╡╨╖ ╤Н╤В╨╛╨│╨╛ ╨┐╨░╨║╨╡╤В
#    ╤Г╨╣╨┤╤С╤В ╨┐╨╛ main-╤В╨░╨▒╨╗╨╕╤Ж╨╡ ╤З╨╡╤А╨╡╨╖ vmbr0/Cudy тАФ ╨┐╤А╨╛╨▒╨░ ╨┐╨╛╨║╨░╨╢╨╡╤В "╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╢╨╕╨▓",
#    ╨▓╨╛╨╛╨▒╤Й╨╡ ╨╜╨╡ ╨║╨░╤Б╨░╤П╤Б╤М wg-home.
# тФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФАтФА
#
# ╨Ы╨╛╨│╨╕╨║╨░:
#   ICMP OK                     тЖТ ╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╢╨╕╨▓, ╤Б╤З╤С╤В╤З╨╕╨║╨╕ ╤Б╨▒╤А╨╛╤И╨╡╨╜╤Л
#   ICMP FAIL + TCP OK          тЖТ ╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╢╨╕╨▓ (ICMP ╨┐╨╛╤В╨╡╤А╤П╨╗╤Б╤П), ╤Б╤З╤С╤В╤З╨╕╨║╨╕ ╤Б╨▒╤А╨╛╤И╨╡╨╜╤Л
#   ICMP FAIL + TCP FAIL        тЖТ ╤Б╤З╨╕╤В╨░╨╡╨╝ ╤Д╨╡╨╣╨╗ (╨╜╤Г╨╢╨╜╨╛ FAIL_THRESHOLD ╨┐╨╛╨┤╤А╤П╨┤)
#   ╨┐╤А╨░╨▓╨╕╨╗╨╛ ╤Г╨╢╨╡ ╨▓ ╨╜╤Г╨╢╨╜╨╛╨╝ ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╨╕ тЖТ ╨╜╨╕╤З╨╡╨│╨╛ ╨╜╨╡ ╨┤╨╡╨╗╨░╤В╤М
#   ╨╕╨╜╤В╨╡╤А╤Д╨╡╨╣╤Б wg-home ╨╛╤В╤Б╤Г╤В╤Б╤В╨▓╤Г╨╡╤В  тЖТ SKIP
#   cooldown                      тЖТ ╨╜╨╡ ╨┤╤С╤А╨│╨░╤В╤М ╤З╨░╤Й╨╡

set -u

LOG=/var/log/phase2-watchdog.log
STATE=/run/phase2-watchdog.state          # active | failsafe
FAILF=/run/phase2-watchdog.fail           # ╤Б╤З╤С╤В╤З╨╕╨║ ╨╜╨╡╤Г╨┤╨░╤З╨╜╤Л╤Е ╨Ф╨Т╨Ю╨Щ╨Э╨л╨е ╨┐╤А╨╛╨▒ ╨┐╨╛╨┤╤А╤П╨┤
COOLD=/run/phase2-watchdog.cooldown       # unixtime ╨┐╨╛╤Б╨╗╨╡╨┤╨╜╨╡╨│╨╛ ╨┐╨╡╤А╨╡╨║╨╗╤О╤З╨╡╨╜╨╕╤П

IFACE=wg-home
PROBE_ICMP_DST=8.8.8.8      # non-RU: ╨┐╨╛╨║╤А╤Л╤В AllowedIPs 0.0.0.0/0, ╨╕╨┤╤С╤В ╨▓ ╤В╤Г╨╜╨╜╨╡╨╗╤М
PROBE_ICMP_TIMEOUT=2
PROBE_TCP_URL=https://1.1.1.1
PROBE_TCP_TIMEOUT=15
TABLE=150
RULE_PREF=32745
RULE_SRC=10.13.13.0/24
FAIL_THRESHOLD=3
COOLDOWN_SEC=300

log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }

alert() {
    if [ -x /usr/local/bin/hids-alert.sh ] && [ -r /etc/hids/alert.env ]; then
        /usr/local/bin/hids-alert.sh "$1" phase2 >/dev/null 2>&1 || true
    fi
    log "ALERT: $1"
}

rule_exists() {
    ip rule show | grep -qE "^${RULE_PREF}:.*from ${RULE_SRC} lookup ${TABLE}"
}
rule_del() { ip rule del pref "$RULE_PREF" 2>/dev/null || true; }
rule_add() { ip rule add from "$RULE_SRC" lookup "$TABLE" pref "$RULE_PREF" 2>/dev/null || true; }

in_cooldown() {
    local now last
    now=$(date +%s)
    last=$(cat "$COOLD" 2>/dev/null || echo 0)
    [ $((now - last)) -lt "$COOLDOWN_SEC" ]
}
set_cooldown() { date +%s >"$COOLD"; }

fails() { cat "$FAILF" 2>/dev/null || echo 0; }
set_fails() { echo "$1" >"$FAILF"; }

# ╨Я╤А╨╛╨▒╨░ A: ICMP ╤З╨╡╤А╨╡╨╖ ╤В╤Г╨╜╨╜╨╡╨╗╤М.
probe_icmp() {
    ping -c 1 -W "$PROBE_ICMP_TIMEOUT" -I "$IFACE" -q "$PROBE_ICMP_DST" >/dev/null 2>&1
}

# ╨Я╤А╨╛╨▒╨░ B: TCP ╤З╨╡╤А╨╡╨╖ ╤В╤Г╨╜╨╜╨╡╨╗╤М. ╨Т╨╛╨╖╨▓╤А╨░╤Й╨░╨╡╤В 0 ╨┐╤А╨╕ ╨╗╤О╨▒╨╛╨╝ ╨▓╨░╨╗╨╕╨┤╨╜╨╛╨╝ HTTP-╨╛╤В╨▓╨╡╤В╨╡.
probe_tcp() {
    local code
    code=$(curl -4 -s -o /dev/null -w '%{http_code}' \
            --max-time "$PROBE_TCP_TIMEOUT" \
            --interface "$IFACE" "$PROBE_TCP_URL" 2>/dev/null)
    case "$code" in
        200|301|302|303|307|308) return 0 ;;
        *) return 1 ;;
    esac
}

main() {
    if ! ip link show "$IFACE" >/dev/null 2>&1; then
        log "SKIP: ╨╕╨╜╤В╨╡╤А╤Д╨╡╨╣╤Б $IFACE ╨╛╤В╤Б╤Г╤В╤Б╤В╨▓╤Г╨╡╤В тАФ ╨╜╨╕╤З╨╡╨│╨╛ ╨╜╨╡ ╤В╤А╨╛╨│╨░╤О"
        return 0
    fi

    if probe_icmp; then
        set_fails 0
        if rule_exists; then
            [ "$(cat "$STATE" 2>/dev/null)" = "active" ] || echo "active" >"$STATE"
            log "OK: ICMP ${PROBE_ICMP_DST} ╨┐╤А╨╛╤И╤С╨╗, ╨┐╤А╨░╨▓╨╕╨╗╨╛ ╨╜╨░ ╨╝╨╡╤Б╤В╨╡"
        else
            if in_cooldown; then
                log "╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╢╨╕╨▓ (ICMP OK), ╨┐╤А╨░╨▓╨╕╨╗╨░ ╨╜╨╡╤В, ╨╜╨╛ cooldown тАФ ╨╜╨╡ ╨▓╨╛╨╖╨▓╤А╨░╤Й╨░╤О"
            else
                rule_add
                if rule_exists; then
                    echo "active" >"$STATE"; set_cooldown
                    log "╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╢╨╕╨▓ (ICMP OK) тАФ ╨┐╤А╨░╨▓╨╕╨╗╨╛ pref $RULE_PREF ╨Т╨Ю╨Ч╨Т╨а╨Р╨й╨Х╨Э╨Ю"
                    alert "wg-home ╤А╨░╨▒╨╛╤В╨░╨╡╤В (ICMP OK). ╨Я╤А╨░╨▓╨╕╨╗╨╛ pref $RULE_PREF ╨▓╨╛╨╖╨▓╤А╨░╤Й╨╡╨╜╨╛ тАФ ╨║╨╗╨╕╨╡╨╜╤В╤Л awg1 ╤Б╨╜╨╛╨▓╨░ ╤З╨╡╤А╨╡╨╖ VPS ╨╜╨░╨┐╤А╤П╨╝╤Г╤О."
                else
                    log "╨Ю╨и╨Ш╨С╨Ъ╨Р: ╨╜╨╡ ╤Г╨┤╨░╨╗╨╛╤Б╤М ╨┤╨╛╨▒╨░╨▓╨╕╤В╤М ip rule pref $RULE_PREF"
                fi
            fi
        fi
        return 0
    fi

    # ICMP ╨╜╨╡ ╨┐╤А╨╛╤И╤С╨╗. ╨а╨╡╤И╨░╨╡╤В TCP.
    if probe_tcp; then
        set_fails 0
        if rule_exists; then
            [ "$(cat "$STATE" 2>/dev/null)" = "active" ] || echo "active" >"$STATE"
            log "OK: ICMP ╨┐╨╛╤В╨╡╤А╤П╨╜, ╨╜╨╛ TCP ╤З╨╡╤А╨╡╨╖ $IFACE ╤А╨░╨▒╨╛╤В╨░╨╡╤В тАФ ╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╢╨╕╨▓, ╨┐╤А╨░╨▓╨╕╨╗╨╛ ╨╜╨░ ╨╝╨╡╤Б╤В╨╡"
        else
            if in_cooldown; then
                log "╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╢╨╕╨▓ (TCP OK), ╨┐╤А╨░╨▓╨╕╨╗╨░ ╨╜╨╡╤В, ╨╜╨╛ cooldown тАФ ╨╜╨╡ ╨▓╨╛╨╖╨▓╤А╨░╤Й╨░╤О"
            else
                rule_add
                if rule_exists; then
                    echo "active" >"$STATE"; set_cooldown
                    log "╤В╤Г╨╜╨╜╨╡╨╗╤М ╨╢╨╕╨▓ (TCP OK) тАФ ╨┐╤А╨░╨▓╨╕╨╗╨╛ pref $RULE_PREF ╨Т╨Ю╨Ч╨Т╨а╨Р╨й╨Х╨Э╨Ю"
                    alert "wg-home ╤А╨░╨▒╨╛╤В╨░╨╡╤В (TCP OK). ╨Я╤А╨░╨▓╨╕╨╗╨╛ pref $RULE_PREF ╨▓╨╛╨╖╨▓╤А╨░╤Й╨╡╨╜╨╛ тАФ ╨║╨╗╨╕╨╡╨╜╤В╤Л awg1 ╤Б╨╜╨╛╨▓╨░ ╤З╨╡╤А╨╡╨╖ VPS ╨╜╨░╨┐╤А╤П╨╝╤Г╤О."
                else
                    log "╨Ю╨и╨Ш╨С╨Ъ╨Р: ╨╜╨╡ ╤Г╨┤╨░╨╗╨╛╤Б╤М ╨┤╨╛╨▒╨░╨▓╨╕╤В╤М ip rule pref $RULE_PREF"
                fi
            fi
        fi
        return 0
    fi

    # ╨Ю╨▒╨╡ ╨┐╤А╨╛╨▒╤Л ╨┐╤А╨╛╨▓╨░╨╗╨╕╨╗╨╕╤Б╤М тАФ ╤Б╤З╨╕╤В╨░╨╡╨╝ ╨╜╨░╤Б╤В╨╛╤П╤Й╨╕╨╣ ╤Д╨╡╨╣╨╗.
    local n
    n=$(($(fails) + 1))
    set_fails "$n"
    log "╨Ф╨Т╨Ю╨Щ╨Э╨Ю╨Щ ╨д╨Х╨Щ╨Ы (ICMP ${PROBE_ICMP_DST} ╨╕ TCP ${PROBE_TCP_URL} ╨╜╨╡ ╨┐╤А╨╛╤И╨╗╨╕) тАФ ╨┐╨╛╨┤╤А╤П╨┤: ${n}/${FAIL_THRESHOLD}"

    [ "$n" -ge "$FAIL_THRESHOLD" ] || return 0

    if rule_exists; then
        if in_cooldown; then
            log "  ╨┐╤А╨░╨▓╨╕╨╗╨╛ pref $RULE_PREF ╨╡╤Б╤В╤М, ╨╜╨╛ cooldown ╨░╨║╤В╨╕╨▓╨╡╨╜ тАФ ╨╜╨╡ ╤В╤А╨╛╨│╨░╤О"
            return 0
        fi
        rule_del
        if ! rule_exists; then
            echo "failsafe" >"$STATE"
            set_cooldown
            set_fails 0
            log "╨┐╤А╨░╨▓╨╕╨╗╨╛ pref $RULE_PREF ╨б╨Э╨п╨в╨Ю тАФ ╨║╨╗╨╕╨╡╨╜╤В╤Л awg1 ╨▓╨╡╤А╨╜╤Г╨╗╨╕╤Б╤М ╨╜╨░ ╨┐╤Г╤В╤М ╤З╨╡╤А╨╡╨╖ OpenWRT"
            alert "wg-home ╨Э╨Х ╨а╨Р╨С╨Ю╨в╨Р╨Х╨в (${n} ╨┤╨▓╨╛╨╣╨╜╤Л╤Е ╤Д╨╡╨╣╨╗╨░: ICMP+TCP). ╨Я╤А╨░╨▓╨╕╨╗╨╛ pref $RULE_PREF ╤Б╨╜╤П╤В╨╛ тАФ ╨║╨╗╨╕╨╡╨╜╤В╤Л awg1 ╨▓╨╡╤А╨╜╤Г╨╗╨╕╤Б╤М ╨╜╨░ ╨┐╤Г╤В╤М ╤З╨╡╤А╨╡╨╖ OpenWRT/gost."
        else
            log "╨Ю╨и╨Ш╨С╨Ъ╨Р: ╨╜╨╡ ╤Г╨┤╨░╨╗╨╛╤Б╤М ╤Б╨╜╤П╤В╤М ip rule pref $RULE_PREF"
        fi
    else
        [ "$(cat "$STATE" 2>/dev/null)" = "failsafe" ] || echo "failsafe" >"$STATE"
        log "╨┐╤А╨░╨▓╨╕╨╗╨░ ╨╜╨╡╤В, ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╨╡ failsafe"
    fi
    return 0
}

main
