# GPU Monitoring System - Setup Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies

```bash
# Install required Python packages
pip3 install --user requests matplotlib

# Verify nvidia-smi is available
nvidia-smi
```

### Step 2: Get Imgur Client ID (2 minutes)

Imgur provides free image hosting for your charts.

1. Go to https://api.imgur.com/oauth2/addclient
2. Fill in the form:
   - **Application name**: GPU Monitor
   - **Authorization type**: Select "OAuth 2 authorization without a callback URL"
   - **Email**: Your email
   - **Description**: GPU monitoring charts
3. Click "Submit"
4. **Copy the Client ID** (it will look like: `abc123def456`)

### Step 3: Get Notion Credentials (3 minutes)

#### 3a. Create Integration
1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Name it "GPU Monitor"
4. Select your workspace
5. Click "Submit"
6. **Copy the "Internal Integration Token"** (starts with `secret_`)

#### 3b. Create Notion Pages
Create **3 pages** in Notion:
- "GPU Real-time Monitor" (for live status updates)
- "GPU Daily Charts" (for today's usage charts)
- "GPU Weekly Charts" (for 7-day usage charts)

#### 3c. Get Page IDs
For each page:
1. Open the page in Notion
2. Click "Share" button (top right)
3. Click "Copy link"
4. Extract the Page ID from URL:
   ```
   https://www.notion.so/My-Page-abc123def456...
                                  ↑
                            This is the Page ID
   ```

#### 3d. Connect Integration to Pages
For each of the 3 pages:
1. Click the "..." menu (top right)
2. Go to "Connections"
3. Click "+ Add connections"
4. Select "GPU Monitor"

### Step 4: Configure Email (Gmail Example)

#### For Gmail:
1. Go to https://myaccount.google.com/apppasswords
2. Sign in to your Google account
3. Create an app password:
   - App: "Mail"
   - Device: "Other" → Type "GPU Monitor"
4. Click "Generate"
5. **Copy the 16-character password**

#### For Other Email Providers:
**Outlook/Hotmail:**
```json
"smtp_server": "smtp-mail.outlook.com",
"smtp_port": 587
```

**TAMU Email:**
```json
"smtp_server": "smtp.tamu.edu",
"smtp_port": 587
```

**Yahoo Mail:**
```json
"smtp_server": "smtp.mail.yahoo.com",
"smtp_port": 587
```

### Step 5: Edit Configuration File

Open `config.json` and fill in your credentials:

```json
{
  "notion": {
    "enabled": true,
    "token": "secret_abc123...",           ← Notion integration token
    "realtime_page_id": "abc123...",       ← Real-time monitor page ID
    "daily_chart_page_id": "def456...",    ← Daily charts page ID
    "weekly_chart_page_id": "ghi789..."    ← Weekly charts page ID
  },
  
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your.email@gmail.com",
    "sender_password": "abcd efgh ijkl mnop",  ← Gmail app password
    "user_email_domain": "tamu.edu"            ← User email domain
  },
  
  "imgur": {
    "enabled": true,
    "client_id": "abc123def456"           ← Imgur client ID
  }
}
```

### Step 6: Test the System

```bash
# Test monitoring (run once to verify it works)
python3 gpu_monitor.py -c config.json

# You should see:
# ✅ Database initialized
# 🚀 GPU Monitor starting...
# ✅ Notion dashboard updated successfully

# Press Ctrl+C to stop
```

### Step 7: Run in Background

```bash
# Run monitoring in background
nohup python3 gpu_monitor.py -c config.json > monitor.log 2>&1 &

# Check if it's running
ps aux | grep gpu_monitor

# View logs
tail -f monitor.log
```

---

## 📊 Generating Charts

### Manual Chart Generation

```bash
# Generate daily charts
python3 gpu_visualizer.py -c config.json --period daily

# Generate weekly charts
python3 gpu_visualizer.py -c config.json --period weekly

# Generate both
python3 gpu_visualizer.py -c config.json --period both

# Generate without uploading (for testing)
python3 gpu_visualizer.py -c config.json --no-upload
```

### Automated Chart Generation

Add to crontab for automatic daily updates:

```bash
# Edit crontab
crontab -e

# Add these lines:
# Generate daily charts every day at 1 AM
0 1 * * * cd /path/to/gpu-monitor && python3 gpu_visualizer.py -c config.json --period daily

# Generate weekly charts every Monday at 2 AM
0 2 * * 1 cd /path/to/gpu-monitor && python3 gpu_visualizer.py -c config.json --period weekly

# Or generate both daily at 1 AM
0 1 * * * cd /path/to/gpu-monitor && python3 gpu_visualizer.py -c config.json --period both
```

---

## 🎨 What You'll See

### Real-time Notion Page (Updates every 30 seconds)
```
🖥️ GPU Monitor Status - Updated: 2025-11-12 14:30:15
═══════════════════════════════════════════════

🎮 GPU 0: NVIDIA H100 NVL
Utilization: 85.5%
Memory: 45000 MB / 95830 MB (47.0%)
Temperature: 65°C

Running Processes:
  • PID 12345 - alex - 12000 MB
  • PID 67890 - sarah - 8000 MB
```

### Daily Charts Page
- Line charts showing utilization and memory over 24 hours
- Color-coded background showing which user was using GPU
- User names labeled on chart

### Weekly Charts Page
- Same format, but 7-day view
- Great for identifying usage patterns

---

## 📧 Email Alerts

When a process is idle (using memory but <5% GPU for 10+ minutes), the user receives:

```
Subject: GPU Monitor: Idle Process Alert - GPU 2

Hi alex,

Just a friendly reminder from the GPU Monitor system.

Your process (PID 12345) on GPU 2 has been using GPU memory 
but showing low utilization (<5%) for the past 10 minutes.

Average utilization: 2.3%

When you get a chance, you might want to check if:
- The job completed but didn't exit cleanly
- The process is stuck or waiting for input
- You're between training runs

To free up the GPU:
  kill 12345

Questions? Feel free to reach out.

Best regards,
GPU Monitor Bot 🤖
```

---

## 🔧 Customization

### Change Update Frequency
In `config.json`:
```json
"update_interval": 60  // Check every 60 seconds instead of 30
```

### Change Alert Thresholds
```json
"idle_threshold_minutes": 15,        // Alert after 15 minutes
"idle_utilization_threshold": 10     // Idle if under 10%
```

### Disable Email Alerts
```json
"email": {
  "enabled": false
}
```

### Change Chart Resolution
```json
"chart_dpi": 200,           // Higher = better quality (larger files)
"chart_figsize": [16, 8]    // Wider charts
```

---

## 🛠️ Troubleshooting

### Problem: "nvidia-smi: command not found"
**Solution**: NVIDIA drivers not installed or not in PATH.
```bash
# Check if drivers are installed
lspci | grep -i nvidia

# Add to PATH if needed
export PATH=/usr/local/cuda/bin:$PATH
```

### Problem: "Notion API returns 401"
**Solution**: Token is incorrect or page not connected to integration.
- Double-check token in config.json
- Make sure you connected the integration to ALL 3 pages

### Problem: "Charts generate but don't show in Notion"
**Solution**: Imgur not configured properly.
- Verify Imgur client_id is correct
- Check if images uploaded successfully (look for "✅ Uploaded" messages)
- Try generating with `--no-upload` to see if charts create correctly

### Problem: "Email not sending"
**Solution**: 
- For Gmail: Use App Password, not regular password
- Check SMTP settings match your provider
- Verify port (usually 587 or 465)
- Check firewall isn't blocking SMTP

### Problem: "ModuleNotFoundError: No module named 'matplotlib'"
**Solution**:
```bash
pip3 install --user matplotlib requests
```

### Problem: "Database is locked"
**Solution**: Another process is using the database.
```bash
# Find and stop the other process
ps aux | grep gpu_monitor
kill <PID>
```

---

## 📁 File Structure

```
gpu-monitor/
├── config.json              # Configuration file
├── gpu_monitor.py           # Main monitoring script
├── gpu_visualizer.py        # Chart generation script
├── gpu_monitor.db           # SQLite database (created automatically)
├── charts/                  # Generated charts
│   ├── daily/
│   └── weekly/
└── monitor.log              # Log file (if using nohup)
```

---

## 🎯 Usage Patterns

### Lab Manager Workflow
```bash
# Morning: Check overnight usage
# Just open the Notion real-time page

# Weekly: Review usage patterns
# Open weekly charts page

# Monthly: Clean old data (optional)
sqlite3 gpu_monitor.db "DELETE FROM gpu_snapshots WHERE timestamp < date('now', '-30 days')"
```

### User Workflow
```bash
# Check if GPUs available
# Open Notion real-time page or run:
nvidia-smi

# If you get an idle process alert
# Check if your job is done:
ps aux | grep <PID>

# Kill if no longer needed:
kill <PID>
```

---

## 📊 Data Retention

By default, the system automatically deletes data older than 7 days.

To change retention:
```python
# In gpu_monitor.py, find cleanup_old_data() call
self.cleanup_old_data(days_to_keep=30)  # Keep 30 days
```

---

## 🚀 Next Steps

Once everything is working:

1. **Set up automatic chart generation** (crontab)
2. **Share Notion pages** with lab members
3. **Monitor email alerts** to see if they're effective
4. **Adjust thresholds** based on your lab's usage patterns

---

## 💡 Tips

- **Start conservative with alerts**: Begin with 15-minute threshold, lower if needed
- **Test emails first**: Send yourself a test alert before going live
- **Bookmark Notion pages**: Easy access for lab members
- **Check logs regularly**: `tail -f monitor.log` to catch any issues

---

## 📝 Support

If you encounter issues:
1. Check the log file: `monitor.log`
2. Test components individually
3. Verify all credentials in config.json
4. Make sure integrations are connected to pages

---

**You're all set! 🎉**

The system will now:
- ✅ Monitor GPUs every 30 seconds
- ✅ Update Notion dashboard in real-time
- ✅ Send email alerts for idle processes
- ✅ Generate daily/weekly usage charts
- ✅ Store 7 days of history

Enjoy efficient GPU resource management!
