#!/usr/bin/env python3
"""
Standalone Process History Logger
Usage: python3 log_processes_to_notion.py
"""

import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from process_history_logger import ProcessHistoryLogger


def main():
    """Log recent processes to Notion database"""
    try:
        # Load configuration
        config_file = os.path.join(os.path.dirname(__file__), 'config.json')
        
        if not os.path.exists(config_file):
            print("❌ config.json not found!")
            return 1
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Check if process history is configured
        if 'process_history_db_id' not in config.get('notion', {}):
            print("⚠️  Process history database not configured in config.json")
            print("   Add 'process_history_db_id' to the 'notion' section")
            return 0
        
        # Initialize logger
        print("📊 Logging GPU process history to Notion...")
        
        logger = ProcessHistoryLogger(
            notion_token=config['notion']['token'],
            database_id=config['notion']['process_history_db_id'],
            db_path=config['database']['path']
        )
        
        # Log all recent processes (last hour)
        logger.log_all_recent_processes()
        
        print("✅ Process history logged successfully")
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
