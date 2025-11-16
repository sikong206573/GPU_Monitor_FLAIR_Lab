#!/usr/bin/env python3
"""
GPU Monitoring System - Main Script
Monitors GPU usage, updates Notion dashboard, sends email alerts
"""

import sqlite3
import subprocess
import time
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import argparse
import sys


class GPUMonitor:
    """Main GPU monitoring class"""
    
    def __init__(self, config_path: str):
        """Initialize monitor with configuration"""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.db_path = self.config['database']['path']
        self.update_interval = self.config['update_interval']
        self.gpus = self.config['gpus']
        
        # Notion configuration
        self.notion_token = self.config['notion']['token']
        self.notion_page_id = self.config['notion']['realtime_page_id']
        self.notion_headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Email configuration
        self.email_enabled = self.config['email']['enabled']
        if self.email_enabled:
            self.smtp_server = self.config['email']['smtp_server']
            self.smtp_port = self.config['email']['smtp_port']
            self.sender_email = self.config['email']['sender_email']
            self.sender_password = self.config['email']['sender_password']
            self.email_domain = self.config['email']['user_email_domain']
        
        # Alert configuration
        self.idle_threshold_minutes = self.config.get('idle_threshold_minutes', 10)
        self.idle_utilization_threshold = self.config.get('idle_utilization_threshold', 5)
        
        # Initialize database
        self.init_database()
        
        # Track alerted processes to avoid spam
        self.alerted_processes = set()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # GPU snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gpu_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                gpu_id INTEGER NOT NULL,
                utilization REAL,
                memory_used INTEGER,
                memory_total INTEGER,
                temperature REAL
            )
        ''')
        
        # Process snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                gpu_id INTEGER NOT NULL,
                pid INTEGER NOT NULL,
                username TEXT NOT NULL,
                memory_usage INTEGER
            )
        ''')
        
        # Email alerts log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                gpu_id INTEGER NOT NULL,
                pid INTEGER NOT NULL,
                username TEXT NOT NULL,
                alert_reason TEXT
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_gpu_snapshots_timestamp 
            ON gpu_snapshots(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_process_snapshots_timestamp 
            ON process_snapshots(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"✅ Database initialized: {self.db_path}")
    
    def get_gpu_info(self) -> List[Dict]:
        """Get current GPU information using nvidia-smi"""
        try:
            # Query GPU stats
            result = subprocess.run([
                'nvidia-smi',
                '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, check=True)
            
            gpu_data = []
            for line in result.stdout.strip().split('\n'):
                parts = [p.strip() for p in line.split(',')]
                gpu_data.append({
                    'index': int(parts[0]),
                    'name': parts[1],
                    'utilization': float(parts[2]),
                    'memory_used': int(parts[3]),
                    'memory_total': int(parts[4]),
                    'temperature': float(parts[5])
                })
            
            return gpu_data
        
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting GPU info: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return []
    
    def get_gpu_processes(self) -> List[Dict]:
        """Get current GPU processes"""
        try:
            result = subprocess.run([
                'nvidia-smi',
                '--query-compute-apps=gpu_bus_id,pid,used_memory',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, check=True)
            
            processes = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                pid = int(parts[1])
                
                # Get username from PID
                try:
                    ps_result = subprocess.run(
                        ['ps', '-o', 'user=', '-p', str(pid)],
                        capture_output=True, text=True, check=True
                    )
                    username = ps_result.stdout.strip()
                except:
                    username = 'unknown'
                
                # Get GPU index from bus ID
                gpu_index = self.get_gpu_index_from_bus(parts[0])
                
                processes.append({
                    'gpu_id': gpu_index,
                    'pid': pid,
                    'username': username,
                    'memory_usage': int(parts[2])
                })
            
            return processes
        
        except subprocess.CalledProcessError:
            return []
        except Exception as e:
            print(f"❌ Error getting GPU processes: {e}")
            return []
    
    def get_gpu_index_from_bus(self, bus_id: str) -> int:
        """Convert GPU bus ID to index"""
        try:
            result = subprocess.run([
                'nvidia-smi',
                '--query-gpu=index,gpu_bus_id',
                '--format=csv,noheader'
            ], capture_output=True, text=True, check=True)
            
            for line in result.stdout.strip().split('\n'):
                idx, bid = line.split(',')
                if bid.strip() == bus_id:
                    return int(idx.strip())
            
            return 0
        except:
            return 0
    
    def save_snapshot(self, gpu_data: List[Dict], processes: List[Dict]):
        """Save current snapshot to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        # Save GPU snapshots
        for gpu in gpu_data:
            cursor.execute('''
                INSERT INTO gpu_snapshots 
                (timestamp, gpu_id, utilization, memory_used, memory_total, temperature)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                gpu['index'],
                gpu['utilization'],
                gpu['memory_used'],
                gpu['memory_total'],
                gpu['temperature']
            ))
        
        # Save process snapshots
        for proc in processes:
            cursor.execute('''
                INSERT INTO process_snapshots
                (timestamp, gpu_id, pid, username, memory_usage)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                timestamp,
                proc['gpu_id'],
                proc['pid'],
                proc['username'],
                proc['memory_usage']
            ))
        
        conn.commit()
        conn.close()
    
    def check_idle_processes(self, gpu_data: List[Dict], processes: List[Dict]):
        """Check for idle processes and send alerts"""
        if not self.email_enabled:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get timestamp from X minutes ago
        check_time = (datetime.now() - timedelta(minutes=self.idle_threshold_minutes)).isoformat()
        
        for proc in processes:
            gpu_id = proc['gpu_id']
            pid = proc['pid']
            username = proc['username']
            
            # Skip if already alerted
            alert_key = f"{gpu_id}_{pid}"
            if alert_key in self.alerted_processes:
                continue
            
            # Get GPU utilization history for this GPU
            cursor.execute('''
                SELECT AVG(utilization) as avg_util
                FROM gpu_snapshots
                WHERE gpu_id = ? AND timestamp >= ?
            ''', (gpu_id, check_time))
            
            result = cursor.fetchone()
            if result and result[0] is not None:
                avg_utilization = result[0]
                
                # Check if process exists in this time window
                cursor.execute('''
                    SELECT COUNT(*) FROM process_snapshots
                    WHERE gpu_id = ? AND pid = ? AND timestamp >= ?
                ''', (gpu_id, pid, check_time))
                
                snapshot_count = cursor.fetchone()[0]
                
                # If utilization is low and process has been there the whole time
                if avg_utilization < self.idle_utilization_threshold and snapshot_count >= 3:
                    # Send alert
                    self.send_idle_alert(gpu_id, pid, username, avg_utilization)
                    self.alerted_processes.add(alert_key)
                    
                    # Log alert
                    cursor.execute('''
                        INSERT INTO email_alerts
                        (timestamp, gpu_id, pid, username, alert_reason)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        gpu_id,
                        pid,
                        username,
                        f"Low utilization: {avg_utilization:.1f}%"
                    ))
        
        conn.commit()
        conn.close()
    
    def send_idle_alert(self, gpu_id: int, pid: int, username: str, avg_util: float):
        """Send email alert for idle process"""
        try:
            recipient_email = f"{username}@{self.email_domain}"
            
            subject = f"GPU Monitor: Idle Process Alert - GPU {gpu_id}"
            
            body = f"""
Hi {username},

Just a friendly reminder from the GPU Monitor system.

Your process (PID {pid}) on GPU {gpu_id} has been using GPU memory but showing low utilization (<{self.idle_utilization_threshold}%) for the past {self.idle_threshold_minutes} minutes.

Average utilization: {avg_util:.1f}%

When you get a chance, you might want to check if:
- The job completed but didn't exit cleanly
- The process is stuck or waiting for input
- You're between training runs

If this process is intentional (e.g., holding memory for next run), no action needed!

To free up the GPU for others:
  kill {pid}

Questions? Feel free to reach out.

Best regards,
GPU Monitor Bot 🤖

---
This is an automated message. The monitor checks every {self.update_interval} seconds.
            """.strip()
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            print(f"📧 Alert sent to {recipient_email} for PID {pid} on GPU {gpu_id}")
        
        except Exception as e:
            print(f"❌ Failed to send email alert: {e}")
    
    def update_notion_dashboard(self, gpu_data: List[Dict], processes: List[Dict]):
        """Update Notion page with current GPU status using in-place updates"""
        try:
            # Get existing blocks
            url = f"https://api.notion.com/v1/blocks/{self.notion_page_id}/children"
            response = requests.get(url, headers=self.notion_headers)
            
            if response.status_code != 200:
                print(f"⚠️  Could not fetch existing blocks, creating new structure")
                self._create_initial_dashboard_structure(gpu_data, processes)
                return
            
            existing_blocks = response.json().get('results', [])
            
            # If page is empty, create initial structure
            if len(existing_blocks) == 0:
                self._create_initial_dashboard_structure(gpu_data, processes)
                return
            
            # Find and update each GPU's code block (in-place update)
            # We look for code blocks and update their content
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # First, update the header timestamp
            header_updated = False
            for block in existing_blocks:
                if block['type'] == 'heading_2':
                    current_text = block['heading_2']['rich_text'][0]['text']['content'] if block['heading_2']['rich_text'] else ''
                    if 'GPU Monitor Status' in current_text:
                        # Update the header
                        block_id = block['id']
                        update_url = f"https://api.notion.com/v1/blocks/{block_id}"
                        update_data = {
                            "heading_2": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": f"🖥️ GPU Monitor Status - Updated: {timestamp}"}
                                }]
                            }
                        }
                        update_response = requests.patch(update_url, headers=self.notion_headers, json=update_data)
                        if update_response.status_code == 200:
                            header_updated = True
                        break

            
            for gpu in gpu_data:
                gpu_id = gpu['index']
                
                # Create updated content for this GPU
                memory_pct = (gpu['memory_used'] / gpu['memory_total'] * 100)
                gpu_content = f"""GPU {gpu_id}: {gpu['name']} | Last Updated: {timestamp}
─────────────────────────────────────────
Utilization: {gpu['utilization']:.1f}%
Memory: {gpu['memory_used']} MB / {gpu['memory_total']} MB ({memory_pct:.1f}%)
Temperature: {gpu['temperature']}°C

Running Processes:"""
                
                # Get processes for this GPU
                gpu_processes = [p for p in processes if p['gpu_id'] == gpu_id]
                if gpu_processes:
                    for proc in gpu_processes:
                        gpu_content += f"\n  • PID {proc['pid']} - {proc['username']} - {proc['memory_usage']} MB"
                else:
                    gpu_content += "\n  ✅ No active processes"
                
                # Find the code block for this GPU and update it
                # Code blocks are identified by looking for ones containing "GPU {gpu_id}:"
                block_updated = False
                for block in existing_blocks:
                    if block['type'] == 'code':
                        # Check if this is the block for current GPU
                        current_text = block['code']['rich_text'][0]['text']['content'] if block['code']['rich_text'] else ''
                        if f"GPU {gpu_id}:" in current_text:
                            # Update this block in-place
                            block_id = block['id']
                            update_url = f"https://api.notion.com/v1/blocks/{block_id}"
                            update_data = {
                                "code": {
                                    "rich_text": [{
                                        "type": "text",
                                        "text": {"content": gpu_content}
                                    }],
                                    "language": "plain text"
                                }
                            }
                            update_response = requests.patch(update_url, headers=self.notion_headers, json=update_data)
                            if update_response.status_code == 200:
                                block_updated = True
                            break
                
                if not block_updated:
                    print(f"⚠️  Could not find block for GPU {gpu_id}, recreating structure")
                    self._create_initial_dashboard_structure(gpu_data, processes)
                    return
            
            # Update timestamp in the first heading
            if existing_blocks and existing_blocks[0]['type'] == 'heading_2':
                heading_block_id = existing_blocks[0]['id']
                update_url = f"https://api.notion.com/v1/blocks/{heading_block_id}"
                update_data = {
                    "heading_2": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": f"🖥️ GPU Monitor Status - Updated: {timestamp}"}
                        }]
                    }
                }
                requests.patch(update_url, headers=self.notion_headers, json=update_data)
            
            print(f"✅ Notion dashboard updated successfully (in-place)")
        
        except Exception as e:
            print(f"❌ Error updating Notion dashboard: {e}")
    
    def _create_initial_dashboard_structure(self, gpu_data: List[Dict], processes: List[Dict]):
        """Create initial dashboard structure (only called once or when structure is broken)"""
        try:
            # Check existing blocks but IGNORE child pages
            url = f"https://api.notion.com/v1/blocks/{self.notion_page_id}/children"
            response = requests.get(url, headers=self.notion_headers)
            
            if response.status_code == 200:
                existing_blocks = response.json().get('results', [])
                
                # Filter out child pages - we only care about content blocks
                content_blocks = [b for b in existing_blocks 
                                 if b['type'] not in ['child_page', 'child_database']]
                
                # If there are content blocks (not just child pages), clear them
                if content_blocks:
                    print("⚠️  Clearing old content blocks (preserving child pages)...")
                    self.clear_notion_page()
            
            # Create structure (child pages will remain untouched)
            blocks = []
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # First, update the header timestamp
            header_updated = False
            for block in existing_blocks:
                if block['type'] == 'heading_2':
                    current_text = block['heading_2']['rich_text'][0]['text']['content'] if block['heading_2']['rich_text'] else ''
                    if 'GPU Monitor Status' in current_text:
                        # Update the header
                        block_id = block['id']
                        update_url = f"https://api.notion.com/v1/blocks/{block_id}"
                        update_data = {
                            "heading_2": {
                                "rich_text": [{
                                    "type": "text",
                                    "text": {"content": f"🖥️ GPU Monitor Status - Updated: {timestamp}"}
                                }]
                            }
                        }
                        update_response = requests.patch(update_url, headers=self.notion_headers, json=update_data)
                        if update_response.status_code == 200:
                            header_updated = True
                        break

            
            # Title with timestamp
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"🖥️ GPU Monitor Status - Updated: {timestamp}"}
                    }]
                }
            })
            
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # Create a code block for each GPU
            for gpu in gpu_data:
                gpu_id = gpu['index']
                memory_pct = (gpu['memory_used'] / gpu['memory_total'] * 100)
                
                gpu_content = f"""GPU {gpu_id}: {gpu['name']}
─────────────────────────────────────────
Utilization: {gpu['utilization']:.1f}%
Memory: {gpu['memory_used']} MB / {gpu['memory_total']} MB ({memory_pct:.1f}%)
Temperature: {gpu['temperature']}°C

Running Processes:"""
                
                gpu_processes = [p for p in processes if p['gpu_id'] == gpu_id]
                if gpu_processes:
                    for proc in gpu_processes:
                        gpu_content += f"\n  • PID {proc['pid']} - {proc['username']} - {proc['memory_usage']} MB"
                else:
                    gpu_content += "\n  ✅ No active processes"
                
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": gpu_content}
                        }],
                        "language": "plain text"
                    }
                })
            
            # Add all blocks at once
            url = f"https://api.notion.com/v1/blocks/{self.notion_page_id}/children"
            response = requests.patch(url, headers=self.notion_headers, json={"children": blocks})
            
            if response.status_code == 200:
                print(f"✅ Initial dashboard structure created (child pages preserved)")
            else:
                print(f"❌ Failed to create initial structure: {response.status_code}")
                print(f"   Response: {response.text}")
        
        except Exception as e:
            print(f"❌ Error creating initial structure: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_notion_page(self):
        """Clear all blocks from Notion page EXCEPT child pages"""
        try:
            # Get all children blocks
            url = f"https://api.notion.com/v1/blocks/{self.notion_page_id}/children"
            response = requests.get(url, headers=self.notion_headers)
            
            if response.status_code == 200:
                blocks = response.json().get('results', [])
                
                # Delete each block EXCEPT child_page and child_database types
                for block in blocks:
                    block_type = block.get('type')
                    
                    # Skip child pages and databases - we want to keep these!
                    if block_type in ['child_page', 'child_database']:
                        print(f"⏭️  Skipping child page: {block.get('id')} (preserving sub-pages)")
                        continue
                    
                    # Delete other blocks (headings, paragraphs, code blocks, etc.)
                    delete_url = f"https://api.notion.com/v1/blocks/{block['id']}"
                    requests.delete(delete_url, headers=self.notion_headers)
        
        except Exception as e:
            print(f"⚠️  Warning: Could not clear Notion page: {e}")
    
    def cleanup_old_data(self, days_to_keep: int = 7):
        """Remove data older than specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        cursor.execute('DELETE FROM gpu_snapshots WHERE timestamp < ?', (cutoff_date,))
        cursor.execute('DELETE FROM process_snapshots WHERE timestamp < ?', (cutoff_date,))
        
        deleted_gpu = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_gpu > 0:
            print(f"🧹 Cleaned up {deleted_gpu} old records")
    
    def run(self):
        """Main monitoring loop"""
        print("🚀 GPU Monitor starting...")
        print(f"📊 Monitoring {len(self.gpus)} GPUs")
        print(f"⏱️  Update interval: {self.update_interval} seconds")
        print(f"📝 Database: {self.db_path}")
        print(f"📧 Email alerts: {'Enabled' if self.email_enabled else 'Disabled'}")
        print("\nPress Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Iteration {iteration}")
                
                # Get current GPU state
                gpu_data = self.get_gpu_info()
                processes = self.get_gpu_processes()
                
                if gpu_data:
                    # Save to database
                    self.save_snapshot(gpu_data, processes)
                    
                    # Update Notion dashboard
                    self.update_notion_dashboard(gpu_data, processes)
                    
                    # Check for idle processes
                    self.check_idle_processes(gpu_data, processes)
                    
                    # Clean up old data periodically (once per hour)
                    if iteration % (3600 // self.update_interval) == 0:
                        self.cleanup_old_data()
                else:
                    print("⚠️  No GPU data available")
                
                # Wait for next iteration
                time.sleep(self.update_interval)
        
        except KeyboardInterrupt:
            print("\n\n👋 GPU Monitor stopped by user")
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='GPU Monitoring System')
    parser.add_argument('-c', '--config', required=True, help='Path to configuration file')
    
    args = parser.parse_args()
    
    if not args.config:
        print("❌ Configuration file required. Use: -c config.json")
        sys.exit(1)
    
    monitor = GPUMonitor(args.config)
    monitor.run()


if __name__ == '__main__':
    main()
