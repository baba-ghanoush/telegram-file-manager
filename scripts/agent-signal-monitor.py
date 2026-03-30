#!/usr/bin/env python3
"""
Agent Signal Monitor
Monitors agent workspaces for completion signals and triggers GitHub commits.
Part of the GitHub Master Plan for perfect agent-signaled commits.
"""

import os
import json
import time
import hashlib
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configuration
CONFIG = {
    "agent_workspaces": {
        "logos": "/Users/eroomybot/.openclaw/workspace/agents/logos",
        "nova": "/Users/eroomybot/.openclaw/workspace/agents/nova",
        "ember": "/Users/eroomybot/.openclaw/workspace/agents/ember",
        "vault": "/Users/eroomybot/.openclaw/workspace/agents/vault"
    },
    "signal_files": {
        "chapter_complete": "chapter_complete.signal",
        "research_verified": "research_verified.signal",
        "chapter_locked": "chapter_locked.signal",
        "verification_complete": "verification_complete.signal"
    },
    "monitor_interval": 60,  # seconds
    "github_repo": "/Users/eroomybot/.openclaw/workspace/skills/telegram-file-manager",
    "log_file": "/Users/eroomybot/.openclaw/workspace/agents/main/memory/github-signal-monitor.log"
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentSignalMonitor:
    def __init__(self):
        self.signals_processed = []
        self.last_check_time = datetime.now()
        
    def check_agent_workspace(self, agent_name, workspace_path):
        """Check an agent's workspace for signal files."""
        signals_found = []
        
        if not os.path.exists(workspace_path):
            logger.warning(f"Workspace not found for agent {agent_name}: {workspace_path}")
            return signals_found
        
        for signal_type, signal_file in CONFIG["signal_files"].items():
            signal_path = os.path.join(workspace_path, signal_file)
            if os.path.exists(signal_path):
                try:
                    # Read signal content
                    with open(signal_path, 'r') as f:
                        signal_content = f.read().strip()
                    
                    # Parse signal (format: JSON or key=value)
                    signal_data = self.parse_signal(signal_content, agent_name, signal_type)
                    signal_data["signal_file"] = signal_path
                    
                    signals_found.append(signal_data)
                    logger.info(f"Found signal: {agent_name} - {signal_type}")
                    
                except Exception as e:
                    logger.error(f"Error reading signal file {signal_path}: {e}")
        
        return signals_found
    
    def parse_signal(self, signal_content, agent_name, signal_type):
        """Parse signal content into structured data."""
        try:
            # Try to parse as JSON
            data = json.loads(signal_content)
        except json.JSONDecodeError:
            # Parse as key=value pairs
            data = {}
            for line in signal_content.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    data[key.strip()] = value.strip()
        
        # Ensure required fields
        timestamp = data.get("timestamp", datetime.now().isoformat())
        chapter = data.get("chapter", "")
        description = data.get("description", f"{agent_name} completed {signal_type}")
        
        return {
            "agent": agent_name,
            "action": signal_type,
            "timestamp": timestamp,
            "chapter": chapter,
            "description": description,
            "raw_data": data
        }
    
    def process_signal(self, signal_data):
        """Process a signal and trigger GitHub commit."""
        try:
            # Generate unique ID for this signal
            signal_id = hashlib.md5(
                f"{signal_data['agent']}_{signal_data['action']}_{signal_data['timestamp']}".encode()
            ).hexdigest()[:8]
            
            # Check if already processed
            if signal_id in self.signals_processed:
                logger.info(f"Signal already processed: {signal_id}")
                return False
            
            # Trigger GitHub workflow via repository_dispatch
            self.trigger_github_workflow(signal_data)
            
            # Clean up signal file
            signal_file = signal_data.get("signal_file")
            if signal_file and os.path.exists(signal_file):
                os.remove(signal_file)
                logger.info(f"Cleaned up signal file: {signal_file}")
            
            # Record as processed
            self.signals_processed.append(signal_id)
            
            # Log to signal log
            self.log_signal_to_file(signal_data, signal_id)
            
            logger.info(f"✅ Processed signal: {signal_data['agent']} - {signal_data['action']} (ID: {signal_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return False
    
    def trigger_github_workflow(self, signal_data):
        """Trigger GitHub Actions workflow via repository_dispatch."""
        try:
            # Change to GitHub repo directory
            original_cwd = os.getcwd()
            os.chdir(CONFIG["github_repo"])
            
            # Create payload for repository_dispatch
            payload = {
                "agent": signal_data["agent"],
                "action": signal_data["action"],
                "chapter": signal_data["chapter"],
                "timestamp": signal_data["timestamp"],
                "description": signal_data["description"]
            }
            
            # In a real implementation, this would use GitHub API
            # For now, we'll simulate by creating a local file that the workflow can detect
            trigger_file = f".github/triggers/signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(trigger_file), exist_ok=True)
            
            with open(trigger_file, 'w') as f:
                json.dump(payload, f, indent=2)
            
            logger.info(f"Created trigger file: {trigger_file}")
            
            # Commit the trigger file
            subprocess.run(["git", "add", trigger_file], check=True)
            commit_message = f"""[SIGNAL] {signal_data['agent']} {signal_data['action']} - Signal detected

Agent: {signal_data['agent']}
Action: {signal_data['action']}
Chapter: {signal_data['chapter']}
Timestamp: {signal_data['timestamp']}
Signal ID: {hashlib.md5(json.dumps(payload).encode()).hexdigest()[:8]}

Signal detected by Agent Signal Monitor.
Triggering GitHub workflow for commit-on-signal protocol.
"""
            
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            
            logger.info(f"✅ Triggered GitHub workflow for {signal_data['agent']} - {signal_data['action']}")
            
            # Clean up trigger file after push
            os.remove(trigger_file)
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"[CLEANUP] Remove trigger file {os.path.basename(trigger_file)}"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            
            os.chdir(original_cwd)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            os.chdir(original_cwd)
            raise
        except Exception as e:
            logger.error(f"Error triggering GitHub workflow: {e}")
            os.chdir(original_cwd)
            raise
    
    def log_signal_to_file(self, signal_data, signal_id):
        """Log processed signal to main memory file."""
        log_entry = {
            "signal_id": signal_id,
            "processed_at": datetime.now().isoformat(),
            **signal_data
        }
        
        log_file = "/Users/eroomybot/.openclaw/workspace/agents/main/memory/agent-signals.log"
        
        # Read existing log
        log_data = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                log_data = []
        
        # Add new entry
        log_data.append(log_entry)
        
        # Write back
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Logged signal to {log_file}")
    
    def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("🚀 Starting Agent Signal Monitor")
        logger.info(f"Monitoring agents: {list(CONFIG['agent_workspaces'].keys())}")
        logger.info(f"Check interval: {CONFIG['monitor_interval']} seconds")
        
        try:
            while True:
                current_time = datetime.now()
                logger.debug(f"Checking for signals at {current_time.isoformat()}")
                
                signals_found = []
                
                # Check each agent workspace
                for agent_name, workspace_path in CONFIG["agent_workspaces"].items():
                    agent_signals = self.check_agent_workspace(agent_name, workspace_path)
                    signals_found.extend(agent_signals)
                
                # Process found signals
                for signal in signals_found:
                    self.process_signal(signal)
                
                # Update last check time
                self.last_check_time = current_time
                
                # Sleep until next check
                time.sleep(CONFIG["monitor_interval"])
                
        except KeyboardInterrupt:
            logger.info("🛑 Signal monitor stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitor loop error: {e}")
            raise
    
    def run_once(self):
        """Run a single check (for testing or manual execution)."""
        logger.info("Running single check for agent signals")
        
        signals_found = []
        for agent_name, workspace_path in CONFIG["agent_workspaces"].items():
            agent_signals = self.check_agent_workspace(agent_name, workspace_path)
            signals_found.extend(agent_signals)
        
        if signals_found:
            logger.info(f"Found {len(signals_found)} signal(s)")
            for signal in signals_found:
                self.process_signal(signal)
        else:
            logger.info("No signals found")
        
        return len(signals_found)

def main():
    """Main entry point."""
    monitor = AgentSignalMonitor()
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Monitor agent workspaces for signals")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuous monitoring")
    parser.add_argument("--interval", type=int, default=CONFIG["monitor_interval"], help="Check interval in seconds")
    
    args = parser.parse_args()
    
    if args.interval != CONFIG["monitor_interval"]:
        CONFIG["monitor_interval"] = args.interval
    
    if args.once:
        monitor.run_once()
    else:
        monitor.monitor_loop()

if __name__ == "__main__":
    main()