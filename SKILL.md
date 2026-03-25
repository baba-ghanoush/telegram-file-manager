---
name: telegram-file-manager
description: Automatically organize Telegram attachments by stripping UUID suffixes, detecting duplicates, and distributing files to correct workspaces based on filename patterns. Also handles email attachments and general file organization across the multi-agent system.
---

# Telegram & Email File Manager

Specialized file organization skill for managing attachments from Telegram, email, and other sources across the multi-agent system. Solves the problem of duplicate files with UUID suffixes and ensures proper distribution to agent workspaces.

## When to Use This Skill

Use this skill when:
- Telegram attachments arrive with UUID suffixes (e.g., `filename---uuid.md`)
- Email attachments need to be organized and distributed
- Files have been sent multiple times and need deduplication
- You need to find "lost" files that were sent but not properly saved
- Setting up automatic file distribution for new agents
- Cleaning up duplicate files across workspaces

## Core Capabilities

### 1. UUID Suffix Stripping
- Detects patterns: `filename---uuid.ext` or `filename-uuid.ext`
- Extracts clean filename: `filename.ext`
- Preserves version numbers: `filename_v1---uuid.md` → `filename_v1.md`

### 2. Duplicate Detection
- Compares file content (MD5 hash)
- Tracks when files were last processed
- Avoids re-processing identical files
- Maintains processing log in `~/.openclaw/workspace/agents/main/memory/file-processing-log.json`

### 3. Smart Distribution
- **Telegram attachments:** `/Users/eroomybot/.openclaw/media/inbound/`
- **Email attachments:** Check Himalaya mail directories
- **Pattern-based routing:**
  - `*Logos*` → Logos workspace
  - `*Nova*` → Nova workspace  
  - `*Ember*` → Ember workspace
  - `*Vault*` → Vault workspace
  - `*bluejay*` → All Blue Jay agent workspaces
  - Default: Main workspace memory directory

### 4. Multi-Source Support
- Telegram media directory
- Email attachments (via himalaya CLI)
- Workspace memory directories
- Project source directories

## File Patterns & Routing Rules

### Telegram Attachments
**Source:** `/Users/eroomybot/.openclaw/media/inbound/`
**Pattern:** `*---*.md` or `*-*.md` (UUID suffix)
**Action:** Strip UUID, route based on filename

### Email Attachments  
**Source:** Himalaya mail directories
**Pattern:** Attachment files in emails
**Action:** Extract, clean, route based on subject/filename

### Blue Jay Project Files
**Pattern:** `*bluejay*`, `*BlueJay*`, `*Blue Jay*`
**Routing:** All Blue Jay agents (Logos, Nova, Ember) + main memory

## Usage Examples

### Basic Telegram File Organization
```bash
# Process all Telegram attachments from last 24 hours
telegram-file-manager process --source telegram --hours 24

# Process specific file pattern
telegram-file-manager process --pattern "*runbook*"

# Dry run (show what would be done)
telegram-file-manager process --dry-run
```

### Email Attachment Management
```bash
# Process email attachments from last 48 hours
telegram-file-manager process --source email --hours 48

# Process attachments from specific sender
telegram-file-manager process --sender "important@example.com"
```

### Duplicate Cleanup
```bash
# Find duplicates across all workspaces
telegram-file-manager duplicates --scan

# Remove duplicates (keep oldest)
telegram-file-manager duplicates --cleanup
```

### File Search & Recovery
```bash
# Find files sent multiple times
telegram-file-manager search --duplicates

# Find "lost" files not in expected locations
telegram-file-manager search --missing

# Recover files from processing log
telegram-file-manager recover --filename "BlueJay_Runbook_v1.md"
```

## Configuration

### Processing Log
Location: `~/.openclaw/workspace/agents/main/memory/file-processing-log.json`
```json
{
  "processed_files": {
    "filename.md": {
      "source_path": "/path/to/original---uuid.md",
      "destination": "/path/to/clean/filename.md",
      "hash": "md5_hash",
      "timestamp": "2026-03-25T01:48:00Z",
      "agent_routed": ["logos", "ember"]
    }
  },
  "duplicates_detected": {
    "filename.md": ["path1", "path2", "path3"]
  }
}
```

### Routing Rules Configuration
Location: `~/.openclaw/workspace/agents/main/memory/file-routing-rules.json`
```json
{
  "patterns": {
    "*Logos*": ["/Users/eroomybot/.openclaw/workspace/agents/logos/"],
    "*Nova*": ["/Users/eroomybot/.openclaw/workspace/agents/nova/"],
    "*Ember*": ["/Users/eroomybot/.openclaw/workspace/agents/ember/"],
    "*Vault*": ["/Users/eroomybot/.openclaw/workspace/agents/vault/"],
    "*bluejay*": [
      "/Users/eroomybot/.openclaw/workspace/agents/logos/",
      "/Users/eroomybot/.openclaw/workspace/agents/nova/",
      "/Users/eroomybot/.openclaw/workspace/agents/ember/",
      "/Users/eroomybot/.openclaw/workspace/agents/main/memory/"
    ]
  },
  "default_destination": "/Users/eroomybot/.openclaw/workspace/agents/main/memory/"
}
```

## Safety & Validation

### Rate Limiting
- Maximum 100 files processed per run
- 1-second delay between file operations
- Skip files larger than 10MB

### Validation
- Verify file integrity after copy (hash comparison)
- Check destination permissions before writing
- Maintain backup of original files for 7 days
- Log all operations with timestamps

### Error Handling
- Continue on single file errors
- Report failures at end of run
- Retry failed operations once
- Alert on permission errors

## Integration Points

### With Himalaya Skill
- Uses `himalaya` CLI to access email attachments
- Parses email metadata for routing context
- Respects email folder structure

### With Multi-Agent System
- Updates agent workspaces automatically
- Notifies agents of new files (optional)
- Maintains file consistency across system

### With GitHub Protocol
- Files ready for commit after organization
- Clean filenames suitable for GitHub
- Version tracking through processing log

## External Endpoints

No external API endpoints. All operations are local:
- File system operations
- Himalaya CLI for email
- Local hash calculations

## Security & Privacy

- No external data sharing
- Local file operations only
- No personal data collection
- All processing logged locally
- Original files preserved (read-only)
- No automatic deletion without confirmation

## Cost Considerations

- Free local operations only
- No API calls or external services
- Minimal system resource usage
- Efficient duplicate detection (hash-based)