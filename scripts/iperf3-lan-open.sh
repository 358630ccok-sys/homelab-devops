#!/bin/bash
# iperf3-lan-open.sh тАФ ╨▓╤А╨╡╨╝╨╡╨╜╨╜╨╛╨╡ ╨╛╤В╨║╤А╤Л╤В╨╕╨╡ ╨┐╨╛╤А╤В╨░ 5201 ╨┤╨╗╤П ╨Ы╨Ю╨Ъ╨Р╨Ы╨м╨Э╨л╨е ╤Б╨╡╤В╨╡╨╣
# ╨╜╨░ ╨▓╤А╨╡╨╝╤П ╨╖╨░╨╝╨╡╤А╨░ iperf3 (╤В╨╡╨╗╨╡╤Д╨╛╨╜ тЖТ Proxmox ╨┐╨╛ Wi-Fi/LAN, ╨╗╨╛╨║╨░╨╗╨╕╨╖╤Г╨╡╤В ╤Г╨╖╨║╨╛╨╡ ╨╝╨╡╤Б╤В╨╛).
#
# ╨Ч╨░╨┐╤Г╤Б╨║:
#   /root/proxmox-local/iperf3-lan-open.sh open    # ╨╛╤В╨║╤А╤Л╤В╤М
#   /root/proxmox-local/iperf3-lan-open.sh close   # ╨╖╨░╨║╤А╤Л╤В╤М (╨┐╨╛ ╤Г╨╝╨╛╨╗╤З╨░╨╜╨╕╤О ╤З╨╕╤Б╤В╨╛)
#
# ╨Т╨Р╨Ц╨Э╨Ю: ╨┐╤А╨░╨▓╨╕╨╗╨░ ╨Э╨Х ╤Б╨╛╤Е╤А╨░╨╜╤П╤О╤В╤Б╤П ╨▓ /etc/iptables (netfilter-persistent save
# ╨╜╨╡ ╨▓╤Л╨╖╤Л╨▓╨░╨╡╤В╤Б╤П) ╨╕ ╨╢╨╕╨▓╤Г╤В ╤В╨╛╨╗╤М╨║╨╛ ╨┤╨╛ ╨┐╨╡╤А╨╡╨╖╨░╨│╤А╤Г╨╖╨║╨╕ ╨╕╨╗╨╕ `close`.
# ╨Я╤А╨░╨▓╨╕╨╗╨░ ╨┐╨╛╨╝╨╡╤З╨╡╨╜╤Л ╨║╨╛╨╝╨╝╨╡╨╜╤В╨░╤А╨╕╨╡╨╝ IPERF3-TEMP тАФ ╨╕╤Е ╨╗╨╡╨│╨║╨╛ ╨╜╨░╨╣╤В╨╕ ╨╕ ╤Г╨┤╨░╨╗╨╕╤В╤М.
set -u

SUBNETS=(192.168.10.0/24 192.168.20.0/24 172.16.0.0/12 10.13.13.0/24)

close_rules() {
    # iptables 1.8.9 legacy ╨╜╨╡ ╨┐╨╛╨┤╨┤╨╡╤А╨╢╨╕╨▓╨░╨╡╤В `-S INPUT --line-numbers`,
    # ╨┐╨╛╤Н╤В╨╛╨╝╤Г ╨╜╨╛╨╝╨╡╤А╨░ ╤Б╤В╤А╨╛╨║ ╨▒╨╡╤А╤С╨╝ ╨╕╨╖ `-L ... --line-numbers`.
    local nums
    nums=$(iptables -L INPUT -n --line-numbers | grep IPERF3-TEMP | awk '{print $1}' | sort -rn)
    local n
    for n in $nums; do
        iptables -D INPUT "$n" 2>/dev/null || true
    done
}

case "${1:-}" in
  open)
    for s in "${SUBNETS[@]}"; do
      iptables -C INPUT -s "$s" -p tcp --dport 5201 -m comment --comment IPERF3-TEMP -j ACCEPT 2>/dev/null \
        || iptables -I INPUT 12 -s "$s" -p tcp --dport 5201 -m comment --comment IPERF3-TEMP -j ACCEPT
    done
    echo "╨┐╨╛╤А╤В 5201 ╨╛╤В╨║╤А╤Л╤В ╨┤╨╗╤П: ${SUBNETS[*]}"
    iptables -L INPUT -n | grep -c IPERF3-TEMP | sed 's/^/╨┐╤А╨░╨▓╨╕╨╗ ╤Б╨╛╨╖╨┤╨░╨╜╨╛: /'
    ;;
  close)
    close_rules
    echo "╨┐╤А╨░╨▓╨╕╨╗╨░ IPERF3-TEMP ╤Г╨┤╨░╨╗╨╡╨╜╤Л"
    ;;
  status)
    echo "╨┐╤А╨░╨▓╨╕╨╗ IPERF3-TEMP: $(iptables -L INPUT -n | grep -c IPERF3-TEMP)"
    pgrep -a iperf3 || echo "iperf3 -s ╨╜╨╡ ╨╖╨░╨┐╤Г╤Й╨╡╨╜"
    ;;
  *) echo "usage: $0 open|close|status"; exit 2 ;;
esac
