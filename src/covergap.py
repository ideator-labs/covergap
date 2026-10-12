"""CoverGap: join CGL renewal endorsements to AI-use inventory before bind.

Policies: trust_packet (control, all ok_bind) vs covergap (join forms to AI use).
Pure stdlib. SAMPLE / fictional fixtures only.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

PolicyName = Literal["trust_packet", "covergap"]
Flag = Literal["ok_bind", "excluded_ai", "narrow_exclude", "ask_broker"]
EndorsementKind = Literal["cg4047", "cg4048", "absolute", "other"]
AiCategory = Literal["marketing", "ops", "scheduling", "other"]

# Highest severity first for primary selection.
SEVERITY: tuple[Flag, ...] = (
    "excluded_ai",
    "narrow_exclude",
    "ask_broker",
    "ok_bind",
)

CG4047_RE = re.compile(r"CG\s*40\s*47", re.IGNORECASE)
CG4048_RE = re.compile(r"CG\s*40\s*48", re.IGNORECASE)
ABSOLUTE_RE = re.compile(r"ABSOLUTE\s+AI\s+EXCLUSION", re.IGNORECASE)


@dataclass(frozen=True)
class Shop:
    shop_id: str
    shop_name: str


@dataclass(frozen=True)
class Endorsement:
    shop_id: str
    form_number: str
    title: str
    kind: EndorsementKind


@dataclass(frozen=True)
class AiUse:
    shop_id: str
    tool: str
    category: AiCategory


@dataclass(frozen=True)
class Policy:
    name: PolicyName


@dataclass(frozen=True)
class Flagged:
    shop_id: str
    shop_name: str
    primary: Flag
    flags: list[str]
    reasons: list[str]


@dataclass
class Run:
    policy: PolicyName
    as_of: str
    org: str
    flagged: list[Flagged] = field(default_factory=list)

    def by_shop(self) -> dict[str, Flagged]:
        return {f.shop_id: f for f in self.flagged}

    def primaries(self) -> dict[str, str]:
        return {f.shop_id: f.primary for f in self.flagged}

    def exception_count(self) -> int:
        return sum(1 for f in self.flagged if f.primary != "ok_bind")

    def to_dict(self) -> dict:
        return {
            "policy": self.policy,
            "as_of": self.as_of,
            "org": self.org,
            "flagged": [asdict(f) for f in self.flagged],
            "primaries": self.primaries(),
            "exception_count": self.exception_count(),
        }


def normalize_form(form_number: str) -> str:
    return re.sub(r"\s+", " ", form_number.strip().upper())


def detect_kind(
    form_number: str,
    title: str,
    declared: str | None = None,
    *,
    skip_cg4047: bool = False,
) -> EndorsementKind:
    """Classify endorsement from form number / title. Deterministic, no ML."""
    if declared in ("cg4047", "cg4048", "absolute", "other"):
        kind = declared  # type: ignore[assignment]
        if skip_cg4047 and kind == "cg4047":
            return "other"
        return kind  # type: ignore[return-value]

    norm = normalize_form(form_number)
    blob = f"{norm} {title.upper()}"

    if not skip_cg4047 and CG4047_RE.search(norm):
        return "cg4047"
    if CG4048_RE.search(norm):
        return "cg4048"
    if ABSOLUTE_RE.search(blob) or "ABSOLUTE" in blob and "AI" in blob and "EXCL" in blob:
        return "absolute"
    if declared == "absolute":
        return "absolute"
    return "other"


def pick_primary(flags: list[str]) -> Flag:
    for sev in SEVERITY:
        if sev in flags:
            return sev
    return "ok_bind"


def classify_shop(
    shop: Shop,
    endorsements: list[Endorsement],
    ai_uses: list[AiUse],
    policy: Policy,
    *,
    skip_cg4047: bool = False,
) -> Flagged:
    shop_ends = [e for e in endorsements if e.shop_id == shop.shop_id]
    shop_ai = [a for a in ai_uses if a.shop_id == shop.shop_id]

    if policy.name == "trust_packet":
        return Flagged(
            shop_id=shop.shop_id,
            shop_name=shop.shop_name,
            primary="ok_bind",
            flags=["ok_bind"],
            reasons=["policy:trust_packet", "no_endorsement_inspect"],
        )

    # Resolve kinds (optionally sabotage CG 40 47 for --break).
    kinds: set[str] = set()
    kind_notes: list[str] = []
    for e in shop_ends:
        kind = detect_kind(
            e.form_number,
            e.title,
            e.kind,
            skip_cg4047=skip_cg4047,
        )
        if skip_cg4047 and (e.kind == "cg4047" or CG4047_RE.search(normalize_form(e.form_number))):
            kind_notes.append(f"sabotage:skip_cg4047 form={e.form_number}")
            kinds.add("other")
            continue
        kinds.add(kind)
        kind_notes.append(f"form={e.form_number} kind={kind}")

    has_ai = len(shop_ai) > 0
    has_marketing = any(a.category == "marketing" for a in shop_ai)
    has_cg4047 = "cg4047" in kinds
    has_cg4048 = "cg4048" in kinds
    has_absolute = "absolute" in kinds

    flags: list[str] = []
    reasons: list[str] = ["policy:covergap"]
    reasons.extend(kind_notes)
    if shop_ai:
        for a in shop_ai:
            reasons.append(f"ai_use:{a.tool} category={a.category}")
    else:
        reasons.append("ai_inventory:empty")

    if has_ai and (has_cg4047 or has_absolute):
        flags.append("excluded_ai")
        if has_cg4047:
            reasons.append("excluded_ai:CG_40_47_with_ai_use")
        if has_absolute:
            reasons.append("excluded_ai:absolute_ai_exclusion_with_ai_use")
    elif has_marketing and has_cg4048 and not has_cg4047 and not has_absolute:
        flags.append("narrow_exclude")
        reasons.append("narrow_exclude:CG_40_48_with_marketing_ai")
    elif has_ai and not has_cg4047 and not has_cg4048 and not has_absolute:
        flags.append("ask_broker")
        reasons.append("ask_broker:ai_use_no_exclusion_forms_found")
    elif not has_ai:
        flags.append("ok_bind")
        if has_cg4047 or has_cg4048 or has_absolute:
            reasons.append("ok_bind:exclusion_present_but_ai_inventory_empty")
        else:
            reasons.append("ok_bind:no_ai_no_exclusion")
    else:
        # Has AI and only other forms, or CG 40 48 without marketing.
        if has_cg4048 and not has_marketing:
            flags.append("ask_broker")
            reasons.append("ask_broker:CG_40_48_but_no_marketing_ai")
        else:
            flags.append("ok_bind")
            reasons.append("ok_bind:within_known_forms")

    if not flags:
        flags = ["ok_bind"]
        reasons.append("ok_bind:default")

    primary = pick_primary(flags)
    return Flagged(
        shop_id=shop.shop_id,
        shop_name=shop.shop_name,
        primary=primary,
        flags=flags,
        reasons=reasons,
    )


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text())


def fixture_to_models(
    raw: dict,
) -> tuple[str, str, list[Shop], list[Endorsement], list[AiUse]]:
    org = raw["org"]
    as_of = raw["as_of"]
    shops = [
        Shop(shop_id=s["shop_id"], shop_name=s["shop_name"]) for s in raw["shops"]
    ]
    endorsements = [
        Endorsement(
            shop_id=e["shop_id"],
            form_number=e["form_number"],
            title=e["title"],
            kind=e["kind"],
        )
        for e in raw["endorsements"]
    ]
    ai_uses = [
        AiUse(shop_id=a["shop_id"], tool=a["tool"], category=a["category"])
        for a in raw["ai_uses"]
    ]
    return org, as_of, shops, endorsements, ai_uses


def run_policy(
    shops: list[Shop],
    endorsements: list[Endorsement],
    ai_uses: list[AiUse],
    as_of: str,
    policy_name: PolicyName,
    org: str,
    *,
    skip_cg4047: bool = False,
) -> Run:
    policy = Policy(name=policy_name)
    run = Run(policy=policy_name, as_of=as_of, org=org)
    for shop in shops:
        run.flagged.append(
            classify_shop(
                shop,
                endorsements,
                ai_uses,
                policy,
                skip_cg4047=skip_cg4047 and policy_name == "covergap",
            )
        )
    return run


def render_run(run: Run) -> str:
    lines = [
        f"org={run.org} policy={run.policy} as_of={run.as_of}",
        "SAMPLE / fictional Harbor Print & Cafe renewal scenarios",
        "",
    ]
    for f in run.flagged:
        lines.append(
            f"  {f.shop_name:<28} {f.shop_id:<14} primary={f.primary:<16} "
            f"flags={f.flags}"
        )
        for r in f.reasons:
            lines.append(f"           {r}")
    lines.append("")
    lines.append(f"exceptions (primary!=ok_bind): {run.exception_count()}")
    return "\n".join(lines)


def write_run(run: Run, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run.to_dict(), indent=2) + "\n")
