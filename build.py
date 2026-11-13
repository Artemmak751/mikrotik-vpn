#!/usr/bin/env python3
"""Собирает ips.rsc для MikroTik из seed.rsc и ips.txt."""
import ipaddress
import re
import sys
from pathlib import Path

LIST_NAME = "to-WG"
MARKER = "gh-ip"
MIN_PREFIXES = 50

BYPASS = [ipaddress.ip_network(x) for x in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.168.0.0/16",
    "224.0.0.0/4", "240.0.0.0/4",
)]

def from_seed(path):
    text = path.read_text(encoding="utf-8", errors="ignore").replace("\\\n", "")
    out = []
    for line in text.splitlines():
        if f"list={LIST_NAME}" not in line:
            continue
        m = re.search(r"\baddress=([0-9./]+)", line)
        if m:
            out.append(m.group(1))
    return out

def from_plain(path):
    out = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out

raw = []
for name, fn in (("seed.rsc", from_seed), ("ips.txt", from_plain)):
    p = Path(name)
    if p.exists():
        got = fn(p)
        print(f"{name}: {len(got)} записей")
        raw += got

nets, bad = [], []
for s in raw:
    try:
        n = ipaddress.ip_network(s, strict=False)
    except ValueError:
        bad.append(s)
        continue
    if n.version != 4:
        continue
    if any(n.overlaps(b) for b in BYPASS):
        print(f"  пропущен приватный/служебный: {n}")
        continue
    nets.append(n)

if bad:
    print("Не разобрано:", bad[:20])

collapsed = list(ipaddress.collapse_addresses(nets))
print(f"ИТОГО: {len(nets)} -> {len(collapsed)}")

if len(collapsed) < MIN_PREFIXES:
    sys.exit(f"ОШИБКА: {len(collapsed)} префиксов, меньше {MIN_PREFIXES}. Публикация отменена.")

lines = ["/ip firewall address-list"]
lines += [f'add list={LIST_NAME} address={n} comment="{MARKER}"' for n in collapsed]
Path("ips.rsc").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("ips.rsc записан")
