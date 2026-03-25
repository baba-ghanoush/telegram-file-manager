#!/bin/bash
# Installation script for Telegram File Manager skill

set -e

echo "📦 Installing Telegram File Manager Skill"
echo "=========================================="

# Check if OpenClaw skills directory exists
SKILLS_DIR="$HOME/.openclaw/workspace/skills"
if [ ! -d "$SKILLS_DIR" ]; then
    echo "❌ OpenClaw skills directory not found: $SKILLS_DIR"
    echo "   Make sure OpenClaw is installed and configured."
    exit 1
fi

# Skill name
SKILL_NAME="telegram-file-manager"
SKILL_PATH="$SKILLS_DIR/$SKILL_NAME"

# Create skill directory
echo "📁 Creating skill directory..."
mkdir -p "$SKILL_PATH"

# Copy all files
echo "📄 Copying skill files..."
cp -r . "$SKILL_PATH/"

# Make script executable
if [ -f "$SKILL_PATH/scripts/file-processor.py" ]; then
    echo "⚙️  Setting executable permissions..."
    chmod +x "$SKILL_PATH/scripts/file-processor.py"
fi

# Create configuration directories
echo "⚙️  Creating configuration directories..."
mkdir -p "$HOME/.openclaw/workspace/agents/main/memory"

# Create default routing rules if they don't exist
RULES_FILE="$HOME/.openclaw/workspace/agents/main/memory/file-routing-rules.json"
if [ ! -f "$RULES_FILE" ]; then
    echo "📝 Creating default routing rules..."
    cat > "$RULES_FILE" << 'EOF'
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
    ],
    "*runbook*": [
      "/Users/eroomybot/.openclaw/workspace/agents/main/memory/"
    ]
  },
  "default_destination": "/Users/eroomybot/.openclaw/workspace/agents/main/memory/"
}
EOF
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Test the skill:"
echo "   python $SKILL_PATH/scripts/file-processor.py --help"
echo ""
echo "2. Process Telegram files:"
echo "   python $SKILL_PATH/scripts/file-processor.py process --source telegram --dry-run"
echo ""
echo "3. Check the skill is recognized:"
echo "   openclaw skills list | grep telegram-file-manager"
echo ""
echo "📚 Documentation: $SKILL_PATH/README.md"