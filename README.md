# CoverGap

Join CGL renewal endorsements to an AI-use inventory before the owner binds.

Two policies:

- `trust_packet` (control): never inspects endorsements; every shop is `ok_bind`.
- `covergap`: flags `excluded_ai`, `narrow_exclude`, `ask_broker`, `ok_bind`
  against CG 40 47 / CG 40 48 / absolute AI exclusions and the AI inventory.

All demo data is SAMPLE / fictional (Harbor Print & Cafe).

```bash
bash demo.sh
```

Break one check on purpose (must exit non-zero):

```bash
bash demo.sh --break
```

Full handoff for a coding agent: [AGENTS.md](./AGENTS.md).

Sources: [sources.md](./sources.md).
