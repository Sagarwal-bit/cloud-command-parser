# Task 5: Subnet Allocation for 10.20.0.0/16

Method: allocate largest to smallest, starting at 10.20.0.0, each block directly after the previous one.
Smallest prefix p such that 2^(32-p) - 2 >= hosts needed.

| Subnet     | Hosts needed | Working                          | Prefix | Network address | Usable range              | Broadcast    | Usable hosts |
|------------|--------------|----------------------------------|--------|-----------------|---------------------------|--------------|--------------|
| app        | 1,000        | 2^10-2 = 1022 >= 1000 (2^9-2=510 too small)  | /22 | 10.20.0.0   | 10.20.0.1 – 10.20.3.254   | 10.20.3.255  | 1,022 |
| public     | 250          | 2^8-2 = 254 >= 250 (2^7-2=126 too small)     | /24 | 10.20.4.0   | 10.20.4.1 – 10.20.4.254   | 10.20.4.255  | 254   |
| data       | 100          | 2^7-2 = 126 >= 100 (2^6-2=62 too small)      | /25 | 10.20.5.0   | 10.20.5.1 – 10.20.5.126   | 10.20.5.127  | 126   |
| management | 20           | 2^5-2 = 30 >= 20 (2^4-2=14 too small)        | /27 | 10.20.5.128 | 10.20.5.129 – 10.20.5.158 | 10.20.5.159  | 30    |

Each next network starts at (previous broadcast + 1): app ends 10.20.3.255 -> public 10.20.4.0;
public ends 10.20.4.255 -> data 10.20.5.0; data ends 10.20.5.127 -> management 10.20.5.128.

# NACL for the public subnet (network/nacl.json)

Inbound: 100 deny 198.51.100.0/24 (all); 110 allow TCP 80; 120 allow TCP 443; 130 allow TCP 22 from
10.20.5.128/27 (management); 140 allow TCP 1024-65535 from 10.20.0.0/22 (replies from app).
Outbound: 100 allow TCP 8000 to 10.20.0.0/22 (app); 110 allow TCP 1024-65535 to 0.0.0.0/0 (replies to clients).

Simulator result on packets_sample.jsonl: 6/6 correct.

## Why replies need their own rules, and why order matters

A NACL is stateless: it does not remember that an inbound request was allowed, so the reply is
evaluated as a brand-new packet against the outbound rules. A reply to a client leaves from port 80/443
to the client's ephemeral port, so an outbound rule for ports 1024-65535 is required (and likewise an inbound
ephemeral rule for replies coming back from the app subnet).

Rules are checked from the lowest number upward and the first match wins. The deny for 198.51.100.0/24
must have a lower number (100) than the allow for TCP 80/443 from 0.0.0.0/0 (110/120). If it were numbered
higher, the broad allow would match first and the abusive range would get through.
