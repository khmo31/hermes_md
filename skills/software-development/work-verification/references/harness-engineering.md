# Harness Engineering Framework (하네스 엔지니어링)

**Source**: YouTube — [하네스 엔지니어링](https://youtu.be/q1v1_btl19w)

A framework for thinking about AI agent control, training, and customization.
The core insight: **a good harness can make a weak model perform well; a bad harness wastes a strong model.**

## The Three-Level Model

### L1 — Agent-Source Modification (highest effort, highest risk)
Forking and modifying the agent program itself.

**Examples**: `oh-my-pi` (forked `pi` agent with custom code-editing approach), Claude Agent SDK multi-agent orchestration.

**Techniques shown in the video**:
- Claude Code: outputs raw code changes → agent finds matching lines → replaces them
- Diff-based agents: outputs git-style diffs → agent applies them
- `oh-my-pi`: inserts random markers per line → LLM modifies them → agent extracts changes → benchmark shows **garbage LLM + oh-my-pi = much better coding performance**

**Risks**:
- Requires coding knowledge + agent architecture understanding
- Evaluation requires GPU/time/money for benchmarking
- Model-specific: "Claude models don't run well on non-Claude harnesses"

### L2 — MCP + Skill Customization (sweet spot for most tasks)
Extending agent capabilities via MCP servers and Skills.

**Examples in this setup**:
- Home Assistant MCP for smart home control
- Notion MCP for knowledge management
- work-verification skill (Behavior Correction Protocol)
- GitHub MCP for repository operations

**Patterns**:
- **Verification MCP**: Chrome DevTools MCP / Playwright MCP for browser-based verification
- **External capability MCP**: database, file system, API access
- **Skill-based education**: SKILL.md to train AI on project-specific conventions

### L3 — Prompt/Config Education (lowest effort, limited durability)
- `AGENTS.md` / `CLAUDE.md` / `CURSORRULES` / `.cursorrules`
- AI reads and follows instructions at project root
- Works at every stage of the agent's decision loop

**Limitation**: Long instructions get lost mid-task. "Like telling a dog complex commands — they forget and ignore."

## Behavior Correction Protocol

See the **Behavior Correction Protocol** section in `work-verification` SKILL.md for the full procedure. Summary:

1. **Detect** — same mistake 2+ times → recurring behavioral issue
2. **Record** — Context + Trigger + Forbidden + Correct
3. **Store** — SKILL.md > memory > AGENTS.md (priority order)
4. **Verify** — rerun and confirm correction sticks

## Tradeoff Summary

| Level | Effort | Flexibility | Durability | When to Use |
|-------|--------|-------------|------------|-------------|
| L1 | High | Max | Max | Building a new agent / core loop change |
| L2 | Medium | High | High | Daily task customization |
| L3 | Low | Medium | Low | Quick project-level instructions |

## Practical Application Notes

- **MCP-first approach**: Before modifying agent source code, see if the problem can be solved with an MCP server or a skill update
- **Verify first**: After any customization, run a concrete test to confirm the behavior change worked
- **Document failures**: When an approach fails repeatedly, record it as a skill pitfall, not just memory
- **Browser MCP (optional)**: Add `@playwright/mcp` when frontend/coding tasks need visual verification. Needs Chromium (~400MB). Config in `mcp_servers` section of config.yaml.
