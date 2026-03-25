#!/usr/bin/env python3
"""
Telegram & Email File Processor
Automatically organizes attachments by stripping UUID suffixes and routing to correct workspaces.
"""

import os
import re
import sys
import json
import hashlib
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configuration
CONFIG_DIR = Path.home() / ".openclaw" / "workspace" / "agents" / "main" / "memory"
PROCESSING_LOG = CONFIG_DIR / "file-processing-log.json"
ROUTING_RULES = CONFIG_DIR / "file-routing-rules.json"

# Default routing patterns
DEFAULT_ROUTING_RULES = {
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

# UUID pattern matching
UUID_PATTERN = re.compile(r'---[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}')
HYPHEN_UUID_PATTERN = re.compile(r'-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}')


class FileProcessor:
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.processing_log = self._load_processing_log()
        self.routing_rules = self._load_routing_rules()
        
    def _load_processing_log(self) -> Dict:
        """Load or create processing log."""
        if PROCESSING_LOG.exists():
            with open(PROCESSING_LOG, 'r') as f:
                return json.load(f)
        return {"processed_files": {}, "duplicates_detected": {}}
    
    def _load_routing_rules(self) -> Dict:
        """Load or create routing rules."""
        if ROUTING_RULES.exists():
            with open(ROUTING_RULES, 'r') as f:
                return json.load(f)
        return DEFAULT_ROUTING_RULES
    
    def _save_processing_log(self):
        """Save processing log."""
        if not self.dry_run:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(PROCESSING_LOG, 'w') as f:
                json.dump(self.processing_log, f, indent=2)
    
    def calculate_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of file."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def clean_filename(self, filename: str) -> str:
        """Remove UUID suffix from filename."""
        # Try ---uuid pattern first
        clean = UUID_PATTERN.sub('', filename)
        if clean != filename:
            return clean
        
        # Try -uuid pattern
        clean = HYPHEN_UUID_PATTERN.sub('', filename)
        return clean
    
    def get_destinations(self, clean_filename: str) -> List[Path]:
        """Get destination paths based on filename patterns."""
        destinations = []
        
        # Check pattern matches
        for pattern, paths in self.routing_rules.get("patterns", {}).items():
            if self._pattern_match(clean_filename, pattern):
                for path in paths:
                    dest = Path(path)
                    if dest.exists() or self.dry_run:
                        destinations.append(dest)
        
        # Add default destination if no matches
        if not destinations:
            default_path = self.routing_rules.get("default_destination")
            if default_path:
                dest = Path(default_path)
                if dest.exists() or self.dry_run:
                    destinations.append(dest)
        
        return destinations
    
    def _pattern_match(self, filename: str, pattern: str) -> bool:
        """Simple pattern matching with wildcards."""
        pattern = pattern.lower()
        filename = filename.lower()
        
        if '*' in pattern:
            # Convert wildcard pattern to regex
            regex_pattern = pattern.replace('*', '.*')
            return re.match(regex_pattern, filename) is not None
        else:
            return pattern in filename
    
    def is_duplicate(self, filepath: Path, clean_filename: str) -> Tuple[bool, Optional[str]]:
        """Check if file is a duplicate."""
        file_hash = self.calculate_hash(filepath)
        
        # Check by hash
        for processed_file, info in self.processing_log.get("processed_files", {}).items():
            if info.get("hash") == file_hash:
                return True, processed_file
        
        # Check by clean filename in processing log
        if clean_filename in self.processing_log.get("processed_files", {}):
            return True, clean_filename
        
        return False, None
    
    def process_file(self, filepath: Path) -> Dict:
        """Process a single file."""
        results = {
            "original": str(filepath),
            "cleaned": None,
            "destinations": [],
            "duplicate": False,
            "duplicate_of": None,
            "error": None,
            "skipped": False
        }
        
        try:
            # Clean filename
            clean_name = self.clean_filename(filepath.name)
            results["cleaned"] = clean_name
            
            # Check if duplicate
            is_dup, dup_of = self.is_duplicate(filepath, clean_name)
            if is_dup:
                results["duplicate"] = True
                results["duplicate_of"] = dup_of
                results["skipped"] = True
                
                # Update duplicates log
                if clean_name not in self.processing_log.get("duplicates_detected", {}):
                    self.processing_log.setdefault("duplicates_detected", {})[clean_name] = []
                self.processing_log["duplicates_detected"][clean_name].append(str(filepath))
                
                if self.verbose:
                    print(f"  ⚠️  Duplicate: {filepath.name} → {clean_name} (duplicate of {dup_of})")
                return results
            
            # Get destinations
            destinations = self.get_destinations(clean_name)
            if not destinations:
                results["error"] = "No valid destinations found"
                return results
            
            results["destinations"] = [str(d) for d in destinations]
            
            # Process for each destination
            file_hash = self.calculate_hash(filepath)
            copied_paths = []
            
            for dest_dir in destinations:
                dest_path = dest_dir / clean_name
                
                if self.verbose:
                    print(f"  📄 {filepath.name} → {dest_path}")
                
                if not self.dry_run:
                    # Ensure destination directory exists
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(filepath, dest_path)
                    copied_paths.append(str(dest_path))
            
            # Update processing log
            self.processing_log.setdefault("processed_files", {})[clean_name] = {
                "source_path": str(filepath),
                "destinations": copied_paths,
                "hash": file_hash,
                "timestamp": datetime.now().isoformat(),
                "agent_routed": [d.name for d in destinations if "agents" in str(d)]
            }
            
        except Exception as e:
            results["error"] = str(e)
            if self.verbose:
                print(f"  ❌ Error processing {filepath.name}: {e}")
        
        return results
    
    def process_directory(self, directory: Path, hours: Optional[int] = None) -> List[Dict]:
        """Process all files in directory."""
        results = []
        
        if not directory.exists():
            print(f"Directory not found: {directory}")
            return results
        
        # Filter by modification time if hours specified
        cutoff_time = None
        if hours:
            cutoff_time = datetime.now() - timedelta(hours=hours)
        
        files_processed = 0
        for filepath in directory.iterdir():
            if filepath.is_file():
                # Check modification time
                if cutoff_time:
                    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    if mtime < cutoff_time:
                        continue
                
                # Process file
                result = self.process_file(filepath)
                results.append(result)
                files_processed += 1
                
                # Rate limiting
                if not self.dry_run and files_processed % 10 == 0:
                    self._save_processing_log()
        
        # Final save
        if not self.dry_run:
            self._save_processing_log()
        
        return results
    
    def find_duplicates(self, scan_directories: List[Path]) -> Dict:
        """Find duplicate files across directories."""
        hash_map = {}
        duplicates = {}
        
        for directory in scan_directories:
            if not directory.exists():
                continue
            
            for filepath in directory.rglob("*"):
                if filepath.is_file() and filepath.suffix in ['.md', '.txt', '.json', '.py']:
                    try:
                        file_hash = self.calculate_hash(filepath)
                        if file_hash in hash_map:
                            duplicates.setdefault(file_hash, []).append(str(filepath))
                            if file_hash not in hash_map:
                                duplicates[file_hash].append(hash_map[file_hash])
                        else:
                            hash_map[file_hash] = str(filepath)
                    except Exception as e:
                        if self.verbose:
                            print(f"  ❌ Error hashing {filepath}: {e}")
        
        return duplicates
    
    def search_files(self, pattern: str, search_dirs: List[Path]) -> List[Path]:
        """Search for files matching pattern."""
        matches = []
        search_pattern = pattern.lower()
        
        for directory in search_dirs:
            if not directory.exists():
                continue
            
            for filepath in directory.rglob("*"):
                if filepath.is_file() and search_pattern in filepath.name.lower():
                    matches.append(filepath)
        
        return matches


def main():
    parser = argparse.ArgumentParser(description="Telegram & Email File Processor")
    parser.add_argument("action", choices=["process", "duplicates", "search", "recover"],
                       help="Action to perform")
    parser.add_argument("--source", choices=["telegram", "email", "all"], default="telegram",
                       help="Source to process")
    parser.add_argument("--hours", type=int, default=24,
                       help="Process files from last N hours")
    parser.add_argument("--pattern", type=str,
                       help="File pattern to match")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be done without making changes")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    processor = FileProcessor(dry_run=args.dry_run, verbose=args.verbose)
    
    if args.action == "process":
        # Determine source directory
        if args.source in ["telegram", "all"]:
            telegram_dir = Path("/Users/eroomybot/.openclaw/media/inbound/")
            if telegram_dir.exists():
                print(f"Processing Telegram directory: {telegram_dir}")
                results = processor.process_directory(telegram_dir, args.hours)
                
                # Print summary
                processed = len([r for r in results if not r.get("skipped")])
                duplicates = len([r for r in results if r.get("duplicate")])
                errors = len([r for r in results if r.get("error")])
                
                print(f"\n📊 Summary:")
                print(f"  Processed: {processed} files")
                print(f"  Duplicates skipped: {duplicates}")
                print(f"  Errors: {errors}")
            else:
                print(f"Telegram directory not found: {telegram_dir}")
        
        # Note: Email processing would require himalaya integration
        # This is a placeholder for future expansion
        
    elif args.action == "duplicates":
        # Scan agent workspaces for duplicates
        scan_dirs = [
            Path("/Users/eroomybot/.openclaw/workspace/agents/logos/"),
            Path("/Users/eroomybot/.openclaw/workspace/agents/nova/"),
            Path("/Users/eroomybot/.openclaw/workspace/agents/ember/"),
            Path("/Users/eroomybot/.openclaw/workspace/agents/vault/"),
            Path("/Users/eroomybot/.openclaw/workspace/agents/main/memory/"),
        ]
        
        print("Scanning for duplicates...")
        duplicates = processor.find_duplicates(scan_dirs)
        
        if duplicates:
            print(f"\n🔍 Found {len(duplicates)} duplicate file groups:")
            for hash_val, files in duplicates.items():
                print(f"\n  Hash: {hash_val[:16]}...")
                for filepath in files:
                    print(f"    {filepath}")
        else:
            print("No duplicates found.")
    
    elif args.action == "search":
        if not args.pattern:
            print("Error: --pattern required for search action")
            return
        
        search_dirs = [
            Path("/Users/eroomybot/.openclaw/media/inbound/"),
            Path("/Users/eroomybot/.openclaw/workspace/agents/main/memory/"),
        ]
        
        print(f"Searching for pattern: {args.pattern}")
        matches = processor.search_files(args.pattern, search_dirs)
        
        if matches:
            print(f"\n🔍 Found {len(matches)} matches:")
            for match in matches:
                print(f"  {match}")
        else:
            print("No matches found.")
    
    elif args.action == "recover":
        if not args.pattern:
            print("Error: --pattern required for recover action")
            return
        
        # Search processing log for file
        clean_name = processor.clean_filename(args.pattern)
        if clean_name in processor.processing_log.get("processed_files", {}):
            info = processor.processing_log["processed_files"][clean_name]
            print(f"\n📁 File: {clean_name}")
            print(f"  Original: {info.get('source_path')}")
            print(f"  Destinations: {', '.join(info.get('destinations', []))}")
            print(f"  Timestamp: {info.get('timestamp')}")
        else:
            print(f"File not found in processing log: {clean_name}")


if __name__ == "__main__":
    main()