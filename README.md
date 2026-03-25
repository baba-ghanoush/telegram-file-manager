# Telegram & Email File Manager

A skill for automatically organizing Telegram and email attachments across the multi-agent system. Solves the problem of duplicate files with UUID suffixes and ensures proper distribution to agent workspaces.

## Problem Solved

When files are sent via Telegram or email to OpenClaw:
1. **Telegram adds UUID suffixes:** `filename---uuid.md`
2. **Files get "lost"** because agents look for `filename.md` but find `filename---uuid.md`
3. **Duplicates accumulate** when files are sent multiple times
4. **Manual distribution** is required to get files to correct agent workspaces

This skill automates all of that.

## Installation

### Via GitHub (Recommended)
```bash
# Clone the skill repository
git clone https://github.com/your-org/telegram-file-manager.git
cd telegram-file-manager

# Install to OpenClaw skills directory
cp -r . /Users/eroomybot/.openclaw/workspace/skills/telegram-file-manager/
```

### Manual Installation
```bash
# Create skill directory
mkdir -p /Users/eroomybot/.openclaw/workspace/skills/telegram-file-manager/

# Copy all files from this repository
cp -r * /Users/eroomybot/.openclaw/workspace/skills/telegram-file-manager/

# Make script executable (if allowed)
chmod +x /Users/eroomybot/.openclaw/workspace/skills/telegram-file-manager/scripts/file-processor.py
```

## Usage

### Basic File Processing
```bash
# Process all Telegram attachments from last 24 hours
telegram-file-manager process --source telegram --hours 24

# Process with verbose output
telegram-file-manager process --source telegram --verbose

# Dry run (show what would be done)
telegram-file-manager process --source telegram --dry-run
```

### Finding Duplicates
```bash
# Scan all agent workspaces for duplicates
telegram-file-manager duplicates --scan

# Clean up duplicates (interactive)
telegram-file-manager duplicates --cleanup
```

### File Search & Recovery
```bash
# Search for files by pattern
telegram-file-manager search --pattern "BlueJay"

# Find "lost" files not in expected locations
telegram-file-manager search --missing

# Recover file information from processing log
telegram-file-manager recover --filename "BlueJay_Logos_Runbook_v1.md"
```

## How It Works

### 1. UUID Suffix Detection
- Detects patterns: `filename---uuid.ext` or `filename-uuid.ext`
- Extracts clean filename: `filename.ext`
- Preserves version numbers: `filename_v1---uuid.md` → `filename_v1.md`

### 2. Duplicate Detection
- Compares file content using MD5 hash
- Tracks processing history in `file-processing-log.json`
- Skips files that have already been processed

### 3. Smart Routing
Files are routed based on filename patterns:

| Pattern | Destination |
|---------|-------------|
| `*Logos*` | Logos workspace |
| `*Nova*` | Nova workspace |
| `*Ember*` | Ember workspace |
| `*Vault*` | Vault workspace |
| `*bluejay*` | All Blue Jay agents + main memory |
| Default | Main workspace memory |

### 4. Processing Log
All operations are logged to:
```
~/.openclaw/workspace/agents/main/memory/file-processing-log.json
```

Example log entry:
```json
{
  "processed_files": {
    "BlueJay_Logos_Runbook_v1.md": {
      "source_path": "/Users/eroomybot/.openclaw/media/inbound/BlueJay_Logos_Runbook_v1---fef959cd-f3e5-40ac-8e93-1b846f656915.md",
      "destinations": [
        "/Users/eroomybot/.openclaw/workspace/agents/logos/BlueJay_Logos_Runbook_v1.md",
        "/Users/eroomybot/.openclaw/workspace/agents/ember/BlueJay_Logos_Runbook_v1.md"
      ],
      "hash": "a1b2c3d4e5f6...",
      "timestamp": "2026-03-25T01:48:00Z",
      "agent_routed": ["logos", "ember"]
    }
  }
}
```

## Integration with Multi-Agent System

### Automatic File Distribution
When a new file arrives:
1. Skill detects it in Telegram media directory
2. Strips UUID suffix
3. Routes to appropriate agent workspaces
4. Updates processing log
5. (Optional) Notifies relevant agents

### Email Support (Future)
- Integration with Himalaya CLI for email access
- Attachment extraction and processing
- Email metadata for routing decisions

## Safety Features

### Rate Limiting
- Maximum 100 files processed per run
- 1-second delay between file operations
- Skip files larger than 10MB

### Validation
- Verify file integrity after copy (hash comparison)
- Check destination permissions before writing
- Maintain backup of original files for 7 days

### Error Handling
- Continue on single file errors
- Report failures at end of run
- Retry failed operations once
- Alert on permission errors

## Configuration

### Routing Rules
Edit: `~/.openclaw/workspace/agents/main/memory/file-routing-rules.json`

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

### Processing Settings
- `--hours`: Process files from last N hours (default: 24)
- `--dry-run`: Preview changes without making them
- `--verbose`: Detailed output of all operations

## GitHub Protocol Compliance

This skill follows strict GitHub protocols:

1. **Clean filenames:** No UUID suffixes in repository
2. **Version tracking:** Processing log tracks all file versions
3. **Audit trail:** Complete history of file movements
4. **Consistency:** Same files across all agent workspaces

## Troubleshooting

### Common Issues

1. **"Directory not found"**
   - Check that Telegram media directory exists: `/Users/eroomybot/.openclaw/media/inbound/`
   - Verify agent workspace directories exist

2. **"Permission denied"**
   - Check file permissions on destination directories
   - Run with appropriate user permissions

3. **Files not being processed**
   - Check modification times with `--hours` parameter
   - Verify UUID pattern matches your files
   - Check processing log for previously processed files

4. **Incorrect routing**
   - Update routing rules in `file-routing-rules.json`
   - Check filename patterns match your files

### Debug Mode
```bash
# Run with maximum verbosity
telegram-file-manager process --source telegram --verbose --dry-run
```

## Future Enhancements

Planned features:
1. **Email integration** with Himalaya CLI
2. **Real-time monitoring** of Telegram/media directory
3. **Agent notifications** when new files arrive
4. **Webhook support** for external integrations
5. **GUI interface** for manual file management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request
5. Follow existing code style and patterns

## License

MIT License - see LICENSE file for details.