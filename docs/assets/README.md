# Architecture diagram exports

Optional **PNG/SVG** exports for README, portfolio, or Figma handoff.

## Suggested files

| File | Source |
|------|--------|
| `architecture-at-a-glance.svg` | End-to-end flow block in [`../architecture.md`](../architecture.md) |
| `architecture-full.svg` | Full pipeline block (same file) |
| `architecture-european-example.svg` | European club example block |

## How to generate

1. Copy diagram content from [`../architecture.md`](../architecture.md) or recreate from [`../case-study.md`](../case-study.md).
2. [mermaid.live](https://mermaid.live) → Export **SVG** (if using Mermaid).
3. Save here and embed in root `README.md` if needed:

```markdown
![Data flow](docs/assets/architecture-full.svg)
```

## Figma

Import SVG → ungroup → style.
