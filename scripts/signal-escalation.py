#!/usr/bin/env python3
"""
Signal Escalation Protocol
Ensures agents signal completion and escalates missing signals to @Automator.
Part of the GitHub Master Plan for perfect agent-signaled commits.
"""

import os
import json
import time
from datetime import datetime, timedelta
import logging
import subprocess

# Configuration
CONFIG = {
    "expected_signals": {
        "chapter_drafting": {
            "agent": "logos",
            "action": "chapter_complete",
            "timeout_minutes": 120,  # 2 hours for chapter drafting
            "escalation_steps": [
                {"minutes": 5, "action": "prompt_agent"},
                {"minutes": 10, "action": "notify_automator"},
                {"minutes": 15, "action": "investigate_status"}
            ]
        },
        "research_verification": {
            "agent": "nova",
            "action": "research_verified",
            "timeout_minutes": 30,  # 30 minutes for research verification
            "escalation_steps": [
                {"minutes": 5, "action": "prompt_agent"},
                {"minutes": 10, "action": "notify_automator"}
            ]
        },
        "chapter_locking": {
            "agent": "ember",
            "action": "chapter_locked",
            "timeout_minutes": 60,  # 1 hour for chapter locking
            "escalation_steps": [
                {"minutes": 5, "action": "prompt_agent"},
                {"minutes": 15, "action": "notify_automator"},
                {"minutes": 30, "action": "investigate_status"}
            ]
        },
        "verification": {
            "agent": "vault",
            "action": "verification_complete",
            "timeout_minutes": 1440,  # 24 hours for daily verification
            "escalation_steps": [
                {"minutes": 60, "action": "prompt_agent"},
                {"minutes": 120, "action": "notify_automator"}
            ]
        }
    },
    "log_file": "/Users/eroomybot/.openclaw/workspace/agents/main/memory/signal-escalation.log",
    "status_file": "/Users/eroomybot/.openclaw/workspace/agents/main/memory/signal-escalation-status.json"
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

class SignalEscalation:
    def __init__(self):
        self.status = self.load_status()
        
    def load_status(self):
        """Load escalation status from file."""
        if os.path.exists(CONFIG["status_file"]):
            try:
                with open(CONFIG["status_file"], 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading status file: {e}")
        
        # Default status
        return {
            "active_escalations": {},
            "completed_signals": [],
            "escalation_history": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }
    
    def save_status(self):
        """Save escalation status to file."""
        try:
            with open(CONFIG["status_file"], 'w') as f:
                json.dump(self.status, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving status file: {e}")
    
    def check_expected_signals(self):
        """Check for expected signals that haven't been received."""
        current_time = datetime.now()
        missing_signals = []
        
        # Load signal log to see what's been received
        signal_log = self.load_signal_log()
        received_signals = [(s.get("agent"), s.get("action")) for s in signal_log]
        
        for signal_name, signal_config in CONFIG["expected_signals"].items():
            agent = signal_config["agent"]
            action = signal_config["action"]
            
            # Check if this signal has been received
            if (agent, action) in received_signals:
                continue  # Signal received, no escalation needed
            
            # Check if we're already escalating this
            escalation_key = f"{agent}_{action}"
            if escalation_key in self.status["active_escalations"]:
                # Already escalating, check next steps
                self.check_escalation_progress(escalation_key, signal_config, current_time)
                continue
            
            # New missing signal - start escalation
            logger.warning(f"Missing signal: {agent} - {action}")
            missing_signals.append({
                "signal_name": signal_name,
                "agent": agent,
                "action": action,
                "expected_within_minutes": signal_config["timeout_minutes"],
                "detected_at": current_time.isoformat()
            })
            
            # Start escalation
            self.start_escalation(escalation_key, signal_config, current_time)
        
        return missing_signals
    
    def load_signal_log(self):
        """Load agent signal log."""
        log_file = "/Users/eroomybot/.openclaw/workspace/agents/main/memory/agent-signals.log"
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def start_escalation(self, escalation_key, signal_config, start_time):
        """Start escalation process for missing signal."""
        escalation = {
            "started_at": start_time.isoformat(),
            "agent": signal_config["agent"],
            "action": signal_config["action"],
            "timeout_minutes": signal_config["timeout_minutes"],
            "escalation_steps": signal_config["escalation_steps"].copy(),
            "current_step": 0,
            "step_history": [],
            "status": "active"
        }
        
        self.status["active_escalations"][escalation_key] = escalation
        self.save_status()
        
        logger.info(f"Started escalation for {escalation_key}")
        
        # Execute first escalation step
        self.execute_escalation_step(escalation_key, 0)
    
    def check_escalation_progress(self, escalation_key, signal_config, current_time):
        """Check if next escalation step should be executed."""
        escalation = self.status["active_escalations"][escalation_key]
        start_time = datetime.fromisoformat(escalation["started_at"])
        
        # Calculate minutes since escalation started
        minutes_elapsed = (current_time - start_time).total_seconds() / 60
        
        # Check if we should move to next step
        current_step = escalation["current_step"]
        if current_step < len(signal_config["escalation_steps"]):
            next_step_config = signal_config["escalation_steps"][current_step]
            
            if minutes_elapsed >= next_step_config["minutes"]:
                # Time for next step
                self.execute_escalation_step(escalation_key, current_step)
                
                # Move to next step
                escalation["current_step"] += 1
                self.save_status()
    
    def execute_escalation_step(self, escalation_key, step_index):
        """Execute a specific escalation step."""
        escalation = self.status["active_escalations"][escalation_key]
        signal_config = CONFIG["expected_signals"][self.get_signal_name(escalation_key)]
        
        if step_index >= len(signal_config["escalation_steps"]):
            return
        
        step_config = signal_config["escalation_steps"][step_index]
        action = step_config["action"]
        
        # Record step execution
        step_record = {
            "step": step_index,
            "action": action,
            "executed_at": datetime.now().isoformat(),
            "minutes_elapsed": step_config["minutes"]
        }
        
        escalation["step_history"].append(step_record)
        
        # Execute the action
        if action == "prompt_agent":
            self.prompt_agent(escalation["agent"], escalation["action"])
        elif action == "notify_automator":
            self.notify_automator(escalation_key, escalation)
        elif action == "investigate_status":
            self.investigate_status(escalation["agent"])
        
        logger.info(f"Executed escalation step {step_index}: {action} for {escalation_key}")
        self.save_status()
    
    def get_signal_name(self, escalation_key):
        """Get signal name from escalation key."""
        for name, config in CONFIG["expected_signals"].items():
            if f"{config['agent']}_{config['action']}" == escalation_key:
                return name
        return "unknown"
    
    def prompt_agent(self, agent, action):
        """Prompt agent to send signal."""
        prompt_message = f"""
        ⚠️ SIGNAL REMINDER ⚠️
        
        Agent: {agent}
        Action: {action}
        
        You have not sent the expected signal for your completed work.
        Please send the signal immediately to maintain GitHub protocol compliance.
        
        Expected signal file: {action}.signal
        Location: Your workspace root directory
        
        Time: {datetime.now().isoformat()}
        
        This is an automated reminder from the Signal Escalation Protocol.
        """
        
        # In a real implementation, this would send a message to the agent
        # For now, we'll log it
        logger.info(f"Prompting agent {agent} for signal {action}")
        logger.info(prompt_message)
        
        # Create a reminder file in agent's workspace
        reminder_file = f"/Users/eroomybot/.openclaw/workspace/agents/{agent}/signal_reminder.txt"
        try:
            with open(reminder_file, 'w') as f:
                f.write(prompt_message)
            logger.info(f"Created reminder file: {reminder_file}")
        except IOError as e:
            logger.error(f"Error creating reminder file: {e}")
    
    def notify_automator(self, escalation_key, escalation):
        """Notify @Automator of missing signal."""
        notification = f"""
        🚨 ESCALATION NOTIFICATION 🚨
        
        Missing Agent Signal Detected!
        
        Agent: {escalation['agent']}
        Action: {escalation['action']}
        Escalation Key: {escalation_key}
        Started: {escalation['started_at']}
        Timeout: {escalation['timeout_minutes']} minutes
        
        Steps Taken:
        {json.dumps(escalation['step_history'], indent=2)}
        
        Current Status: Agent has not signaled completion
        
        Required Action: Investigate why agent {escalation['agent']} 
        has not sent signal for {escalation['action']}
        
        Time: {datetime.now().isoformat()}
        
        This notification is part of the GitHub Master Plan signal enforcement.
        """
        
        logger.warning(f"Notifying @Automator: {notification}")
        
        # In a real implementation, this would send a message to @Automator
        # For now, we'll create a notification file
        notification_file = "/Users/eroomybot/.openclaw/workspace/agents/main/memory/automator-notifications.log"
        try:
            with open(notification_file, 'a') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Notification at {datetime.now().isoformat()}\n")
                f.write(notification)
                f.write(f"\n{'='*80}\n")
            logger.info(f"Logged notification to {notification_file}")
        except IOError as e:
            logger.error(f"Error logging notification: {e}")
    
    def investigate_status(self, agent):
        """Investigate agent status."""
        investigation = f"""
        🔍 AGENT STATUS INVESTIGATION
        
        Agent: {agent}
        Investigation Time: {datetime.now().isoformat()}
        
        Checks:
        1. Workspace exists: {os.path.exists(f'/Users/eroomybot/.openclaw/workspace/agents/{agent}')}
        2. Recent activity: Checking...
        3. Session status: Unknown
        4. Signal files: Checking...
        
        Investigation initiated due to missing signal.
        """
        
        logger.info(f"Investigating agent {agent} status")
        
        # Check for recent files in agent workspace
        workspace_path = f"/Users/eroomybot/.openclaw/workspace/agents/{agent}"
        if os.path.exists(workspace_path):
            try:
                # List recent files
                result = subprocess.run(
                    ["find", workspace_path, "-type", "f", "-mtime", "-1"],
                    capture_output=True,
                    text=True
                )
                recent_files = result.stdout.strip().split('\n')
                recent_files = [f for f in recent_files if f]  # Remove empty strings
                
                investigation += f"\nRecent files (last 24h): {len(recent_files)} found\n"
                if recent_files:
                    investigation += "Sample:\n"
                    for file in recent_files[:5]:
                        investigation += f"  - {file}\n"
                
            except subprocess.CalledProcessError as e:
                investigation += f"\nError checking recent files: {e}\n"
        else:
            investigation += "\n❌ Workspace does not exist!\n"
        
        # Log investigation
        investigation_file = f"/Users/eroomybot/.openclaw/workspace/agents/main/memory/agent-investigations.log"
        try:
            with open(investigation_file, 'a') as f:
                f.write(f"\n{'='*80}\n")
                f.write(investigation)
                f.write(f"\n{'='*80}\n")
            logger.info(f"Logged investigation to {investigation_file}")
        except IOError as e:
            logger.error(f"Error logging investigation: {e}")
    
    def check_for_received_signals(self):
        """Check if any escalated signals have been received."""
        signal_log = self.load_signal_log()
        
        for escalation_key in list(self.status["active_escalations"].keys()):
            escalation = self.status["active_escalations"][escalation_key]
            agent = escalation["agent"]
            action = escalation["action"]
            
            # Check if signal has been received
            signal_received = False
            for signal in signal_log:
                if signal.get("agent") == agent and signal.get("action") == action:
                    signal_received = True
                    break
            
            if signal_received:
                # Signal received - complete escalation
                self.complete_escalation(escalation_key)
    
    def complete_escalation(self, escalation_key):
        """Complete an escalation (signal received)."""
        escalation = self.status["active_escalations"].pop(escalation_key, None)
        if escalation:
            escalation["completed_at"] = datetime.now().isoformat()
            escalation["status"] = "completed"
            
            self.status["completed_signals"].append(escalation)
            self.save_status()
            
            logger.info(f"✅ Escalation completed for {escalation_key} - signal received")
    
    def run_monitoring_cycle(self):
        """Run one monitoring cycle."""
        logger.info("Running signal escalation monitoring cycle")
        
        # Check for missing signals
        missing_signals = self.check_expected_signals()
        
        if missing_signals:
            logger.warning(f"Found {len(missing_signals)} missing signal(s)")
            for signal in missing_signals:
                logger.warning(f"  - {signal['agent']} - {signal['action']}")
        
        # Check if any escalated signals have been received
        self.check_for_received_signals()
        
        # Log status
        active_count = len(self.status["active_escalations"])
        completed_count = len(self.status["completed_signals"])
        
        logger.info(f"Escalation Status: {active_count} active, {completed_count} completed")
        
        return {
            "missing_signals": len(missing_signals),
            "active_escalations": active_count,
            "completed_signals": completed_count
        }

def main():
    """Main entry point."""
    escalation = SignalEscalation()
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Signal Escalation Protocol")
    parser.add_argument("--interval", type=int, default=300, help="Monitoring interval in seconds (default: 300)")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuous monitoring")
    
    args = parser.parse_args()
    
    if args.once:
        result = escalation.run_monitoring_cycle()
        print(json.dumps(result, indent=2))
    else:
        logger.info(f"🚀 Starting Signal Escalation Protocol (interval: {args.interval}s)")
        try:
            while True:
                escalation.run_monitoring_cycle()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("🛑 Signal escalation stopped by user")

if __name__ == "__main__":
    main()