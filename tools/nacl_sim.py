"""Simulate a stateless Network Access Control List (NACL).

Usage
  python nacl_sim.py RULES PACKETS                 print the decision for every packet
  python nacl_sim.py RULES PACKETS --check         also compare with the "expected" field and print a score

RULES (your network/nacl.json)
{
  "inbound":  [ {"rule": 100, "protocol": "tcp", "port_from": 443, "port_to": 443,
                 "cidr": "0.0.0.0/0", "action": "allow"}, ... ],
  "outbound": [ ... ]
}
  rule      integer from 1 to 32766, unique within its direction
  protocol  "tcp", "udp" or "all" ("all" matches every protocol and every port)
  port_from, port_to   inclusive destination port range (ignored when protocol is "all")
  cidr      inbound rules match the packet's SOURCE address; outbound rules match its DESTINATION address
  action    "allow" or "deny"

PACKETS (JSON Lines), one per line:
  {"id": "P01", "direction": "inbound", "protocol": "tcp", "port": 443, "address": "203.0.113.7", "expected": "allow"}
  address   the remote address: the source for inbound packets, the destination for outbound packets
  port      the destination port of the packet
  expected  optional; used only with --check

Evaluation (as in a real NACL)
  Rules of the packet's direction are checked from the LOWEST rule number upward.
  The first rule that matches decides. If no rule matches, the packet is DENIED.
  The NACL is stateless: every packet, including a reply, is checked on its own.
Only the Python standard library is used.
"""
import argparse
import ipaddress
import json
import sys


def load_rules(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    rules = {}
    for d in ('inbound', 'outbound'):
        lst = data.get(d)
        if not isinstance(lst, list):
            sys.exit(f'rules file must contain a list "{d}"')
        seen = set()
        for r in lst:
            for k in ('rule', 'protocol', 'cidr', 'action'):
                if k not in r:
                    sys.exit(f'{d} rule {r} is missing "{k}"')
            if not (isinstance(r['rule'], int) and 1 <= r['rule'] <= 32766):
                sys.exit(f'{d}: rule number {r["rule"]} must be an integer from 1 to 32766')
            if r['rule'] in seen:
                sys.exit(f'{d}: rule number {r["rule"]} is used twice')
            seen.add(r['rule'])
            if r['protocol'] not in ('tcp', 'udp', 'all'):
                sys.exit(f'{d} rule {r["rule"]}: protocol must be tcp, udp or all')
            if r['action'] not in ('allow', 'deny'):
                sys.exit(f'{d} rule {r["rule"]}: action must be allow or deny')
            if r['protocol'] != 'all':
                if not (0 <= r.get('port_from', -1) <= r.get('port_to', -1) <= 65535):
                    sys.exit(f'{d} rule {r["rule"]}: need 0 <= port_from <= port_to <= 65535')
            r['_net'] = ipaddress.ip_network(r['cidr'], strict=True)
        rules[d] = sorted(lst, key=lambda r: r['rule'])
    return rules


def decide(rules, pkt):
    addr = ipaddress.ip_address(pkt['address'])
    for r in rules[pkt['direction']]:
        if addr not in r['_net']:
            continue
        if r['protocol'] != 'all':
            if r['protocol'] != pkt['protocol'] or not (r['port_from'] <= pkt['port'] <= r['port_to']):
                continue
        return r['action'], r['rule']
    return 'deny', None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rules')
    ap.add_argument('packets')
    ap.add_argument('--check', action='store_true', help='compare with "expected" and print a score')
    a = ap.parse_args()
    rules = load_rules(a.rules)
    correct = total = 0
    with open(a.packets, encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            p = json.loads(line)
            action, rule = decide(rules, p)
            src = f'rule {rule}' if rule is not None else 'no match (default deny)'
            msg = f'{p["id"]:>4}  {p["direction"]:8} {p["protocol"]:3} port {p["port"]:<5} {p["address"]:<15} -> {action.upper():5} ({src})'
            if a.check and 'expected' in p:
                total += 1
                ok = action == p['expected']
                correct += ok
                msg += '  OK' if ok else f'  WRONG (expected {p["expected"]})'
            print(msg)
    if a.check:
        print(f'\nCorrect: {correct} / {total} = {100.0 * correct / total:.1f}%')


if __name__ == '__main__':
    main()
