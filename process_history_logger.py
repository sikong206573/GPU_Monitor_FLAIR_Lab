"""
Process History Logger for Notion Database
Tracks GPU process lifecycle and logs to Notion database
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import requests


class ProcessHistoryLogger:
    """Log process history to Notion database"""
    
    def __init__(self, notion_token: str, database_id: str, db_path: str):
        """
        Initialize logger
        
        Args:
            notion_token: Notion API token
            database_id: Notion database ID for process history
            db_path: SQLite database path
        """
        self.notion_token = notion_token
        self.database_id = database_id
        self.db_path = db_path
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Track which processes we've already logged to Notion
        self.logged_processes = set()
    
    def log_process_session(self, gpu_id: int, pid: int, username: str):
        """
        Log a process session to Notion database
        
        Args:
            gpu_id: GPU ID
            pid: Process ID
            username: Username
        """
        try:
            # Check if already logged
            process_key = f"{gpu_id}_{pid}"
            if process_key in self.logged_processes:
                return
            
            # Get process statistics from SQLite
            stats = self.get_process_stats(gpu_id, pid)
            if not stats:
                return
            
            # Determine status
            status = "Running"
            if stats['is_ended']:
                status = "Completed"
            elif stats['avg_utilization'] < 5 and stats['duration_minutes'] > 10:
                status = "Idle Alert"
            
            # Create Notion database entry
            properties = {
                "Process": {
                    "title": [
                        {
                            "text": {
                                "content": f"GPU {gpu_id} - {username} - PID {pid}"
                            }
                        }
                    ]
                },
                "GPU ID": {
                    "select": {
                        "name": f"GPU {gpu_id}"
                    }
                },
                "Username": {
                    "select": {
                        "name": username
                    }
                },
                "PID": {
                    "number": pid
                },
                "Start Time": {
                    "date": {
                        "start": stats['start_time']
                    }
                },
                "Avg Utilization": {
                    "number": round(stats['avg_utilization'], 1)
                },
                "Peak Utilization": {
                    "number": round(stats['peak_utilization'], 1)
                },
                "Avg Memory": {
                    "number": stats['avg_memory']
                },
                "Peak Memory": {
                    "number": stats['peak_memory']
                },
                "Status": {
                    "status": {
                        "name": status
                    }
                }
            }
            
            # Add end time if process has ended
            if stats['is_ended']:
                properties["End Time"] = {
                    "date": {
                        "start": stats['end_time']
                    }
                }
            
            # Create database entry
            url = "https://api.notion.com/v1/pages"
            data = {
                "parent": {"database_id": self.database_id},
                "properties": properties
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                print(f"  ✅ Logged process to Notion: GPU {gpu_id} - {username} - PID {pid}")
                self.logged_processes.add(process_key)
            else:
                print(f"  ⚠️  Failed to log process: {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ Error logging process to Notion: {e}")
    
    def get_process_stats(self, gpu_id: int, pid: int) -> Optional[Dict]:
        """Get process statistics from SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get process snapshots
            cursor.execute('''
                SELECT timestamp, memory_usage
                FROM process_snapshots
                WHERE gpu_id = ? AND pid = ?
                ORDER BY timestamp
            ''', (gpu_id, pid))
            
            process_snapshots = cursor.fetchall()
            if not process_snapshots:
                conn.close()
                return None
            
            start_time = process_snapshots[0][0]
            end_time = process_snapshots[-1][0]
            
            # Get GPU utilization during this time
            cursor.execute('''
                SELECT AVG(utilization), MAX(utilization)
                FROM gpu_snapshots
                WHERE gpu_id = ? 
                  AND timestamp >= ? 
                  AND timestamp <= ?
            ''', (gpu_id, start_time, end_time))
            
            util_stats = cursor.fetchone()
            avg_util = util_stats[0] if util_stats[0] else 0
            peak_util = util_stats[1] if util_stats[1] else 0
            
            # Memory stats
            memory_values = [row[1] for row in process_snapshots]
            avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
            peak_memory = max(memory_values) if memory_values else 0
            
            # Calculate duration
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            duration_minutes = (end_dt - start_dt).total_seconds() / 60
            
            # Check if process has ended (no snapshot in last 2 minutes)
            cursor.execute('''
                SELECT COUNT(*) FROM process_snapshots
                WHERE gpu_id = ? AND pid = ?
                  AND timestamp > datetime('now', '-2 minutes')
            ''', (gpu_id, pid))
            
            is_ended = cursor.fetchone()[0] == 0
            
            conn.close()
            
            return {
                'start_time': start_time,
                'end_time': end_time,
                'avg_utilization': avg_util,
                'peak_utilization': peak_util,
                'avg_memory': int(avg_memory),
                'peak_memory': int(peak_memory),
                'duration_minutes': duration_minutes,
                'is_ended': is_ended
            }
        
        except Exception as e:
            print(f"  ❌ Error getting process stats: {e}")
            return None
    
    def log_all_recent_processes(self):
        """Log all processes from the last hour to Notion"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get distinct processes from last hour
            cursor.execute('''
                SELECT DISTINCT gpu_id, pid, username
                FROM process_snapshots
                WHERE timestamp > datetime('now', '-1 hour')
            ''')
            
            processes = cursor.fetchall()
            conn.close()
            
            for gpu_id, pid, username in processes:
                self.log_process_session(gpu_id, pid, username)
        
        except Exception as e:
            print(f"❌ Error logging recent processes: {e}")


# Example usage (add to gpu_monitor.py)
def example_integration():
    """
    How to integrate into gpu_monitor.py
    """
    
    # In __init__:
    # self.process_logger = ProcessHistoryLogger(
    #     notion_token=self.notion_token,
    #     database_id=self.config['notion']['process_history_db_id'],
    #     db_path=self.db_path
    # )
    
    # In run() loop, after saving snapshots:
    # self.process_logger.log_all_recent_processes()
    
    pass
