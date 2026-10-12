#!/usr/bin/env python3
"""CLI for CoverGap check runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from covergap import (
    fixture_to_models,
    load_fixture,
    render_run,
    run_policy,
    write_run,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="CoverGap endorsement-vs-AI classify")
    sub = p.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="Classify shops under a policy")
    check.add_argument("--fixture", type=Path, required=True)
    check.add_argument(
        "--policy",
        choices=("trust_packet", "covergap"),
        required=True,
    )
    check.add_argument("--out", type=Path, required=True)
    check.add_argument("--quiet", action="store_true")
    check.add_argument(
        "--skip-cg4047",
        action="store_true",
        help="Sabotage path: do not detect CG 40 47 (used by demo.sh --break)",
    )

    args = p.parse_args(argv)
    raw = load_fixture(args.fixture)
    org, as_of, shops, endorsements, ai_uses = fixture_to_models(raw)

    if args.cmd == "check":
        run = run_policy(
            shops,
            endorsements,
            ai_uses,
            as_of=as_of,
            policy_name=args.policy,
            org=org,
            skip_cg4047=args.skip_cg4047,
        )
        write_run(run, args.out)
        if not args.quiet:
            print(render_run(run))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
