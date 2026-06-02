# RV32M Release Checklist

## Pre-release checks

- [ ] All item 7 gates green (format, loader, integrity, reproducibility)
- [ ] All item 8 gates green (loop smoke, watchdog, e2e, stability)
- [ ] All item 9 gates green (channel ABI, roundtrip, stop ABI, compat)
- [ ] All item 10 gates green (external e2e, coverage, release)
- [ ] No-regression on C3/C2 minimal gates
- [ ] Repeat-stability 3/3 verified
- [ ] Budget metrics within baseline

## Rollout stages

1. **Preflight**: format contract + happy path
2. **Minimal**: all loader gates + loop/cwd gates + channel ABI
3. **Staged**: full gate suite + 3/3 repeat-stability
4. **Release**: all gates green + no-regression + budget SLA

## Exit criteria for each item

### Item 7 (Loader)
- All 7.* gates green
- Staged 3/3 reproducibility
- Integrity/repro artifacts present

### Item 8 (Universal loop)
- E2E gate green
- Watchdog gate green
- No-regression on C3/C2 gates

### Item 9 (Channel ABI)
- ABI contract gate green
- IO roundtrip gate green
- Timeout recovery gate green
- Stop ABI gate green

### Item 10 (Full E2E)
- External e2e smoke gate green
- Coverage gate green
- Release gate green (smoke + selected full)
- Budget SLA met
- This checklist complete
