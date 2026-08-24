"""VERINE NERVE CLI.

Usage:
  python -m verine.cli fixture run [--incident INCIDENT_ID] [--hidden edge_id,edge_id]
  python -m verine.cli case replay CASE_ID
  python -m verine.cli benchmark
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from .api.service import VerineService


def _service(data_dir: str | None) -> VerineService:
    root = Path(data_dir) if data_dir else Path(tempfile.mkdtemp(prefix="verine_"))
    svc = VerineService(root)
    svc.seed_fixture()
    return svc


def cmd_fixture_run(args) -> int:
    svc = _service(args.data_dir)
    meta = svc.fixture_meta()
    hidden = args.hidden.split(",") if args.hidden else []
    scenario, compiled = svc.compile_and_store_scenario(
        capability_id="cap_digital_payments_authorization",
        incident_id=args.incident,
        hidden_edge_ids=hidden,
        seed=args.seed if args.seed is not None else meta["default_seed"],
    )
    result = svc.run_simulation(scenario.scenario_id)
    case = result["case_file"]
    det = result["model_outputs"]["deterministic_propagation_v1"]["metrics"]["capabilities"][
        "cap_digital_payments_authorization"
    ]
    print(f"scenario_id     : {scenario.scenario_id}")
    print(f"graph_hash      : {case['graph_hash']}")
    print(f"scenario_hash   : {case['scenario_hash']}")
    print(f"run_hash        : {case['run_hash']}")
    print(f"case_file_id    : {case['case_file_id']}")
    print(f"status          : {case['capability_status']}")
    print(f"min service lvl : {det['min_service_level']}  (floor breach: {det['breached_floor']}, "
          f"time-to-floor: {det['time_to_floor_minutes']}m, breach duration: {det['floor_breach_duration_minutes']}m)")
    chosen = result["containment"]["chosen_set"]
    if chosen:
        print(f"containment     : {chosen['action_ids']} (cost {chosen['total_cost']:.0f}, "
              f"loss {result['containment']['baseline_no_action']['expected_service_loss_sl_hours']} -> "
              f"{chosen['expected_service_loss_sl_hours']} sl-hours)")
    print(f"disagreement    : {result['disagreement']['overall_level']}")
    print(f"unknowns        : {len(result['unknowns']['unknowns'])} "
          f"(reliability: {result['unknowns']['reliability_label']})")
    if args.out:
        Path(args.out).write_text(json.dumps(case, indent=2))
        print(f"case file       : written to {args.out}")
    if args.data_dir:
        print(f"data dir        : {args.data_dir} (replay with: python -m verine.cli "
              f"--data-dir {args.data_dir} case replay {case['case_file_id']})")
    return 0


def cmd_case_replay(args) -> int:
    if not args.data_dir:
        print("--data-dir is required for replay (must point at the store holding the case)", file=sys.stderr)
        return 2
    svc = VerineService(Path(args.data_dir))
    verdict = svc.replay(args.case_id)
    print(json.dumps(verdict, indent=2))
    return 0 if verdict.get("hashes_match") else 1


def cmd_benchmark(args) -> int:
    from .evaluation.benchmark import run_benchmarks

    svc = _service(args.data_dir)
    report = run_benchmarks(svc)
    out = Path(args.out) if args.out else Path("research/benchmark/latest_benchmark.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    for task in report["tasks"]:
        print(f"{task['task_id']:>4}  {task['status']:<8} {task['name']}")
    print(f"\nreport written to {out}")
    return 0 if all(t["status"] in ("pass", "pending") for t in report["tasks"]) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="verine")
    p.add_argument("--data-dir", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    fx = sub.add_parser("fixture")
    fx_sub = fx.add_subparsers(dest="fixture_cmd", required=True)
    fx_run = fx_sub.add_parser("run")
    fx_run.add_argument("--incident", default="inc_compound_payment_crisis")
    fx_run.add_argument("--hidden", default="")
    fx_run.add_argument("--seed", type=int, default=None)
    fx_run.add_argument("--out", default=None)
    fx_run.set_defaults(func=cmd_fixture_run)

    case = sub.add_parser("case")
    case_sub = case.add_subparsers(dest="case_cmd", required=True)
    case_replay = case_sub.add_parser("replay")
    case_replay.add_argument("case_id")
    case_replay.set_defaults(func=cmd_case_replay)

    bench = sub.add_parser("benchmark")
    bench.add_argument("--out", default=None)
    bench.set_defaults(func=cmd_benchmark)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
