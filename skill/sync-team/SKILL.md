# /sync-team — AI-Merge Team Configurations

Sync your team's standard dev configurations with intelligent AI-powered merging. This skill pulls team config profiles and uses your IDE's LLM to intelligently merge them with your existing personal configurations — preserving your customizations while incorporating team standards.

## Prerequisites

The `devsync-mcp` MCP server must be configured. Add to your MCP settings:

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

## Workflow

### Step 1: Ask for the team profile

Ask the user for their team config repository URL if not already known:

> "What's the Git URL for your team's config profile? (e.g., https://github.com/acme/team-configs)"

### Step 2: Pull the team profile

Use the `pull_team_profile` MCP tool:

```
pull_team_profile(git_url="<user's URL>")
```

Report the profile name, version, and number of configs found.

### Step 3: Show available configs

Use `list_profile_configs` with the namespace from step 2:

```
list_profile_configs(namespace="<namespace>")
```

Present the list to the user in a readable format:

| Config | Type | Target | Description |
|--------|------|--------|-------------|
| ... | ... | ... | ... |

### Step 4: Check current status

Use `get_merge_status` to see what's already been merged:

```
get_merge_status(namespace="<namespace>")
```

Show which configs are pending, merged, or changed since last merge.

### Step 5: Preview and merge each config

For each config the user wants to merge (or all pending ones):

1. **Preview**: Call `preview_merge(namespace, config_name)` to get both source (team) and target (your current) content.

2. **Analyze**: Read both contents carefully. Understand the semantics:
   - For shell profiles: identify aliases, exports, PATH additions, functions
   - For git configs: identify sections, settings, aliases
   - For AI rules: identify standards, conventions, patterns
   - For editor configs: identify formatting rules, settings

3. **Merge intelligently**:
   - Preserve ALL of the user's existing personal customizations
   - Add team additions that don't conflict
   - For conflicts, prefer team standards but add a comment noting the user's original value
   - Add a comment header noting the merge: `# Merged from <profile_name> on <date>`
   - Maintain the file's original structure and formatting style

4. **Present the merge**: Show the user the proposed merged content and explain what changed.

5. **Apply**: Once approved, call `apply_merge(namespace, config_name, merged_content, target_path)`.

### Step 6: Summary

After all merges, show a summary:
- Number of configs merged
- Number skipped
- Backup locations (from apply_merge responses)
- How to restore if needed: "Use `restore_backup` with the backup path"

## Quick Sync

For returning users, use `sync_all` to check for updates:

```
sync_all(namespace="<namespace>")
```

This pulls latest changes and shows what needs attention. Only re-merge configs that are "pending" (new) or where the team profile has been updated.

## Rollback

If the user wants to undo a merge:

1. `list_backups(profile_name="<namespace>")` — find the backup
2. `restore_backup(backup_path="<path>", target_path="<original>")` — restore it

## Tips

- Always create backups before merging (apply_merge does this automatically)
- For first-time setup, merge all configs in order
- For updates, only merge configs with "pending" or "changed" status
- Shell profiles are the most sensitive — always show the diff to the user before applying
