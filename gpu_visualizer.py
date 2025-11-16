#!/usr/bin/env python3
"""
GPU Visualization System
Generates usage history charts and uploads to Notion via Imgur
"""

import sqlite3
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json
import os
import base64
import requests
from typing import List, Dict, Tuple
import argparse


class GPUVisualizer:
    """GPU data visualization and chart generation"""
    
    def __init__(self, config_path: str):
        """Initialize visualizer with configuration"""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.db_path = self.config['database']['path']
        self.output_dir = self.config.get('chart_output_dir', './charts')
        
        # Chart settings
        self.chart_dpi = self.config.get('chart_dpi', 150)
        self.chart_figsize = tuple(self.config.get('chart_figsize', [14, 6]))
        
        # User colors for visualization
        self.user_colors = {}
        self.color_palette = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', 
            '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
            '#F8B195', '#C06C84', '#6C5B7B', '#355C7D'
        ]
        
        # Create output directories
        os.makedirs(f"{self.output_dir}/daily", exist_ok=True)
        os.makedirs(f"{self.output_dir}/weekly", exist_ok=True)
        
        print(f"✅ Visualizer initialized")
        print(f"📊 Output directory: {self.output_dir}")
    
    def get_user_color(self, username: str) -> str:
        """Get consistent color for a user"""
        if username not in self.user_colors:
            color_idx = len(self.user_colors) % len(self.color_palette)
            self.user_colors[username] = self.color_palette[color_idx]
        return self.user_colors[username]
    
    def fetch_daily_data(self, gpu_id: int) -> Tuple[List, List, List, List]:
        """Fetch today's data for a specific GPU"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get today's date range
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now()
        
        # Fetch GPU utilization and memory data
        cursor.execute('''
            SELECT timestamp, utilization, memory_used, memory_total
            FROM gpu_snapshots
            WHERE gpu_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        ''', (gpu_id, today_start.isoformat(), today_end.isoformat()))
        
        gpu_data = cursor.fetchall()
        
        # Fetch process data for user identification
        cursor.execute('''
            SELECT timestamp, username, memory_usage
            FROM process_snapshots
            WHERE gpu_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        ''', (gpu_id, today_start.isoformat(), today_end.isoformat()))
        
        process_data = cursor.fetchall()
        
        conn.close()
        
        return gpu_data, process_data, today_start, today_end
    
    def fetch_weekly_data(self, gpu_id: int) -> Tuple[List, List, List, List]:
        """Fetch past 7 days data for a specific GPU"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get 7-day date range
        week_start = datetime.now() - timedelta(days=7)
        week_end = datetime.now()
        
        # Fetch GPU data
        cursor.execute('''
            SELECT timestamp, utilization, memory_used, memory_total
            FROM gpu_snapshots
            WHERE gpu_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        ''', (gpu_id, week_start.isoformat(), week_end.isoformat()))
        
        gpu_data = cursor.fetchall()
        
        # Fetch process data
        cursor.execute('''
            SELECT timestamp, username, memory_usage
            FROM process_snapshots
            WHERE gpu_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
        ''', (gpu_id, week_start.isoformat(), week_end.isoformat()))
        
        process_data = cursor.fetchall()
        
        conn.close()
        
        return gpu_data, process_data, week_start, week_end
    
    def create_utilization_chart(self, gpu_id: int, gpu_data: List, process_data: List, 
                                 start_time, end_time, period: str = 'daily'):
        """Create GPU utilization chart with user color coding"""
        if not gpu_data:
            print(f"⚠️  No data available for GPU {gpu_id} ({period})")
            return None
        
        fig, ax = plt.subplots(figsize=self.chart_figsize)
        
        # Parse GPU data
        timestamps = [datetime.fromisoformat(row[0]) for row in gpu_data]
        utilizations = [row[1] for row in gpu_data]
        
        # Plot utilization line
        ax.plot(timestamps, utilizations, color='#2E86AB', linewidth=2, label='GPU Utilization')
        ax.fill_between(timestamps, utilizations, alpha=0.3, color='#2E86AB')
        
        # Add user color coding in background
        if process_data:
            # Group process data by timestamp
            process_by_time = {}
            for row in process_data:
                ts = datetime.fromisoformat(row[0])
                username = row[1]
                if ts not in process_by_time:
                    process_by_time[ts] = []
                process_by_time[ts].append(username)
            
            # Create colored background segments
            current_users = set()
            segment_start = None
            
            for i, ts in enumerate(timestamps):
                # Get users at this timestamp
                users_at_time = set(process_by_time.get(ts, []))
                
                # If users changed, draw previous segment
                if users_at_time != current_users:
                    if segment_start is not None and current_users:
                        # Draw segment with blended color
                        user_list = list(current_users)
                        color = self.get_user_color(user_list[0])
                        ax.axvspan(segment_start, ts, alpha=0.15, color=color)
                        
                        # Add label in the middle of segment
                        if i > 0:
                            mid_point = segment_start + (ts - segment_start) / 2
                            label_text = ', '.join(sorted(user_list))
                            ax.text(mid_point, ax.get_ylim()[1] * 0.95, label_text,
                                   ha='center', va='top', fontsize=8, 
                                   bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
                    
                    segment_start = ts
                    current_users = users_at_time
            
            # Draw final segment
            if segment_start is not None and current_users:
                user_list = list(current_users)
                color = self.get_user_color(user_list[0])
                ax.axvspan(segment_start, timestamps[-1], alpha=0.15, color=color)
                mid_point = segment_start + (timestamps[-1] - segment_start) / 2
                label_text = ', '.join(sorted(user_list))
                ax.text(mid_point, ax.get_ylim()[1] * 0.95, label_text,
                       ha='center', va='top', fontsize=8,
                       bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
        
        # Formatting
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Utilization (%)', fontsize=12)
        ax.set_title(f'GPU {gpu_id} - Utilization ({period.capitalize()})', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis based on period
        if period == 'daily':
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        else:  # weekly
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator())
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save figure
        filename = f"{self.output_dir}/{period}/gpu_{gpu_id}_utilization_{period}.png"
        plt.savefig(filename, dpi=self.chart_dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Created {period} utilization chart: {filename}")
        return filename
    
    def create_memory_chart(self, gpu_id: int, gpu_data: List, process_data: List,
                           start_time, end_time, period: str = 'daily'):
        """Create GPU memory usage chart with user color coding"""
        if not gpu_data:
            return None
        
        fig, ax = plt.subplots(figsize=self.chart_figsize)
        
        # Parse GPU data
        timestamps = [datetime.fromisoformat(row[0]) for row in gpu_data]
        memory_used = [row[2] for row in gpu_data]
        memory_total = gpu_data[0][3] if gpu_data else 1
        memory_pct = [(mem / memory_total * 100) for mem in memory_used]
        
        # Plot memory line
        ax.plot(timestamps, memory_pct, color='#A23B72', linewidth=2, label='Memory Usage')
        ax.fill_between(timestamps, memory_pct, alpha=0.3, color='#A23B72')
        
        # Add user color coding (same logic as utilization chart)
        if process_data:
            process_by_time = {}
            for row in process_data:
                ts = datetime.fromisoformat(row[0])
                username = row[1]
                if ts not in process_by_time:
                    process_by_time[ts] = []
                process_by_time[ts].append(username)
            
            current_users = set()
            segment_start = None
            
            for i, ts in enumerate(timestamps):
                users_at_time = set(process_by_time.get(ts, []))
                
                if users_at_time != current_users:
                    if segment_start is not None and current_users:
                        user_list = list(current_users)
                        color = self.get_user_color(user_list[0])
                        ax.axvspan(segment_start, ts, alpha=0.15, color=color)
                        
                        mid_point = segment_start + (ts - segment_start) / 2
                        label_text = ', '.join(sorted(user_list))
                        ax.text(mid_point, ax.get_ylim()[1] * 0.95, label_text,
                               ha='center', va='top', fontsize=8,
                               bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
                    
                    segment_start = ts
                    current_users = users_at_time
            
            if segment_start is not None and current_users:
                user_list = list(current_users)
                color = self.get_user_color(user_list[0])
                ax.axvspan(segment_start, timestamps[-1], alpha=0.15, color=color)
                mid_point = segment_start + (timestamps[-1] - segment_start) / 2
                label_text = ', '.join(sorted(user_list))
                ax.text(mid_point, ax.get_ylim()[1] * 0.95, label_text,
                       ha='center', va='top', fontsize=8,
                       bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
        
        # Formatting
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Memory Usage (%)', fontsize=12)
        ax.set_title(f'GPU {gpu_id} - Memory Usage ({period.capitalize()})', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        if period == 'daily':
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator())
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save figure
        filename = f"{self.output_dir}/{period}/gpu_{gpu_id}_memory_{period}.png"
        plt.savefig(filename, dpi=self.chart_dpi, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Created {period} memory chart: {filename}")
        return filename
    
    def generate_daily_charts(self) -> List[str]:
        """Generate daily charts for all GPUs"""
        print("\n📊 Generating daily charts...")
        chart_files = []
        
        gpus = self.config['gpus']
        for gpu in gpus:
            gpu_id = gpu['id']
            
            gpu_data, process_data, start, end = self.fetch_daily_data(gpu_id)
            
            if gpu_data:
                # Create utilization chart
                util_file = self.create_utilization_chart(gpu_id, gpu_data, process_data, start, end, 'daily')
                if util_file:
                    chart_files.append(util_file)
                
                # Create memory chart
                mem_file = self.create_memory_chart(gpu_id, gpu_data, process_data, start, end, 'daily')
                if mem_file:
                    chart_files.append(mem_file)
        
        print(f"✅ Generated {len(chart_files)} daily charts")
        return chart_files
    
    def generate_weekly_charts(self) -> List[str]:
        """Generate weekly charts for all GPUs"""
        print("\n📊 Generating weekly charts...")
        chart_files = []
        
        gpus = self.config['gpus']
        for gpu in gpus:
            gpu_id = gpu['id']
            
            gpu_data, process_data, start, end = self.fetch_weekly_data(gpu_id)
            
            if gpu_data:
                # Create utilization chart
                util_file = self.create_utilization_chart(gpu_id, gpu_data, process_data, start, end, 'weekly')
                if util_file:
                    chart_files.append(util_file)
                
                # Create memory chart
                mem_file = self.create_memory_chart(gpu_id, gpu_data, process_data, start, end, 'weekly')
                if mem_file:
                    chart_files.append(mem_file)
        
        print(f"✅ Generated {len(chart_files)} weekly charts")
        return chart_files


class S3Uploader:
    """Upload images to AWS S3"""
    
    def __init__(self, bucket: str, region: str = 'us-east-1', 
                 access_key: str = None, secret_key: str = None):
        """
        Initialize S3 uploader
        
        Args:
            bucket: S3 bucket name
            region: AWS region
            access_key: AWS access key (optional, uses boto3 config if not provided)
            secret_key: AWS secret key (optional, uses boto3 config if not provided)
        """
        try:
            import boto3
            
            if access_key and secret_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region
                )
            else:
                # Use default credentials from ~/.aws/credentials or environment
                self.s3_client = boto3.client('s3', region_name=region)
            
            self.bucket = bucket
            self.region = region
            print(f"✅ S3 uploader initialized (bucket: {bucket}, region: {region})")
        
        except ImportError:
            print("❌ boto3 not installed. Install with: pip3 install --user boto3")
            raise
        except Exception as e:
            print(f"❌ Error initializing S3 client: {e}")
            raise
    
    def upload_image(self, image_path: str) -> str:
        """Upload image to S3 and return public URL"""
        try:
            # Generate S3 key with timestamp for uniqueness
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.basename(image_path)
            s3_key = f"gpu-charts/{timestamp}_{filename}"
            
            # Upload file
            self.s3_client.upload_file(
                image_path,
                self.bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/png',
                    'ACL': 'public-read'
                }
            )
            
            # Generate public URL
            url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            print(f"  ✅ Uploaded: {filename} → {url}")
            return url
        
        except Exception as e:
            print(f"  ❌ Error uploading {image_path}: {e}")
            return None


class NotionChartUpdater:
    """Update Notion pages with charts"""
    
    def __init__(self, notion_token: str):
        self.token = notion_token
        self.headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def clear_page(self, page_id: str):
        """Clear all content from a Notion page"""
        try:
            url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                blocks = response.json().get('results', [])
                for block in blocks:
                    delete_url = f"https://api.notion.com/v1/blocks/{block['id']}"
                    requests.delete(delete_url, headers=self.headers)
        except Exception as e:
            print(f"⚠️  Warning: Could not clear page: {e}")
    
    def update_chart_page(self, page_id: str, chart_urls: Dict[str, str], title: str):
        """Update Notion page with chart images (appends new charts, keeps history)"""
        try:
            # Don't clear the page - we want to keep historical charts!
            # Instead, append new charts with timestamp
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Build new content to append
            blocks = []
            
            # Add timestamp header for this update
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": f"📊 {title} - {timestamp}"}
                    }]
                }
            })
            
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # Add each chart
            for filename, url in chart_urls.items():
                if url:
                    # Chart name as heading
                    chart_name = os.path.basename(filename).replace('_', ' ').replace('.png', '').title()
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": chart_name}
                            }]
                        }
                    })
                    
                    # Image block
                    blocks.append({
                        "object": "block",
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external": {"url": url}
                        }
                    })
                    
                    # Spacer
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": ""}
                            }]
                        }
                    })
            
            # Separator between updates
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # Append blocks to the page (don't replace, just add)
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i:i+batch_size]
                url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                response = requests.patch(url, headers=self.headers, json={"children": batch})
                
                if response.status_code != 200:
                    print(f"❌ Failed to append to Notion page: {response.text}")
                    return False
            
            print(f"✅ Charts appended to Notion page (history preserved)")
            return True
        
        except Exception as e:
            print(f"❌ Error updating Notion page: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='GPU Visualization System')
    parser.add_argument('-c', '--config', required=True, help='Path to configuration file')
    parser.add_argument('--period', choices=['daily', 'weekly', 'both'], default='both',
                       help='Which charts to generate')
    parser.add_argument('--no-upload', action='store_true', help='Generate charts but do not upload')
    
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = json.load(f)
    
    # Initialize visualizer
    visualizer = GPUVisualizer(args.config)
    
    # Generate charts
    daily_files = []
    weekly_files = []
    
    if args.period in ['daily', 'both']:
        daily_files = visualizer.generate_daily_charts()
    
    if args.period in ['weekly', 'both']:
        weekly_files = visualizer.generate_weekly_charts()
    
    # Upload to Notion via S3
    if not args.no_upload:
        s3_enabled = config.get('aws_s3', {}).get('enabled', False)
        notion_enabled = config.get('notion', {}).get('enabled', True)
        
        if not s3_enabled:
            print("\n⚠️  AWS S3 not configured. Charts generated but not uploaded.")
            print("To enable uploads, configure aws_s3 section in config.json")
            return
        
        if not notion_enabled:
            print("\n⚠️  Notion not configured. Charts generated but not uploaded.")
            return
        
        print("\n📤 Uploading charts to S3...")
        
        s3_config = config['aws_s3']
        uploader = S3Uploader(
            bucket=s3_config['bucket'],
            region=s3_config.get('region', 'us-east-1'),
            access_key=s3_config.get('access_key'),
            secret_key=s3_config.get('secret_key')
        )
        
        # Upload daily charts
        daily_urls = {}
        for file_path in daily_files:
            url = uploader.upload_image(file_path)
            if url:
                daily_urls[file_path] = url
        
        # Upload weekly charts
        weekly_urls = {}
        for file_path in weekly_files:
            url = uploader.upload_image(file_path)
            if url:
                weekly_urls[file_path] = url
        
        # Update Notion pages
        print("\n📝 Updating Notion pages...")
        
        notion_token = config['notion']['token']
        notion_updater = NotionChartUpdater(notion_token)
        
        if daily_urls and 'daily_chart_page_id' in config['notion']:
            notion_updater.update_chart_page(
                config['notion']['daily_chart_page_id'],
                daily_urls,
                "GPU Daily Usage Charts"
            )
        
        if weekly_urls and 'weekly_chart_page_id' in config['notion']:
            notion_updater.update_chart_page(
                config['notion']['weekly_chart_page_id'],
                weekly_urls,
                "GPU Weekly Usage Charts"
            )
    
    print("\n✅ Visualization complete!")


if __name__ == '__main__':
    main()
