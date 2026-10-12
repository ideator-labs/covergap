# AGENTS.md - CoverGap

Cold-start handoff for a coding agent with no prior context.

## What it is and the one claim

Small businesses adopt Toast, Jobber, Square, and Shopify AI tools while 2026
CGL renewals quietly attach ISO CG 40 47 / CG 40 48 or carrier absolute AI
exclusions. Owners sign renewals without reading form numbers.

CoverGap joins each shop's renewal Endorsement list to its AiUse inventory,
then classifies before bind. Two policies:

- `trust_packet` (control): never inspects endorsements. Every shop is primary
  `ok_bind`.
- `covergap`: join form numbers + kinds to AI inventory. Flags:
  - `ok_bind` no AI exposure that hits an exclusion (including empty AI
    inventory even when an exclusion form is present)
  - `excluded_ai` CG 40 47 or absolute AI exclusion present AND shop has any
    AI use
  - `narrow_exclude` only CG 40 48 (Coverage B / advertising injury) present
    AND shop has marketing AI use
  - `ask_broker` AI inventory nonempty and no CG 40 47 / CG 40 48 / absolute
    found (do not assume silent coverage is safe forever)

A shop can carry multiple flags. `primary` is the highest severity:
`excluded_ai` > `narrow_exclude` > `ask_broker` > `ok_bind`.

The claim `bash demo.sh` proves. On SAMPLE Harbor Print & Cafe fixtures with
`as_of=2026-10-12T09:00:00`, `trust_packet` marks cafe, salon, hvac, and
bookshop all `ok_bind`. `covergap` marks cafe `excluded_ai`, salon
`narrow_exclude`, hvac `excluded_ai`, bookshop `ok_bind` (exclusion present
but AI inventory empty). Exception count under covergap is 3.

All fixture data is SAMPLE / fictional. Org and shops are made up.

## Status: real vs stubbed

Real:

- Endorsement and AiUse load from JSON (`fixture_to_models`).
- Policies `covergap` and `trust_packet` with flags + primary above.
- Form detection for CG 40 47 / CG 40 48 variants and absolute AI exclusion
  patterns (deterministic regex, no ML).
- Text render and JSON run output via `src/cli.py`.
- Self-checking `demo.sh` with five checks and `demo.sh --break`.

Stubbed or not built:

- No live broker portal, AMS, or policy PDF parser.
- No carrier API. Flags are classification only.
- No bind / hold UI. No broker email draft.
- No Hivemind OS, Workflow Core, or dbl-entry integration.
- No legal advice. Form titles in fixtures are illustrative SAMPLE labels.

## Data shape (with paths)

Frozen dataclasses live at the top of `src/covergap.py`.

| Type | Fields | Notes |
|------|--------|-------|
| `Shop` | `shop_id`, `shop_name` | One renewal scenario per shop. |
| `Endorsement` | `shop_id`, `form_number`, `title`, `kind` | `kind` is cg4047, cg4048, absolute, or other. |
| `AiUse` | `shop_id`, `tool`, `category` | category: marketing, ops, scheduling, other. |
| `Policy` | `name` | trust_packet or covergap. |
| `Flagged` | `shop_id`, `shop_name`, `primary`, `flags`, `reasons` | One row per shop. |
| `Run` | `policy`, `as_of`, `org`, `flagged` | Helpers: `primaries`, `exception_count`, `to_dict`. |

Detection:

- Form numbers normalized to upper; `CG 40 47` / `CG4047` variants map to
  cg4047; `CG 40 48` variants to cg4048.
- Absolute when declared kind is absolute, or title/form matches absolute AI
  exclusion patterns.
- Marketing AI = any AiUse with `category=marketing`.
- Any AI = any AiUse row for that shop.

Fixtures:

- `fixtures/harbor_print.json` (SAMPLE Harbor Print & Cafe)
- `fixtures/expected.json` (expected primaries for both policies)

## Repo map

```
covergap/
  AGENTS.md
  README.md
  LICENSE
  requirements.txt   # empty on purpose; stdlib only
  sources.md
  demo.sh
  .gitignore
  src/
    covergap.py      # types, classify, render
    cli.py           # check entrypoint
  fixtures/          # SAMPLE endorsements + AI uses + expected
  data/              # gitignored run output from demo.sh
```

## Verified run steps

Fresh clone:

```bash
cd /path/to/covergap
bash demo.sh
```

Expect five PASS lines, then `SUMMARY: 5 passed, 0 failed` and `ALL CLAIMS PASSED`,
exit 0.

Break check (must fail, then restore by running without `--break`):

```bash
bash demo.sh --break
# expect non-zero exit; CHECK 2 FAIL (cafe CG 40 47 skipped); SUMMARY includes failed
bash demo.sh
# expect exit 0 again
```

`--break` passes `--skip-cg4047` to the covergap CLI run so cafe is no longer
`excluded_ai`. That sabotages CHECK 2 on purpose.

Manual one-shot:

```bash
PYTHONPATH=src python3 src/cli.py check \
  --fixture fixtures/harbor_print.json \
  --policy covergap \
  --out data/covergap.json
```

## Design decisions

1. `trust_packet` is the control. It shows what bind looks like when nobody
   reads endorsement form numbers against the AI inventory.
2. Classification is pure and fixture-driven. No live policy side effects.
3. Bookshop with CG 40 47 but empty AI inventory stays `ok_bind`. The exclusion
   is noted in reasons; there is no exposure to flag yet.
4. Stdlib only. No pip install step for the demo.
5. `--break` skips CG 40 47 detection only. Salon / hvac / bookshop checks
   still pass so the failure is localized to CHECK 2.

## Limits

- No live AMS, broker portal, or PDF endorsement extract.
- Form titles are SAMPLE strings, not certified ISO text.
- One org fixture with four shops. Multi-carrier packets are out of scope.
- No distinction between admitted and E&S markets.
- `ask_broker` is a soft flag when AI is present and no known exclusion form
  matched. Silent coverage may still exist; the POC refuses to call that safe.

## Prioritized next steps

1. Parse a SAMPLE endorsement PDF page list into `Endorsement` rows.
   Done when: `cli.py import-forms` writes fixture JSON and `bash demo.sh`
   still passes on SAMPLE data.
2. Add an `affirmative_needed` secondary flag when excluded_ai or
   narrow_exclude fires.
   Done when: cafe and salon rows include `affirmative_needed` in `flags` and
   a demo check asserts it.
3. Export a broker hold CSV (shop, primary, forms, ai tools, reasons).
   Done when: `cli.py export-csv` writes a file and demo asserts row count 4
   under covergap.

## Working rules

- Keep prose short. No em-dashes. Label SAMPLE data clearly.
- Prove changes with `bash demo.sh`. Run `--break` once when changing checks.
- Do not add pip dependencies unless the claim needs them.
- Commit as `danielgerlag <daniel@gerlag.ca>`.

## Sources

See `sources.md`. Only those five real URLs are cited.
