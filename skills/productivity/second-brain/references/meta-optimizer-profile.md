# Meta-Optimizer Profile Spec

> Profile: `~/.hermes/profiles/meta-optimizer/`
> Cron: `meta-optimizer-weekly` (Sun 22:00 UTC)

## Scope: Allowlist

```
✅ ~/second_brain/20_Meta/improvement_proposals/**  (write_file only)
```

## Scope: Denylist (preflight enforced)

```
❌ ~/.hermes/SOUL.md, AGENTS.md, config.yaml
❌ ~/.hermes/roles/**, skills/**
❌ ~/.hermes/profiles/meta-optimizer/**
❌ ~/.hermes/MEMORY.md, USER.md
❌ ~/second_brain/10_Wiki/**
❌ cronjob:* (all), including self (meta-optimizer-weekly)
```

## Dual Protection

1. **Preflight**: denylist check before every tool call → abort if violation
2. **Postflight**: profile directory SHA256 manifest comparison → abort if changed

## Trigger Conditions

- metrics.jsonl ≥ 30 lines (Central Limit Theorem)
- Per-domain analysis: n ≥ 10 per domain
- Below threshold: trend observation only, no proposals

## Approval Gate

```
Meta-Optimizer → proposal.md (improvement_proposals/)
              → user review
              → Hermes Agent applies (patch/cronjob update)
```
