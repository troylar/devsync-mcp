# devsync-mcp

MCP server for AI-merge of team dev configurations. Works with any MCP-capable IDE (Claude Code, Cursor, Windsurf, Copilot, Zed, etc.).

## What it does

Teams maintain a shared config profile repo (shell configs, git settings, AI rules, editor configs). `devsync-mcp` provides MCP tools that let the IDE's LLM intelligently merge team configs with your personal configs — preserving your customizations while incorporating team standards.

**Key insight:** The MCP server does NOT call an LLM. It provides source and target content to the host IDE's LLM, which performs the intelligent merge.

## Install

```bash
pip install devsync-mcp
```

## MCP Configuration

Add to your IDE's MCP settings:

```json
{
  "mcpServers": {
    "devsync-mcp": {
      "command": "devsync-mcp",
      "transport": "stdio"
    }
  }
}
```

## Tools

| Tool | Purpose |
|------|---------|
| `pull_team_profile` | Clone/pull team config repo |
| `list_profile_configs` | List configs in a profile |
| `detect_current_configs` | Scan environment for existing configs |
| `preview_merge` | Return source + target for LLM merge |
| `apply_merge` | Write merged content with backup |
| `sync_all` | Pull latest + present merge plan |
| `list_backups` | List previous merge backups |
| `restore_backup` | Restore from backup |
| `get_merge_status` | Show merged/pending/changed status |

## AI-Merge Flow

```
1. pull_team_profile(git_url)     → downloads team config repo
2. list_profile_configs(profile)  → shows available configs
3. detect_current_configs()       → finds your existing configs
4. preview_merge(profile, config) → returns {source_content, target_content}
5. HOST LLM reads both, produces intelligent merge
6. apply_merge(target, merged)    → writes with backup
```

## Team Profile Format

Create a `devsync-profile.yaml` in your team config repo:

```yaml
name: acme-team-config
description: ACME Corp standard dev environment
version: 1.0.0

configs:
  - name: zshrc-additions
    file: shell/zshrc-additions.sh
    target: ~/.zshrc
    type: shell_profile
    description: Team shell aliases and PATH additions

  - name: claude-rules
    file: ai-rules/claude-rules.md
    target: CLAUDE.md
    type: ai_rules
    description: Team coding standards for Claude Code
```

## Config Types

- `shell_profile` — `.zshrc`, `.bashrc`, `.bash_profile`, `.profile`
- `git_config` — `.gitconfig`, `.gitignore_global`
- `editor_config` — `.editorconfig`
- `ai_rules` — `CLAUDE.md`, `.cursorrules`, `AGENTS.md`, etc.
- `vscode_settings` — `.vscode/settings.json`, etc.
- `ssh_config` — `.ssh/config`
- `custom` — any file with explicit source/target mapping

## Claude Code Skill

Install the `/sync-team` skill for a guided experience:

```bash
cp -r skill/sync-team ~/.claude/skills/
```

Then use `/sync-team` in Claude Code to walk through the full sync flow.

## Development

```bash
git clone https://github.com/troylar/devsync-mcp
cd devsync-mcp
pip install -e ".[dev]"
pytest
```

## License

MIT
