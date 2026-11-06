"""Cost per 1,000 requests and SLO error budget, step by step.

  python scripts/cost.py --replicas 2 --cpu-limit 1 --mem-limit-gib 1 \
         --stats results/loadtest/loadtest_stats.csv [--slo-target 99.0]
Uses data/rate_card.json. All inputs come from the measured Locust CSV and the Deployment limits.
"""
import argparse
import csv
import json


def cost_per_1000(replicas, cpu, mem_gib, rps, vcpu_hour, gib_hour):
    hourly_per_replica = cpu * vcpu_hour + mem_gib * gib_hour
    hourly_all = replicas * hourly_per_replica
    requests_per_hour = rps * 3600
    return hourly_per_replica, hourly_all, requests_per_hour, hourly_all / requests_per_hour * 1000


def error_budget(total, failures, target_pct):
    allowed = total * (100 - target_pct) / 100
    return allowed, failures, (failures / allowed * 100 if allowed else float("inf"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicas", type=int, required=True)
    ap.add_argument("--cpu-limit", type=float, default=1.0)
    ap.add_argument("--mem-limit-gib", type=float, default=1.0)
    ap.add_argument("--stats", required=True)
    ap.add_argument("--rate-card", default="data/rate_card.json")
    ap.add_argument("--slo-target", type=float, default=99.0)
    a = ap.parse_args()
    rc = json.load(open(a.rate_card))
    row = next(r for r in csv.DictReader(open(a.stats)) if r["Name"] == "Aggregated")
    total, fails, rps = int(row["Request Count"]), int(row["Failure Count"]), float(row["Requests/s"])
    per, hourly, rph, c = cost_per_1000(a.replicas, a.cpu_limit, a.mem_limit_gib, rps,
                                        rc["vcpu_hour"], rc["gib_memory_hour"])
    print(f"measured: {total} requests, {fails} failures, {rps} requests/s")
    print(f"1. hourly cost per replica = {a.cpu_limit} vCPU x {rc['vcpu_hour']} + "
          f"{a.mem_limit_gib} GiB x {rc['gib_memory_hour']} = {per:.4f} {rc['currency']}")
    print(f"2. hourly cost of {a.replicas} replicas = {a.replicas} x {per:.4f} = {hourly:.4f}")
    print(f"3. requests per hour = {rps} x 3600 = {rph:.1f}")
    print(f"4. cost per 1000 requests = {hourly:.4f} / {rph:.1f} x 1000 = {c:.4f} {rc['currency']}")
    allowed, used, pct = error_budget(total, fails, a.slo_target)
    print(f"SLO: {a.slo_target}% of requests succeed in one load-test run")
    print(f"error budget = {total} x (1 - {a.slo_target / 100}) = {allowed:.2f} requests; "
          f"failures = {used}; budget used = {pct:.1f}%")


if __name__ == "__main__":
    main()
