import argparse
import json

from .rules import load_rules
from .validate import format_findings, validate_copy
from .visual_angles import feasible_angles, render_report


def cmd_angles(args: argparse.Namespace) -> None:
    if args.json:
        rules = load_rules()
        angles = feasible_angles(include_avoid=args.include_avoid)
        print(json.dumps([{
            "id": a.id, "name": a.name, "headline_type": a.headline_type,
            "doctor_usage": a.doctor_usage, "risk": a.risk, "description": a.description,
            "checklist": a.checklist, "example_headline": a.example_headline,
            "prompt": a.prompt(rules),
        } for a in angles], indent=2, ensure_ascii=False))
    else:
        print(render_report(include_avoid=args.include_avoid))


def cmd_validate(args: argparse.Namespace) -> None:
    findings = validate_copy(args.headline, args.body or "")
    print(f"Headline: {args.headline}")
    if args.body:
        print(f"Body: {args.body}")
    print()
    print(format_findings(findings))


def main() -> None:
    parser = argparse.ArgumentParser(description="Jaadu Diet ad-compliance tool.")
    sub = parser.add_subparsers(dest="command", required=True)

    angles_p = sub.add_parser("angles", help="List feasible visual angles + generation prompts.")
    angles_p.add_argument("--json", action="store_true", help="Output JSON instead of a text report.")
    angles_p.add_argument("--include-avoid", action="store_true", help="Also include the banned reference angle.")
    angles_p.set_defaults(func=cmd_angles)

    validate_p = sub.add_parser("validate", help="Validate a headline/body against the ruleset.")
    validate_p.add_argument("--headline", required=True)
    validate_p.add_argument("--body", default="")
    validate_p.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
