# Skills

Claude Code skills that build on this MCP server. They live in the repo so they
version alongside the tools they call.

## Installing

Skills are discovered from `~/.claude/skills/`. Symlink rather than copy, so
edits here take effect immediately:

```bash
ln -s "$(pwd)/skills/fueling-plan" ~/.claude/skills/fueling-plan
```

Verify with `/skills` in a new Claude Code session.

## Available

| Skill | What it does |
|---|---|
| [`fueling-plan`](fueling-plan/) | Turns today's TrainingPeaks sessions into a count of specific nutrition products to carry — carbs, sodium, fluid and caffeine, solved against what's actually been purchased. |

## Requirements

These call the `tp_*` tools, so the TrainingPeaks MCP must be connected. The
`.mcp.json` at the repo root registers it for Claude Code sessions started in
this directory; Claude Desktop needs the entry from `tp-mcp config` in its own
config file.

`fueling-plan` additionally reads Gmail when refreshing its product pantry.
Day-to-day use reads the cached `pantry.json` and does not need Gmail.
