# GPU Monitor - Quick Reference Card

## 🚀 Start/Stop Monitoring

```bash
# Start monitoring in background
nohup python3 gpu_monitor.py -c config.json > monitor.log 2>&1 &

# Check if running
ps aux | grep gpu_monitor

# Stop monitoring
pkill -f gpu_monitor.py

# View live logs
tail -f monitor.log
```

## 📊 Generate Charts

```bash
# Generate daily charts and upload to Notion
python3 gpu_visualizer.py -c config.json --period daily

# Generate weekly charts
python3 gpu_visualizer.py -c config.json --period weekly

# Generate both
python3 gpu_visualizer.py -c config.json

# Test locally without uploading
python3 gpu_visualizer.py -c config.json --no-upload
```

## 🔍 Check System Status

```bash
# View current GPU status
nvidia-smi

# Check database size
ls -lh gpu_monitor.db

# Count records in database
sqlite3 gpu_monitor.db "SELECT COUNT(*) FROM gpu_snapshots"

# View recent alerts
sqlite3 gpu_monitor.db "SELECT * FROM email_alerts ORDER BY timestamp DESC LIMIT 10"
```

## 📧 Test Email

```bash
# Send test email (edit with your config)
python3 -c "
import smtplib
from email.mime.text import MIMEText

msg = MIMEText('Test from GPU Monitor')
msg['Subject'] = 'Test Email'
msg['From'] = 'your.email@gmail.com'
msg['To'] = 'your.email@tamu.edu'

with smtplib.SMTP('smtp.gmail.com', 587) as server:
    server.starttls()
    server.login('your.email@gmail.com', 'your-app-password')
    server.send_message(msg)
print('✅ Test email sent!')
"
```

## 🗑️ Database Maintenance

```bash
# Clean old data (older than 7 days)
sqlite3 gpu_monitor.db "DELETE FROM gpu_snapshots WHERE timestamp < datetime('now', '-7 days')"
sqlite3 gpu_monitor.db "DELETE FROM process_snapshots WHERE timestamp < datetime('now', '-7 days')"
sqlite3 gpu_monitor.db "VACUUM"

# View database schema
sqlite3 gpu_monitor.db ".schema"

# Export data to CSV
sqlite3 gpu_monitor.db -header -csv "SELECT * FROM gpu_snapshots WHERE DATE(timestamp) = DATE('now')" > today.csv
```

## 🔧 Quick Fixes

### Monitor not updating Notion?
```bash
# Check logs
tail -n 50 monitor.log

# Test Notion API manually
curl -X GET https://api.notion.com/v1/pages/YOUR_PAGE_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Notion-Version: 2022-06-28"
```

### Charts not uploading?
```bash
# Test Imgur API
curl -X POST https://api.imgur.com/3/image \
  -H "Authorization: Client-ID YOUR_CLIENT_ID" \
  -F "image=@charts/daily/gpu_0_utilization_daily.png"
```

### Email not sending?
```bash
# Test SMTP connection
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your.email@gmail.com', 'your-app-password')
print('✅ SMTP connection successful')
server.quit()
"
```

## ⏰ Cron Jobs

```bash
# Edit crontab
crontab -e

# Useful cron schedules:

# Daily charts at 1 AM
0 1 * * * cd ~/gpu-monitor && python3 gpu_visualizer.py -c config.json --period daily

# Weekly charts every Monday at 2 AM
0 2 * * 1 cd ~/gpu-monitor && python3 gpu_visualizer.py -c config.json --period weekly

# Restart monitor daily at 3 AM (for system maintenance)
0 3 * * * pkill -f gpu_monitor.py && cd ~/gpu-monitor && nohup python3 gpu_monitor.py -c config.json > monitor.log 2>&1 &

# Clean old database records every Sunday at 4 AM
0 4 * * 0 cd ~/gpu-monitor && sqlite3 gpu_monitor.db "DELETE FROM gpu_snapshots WHERE timestamp < datetime('now', '-7 days'); VACUUM;"
```

## 📊 Useful SQL Queries

```bash
# Average GPU utilization today
sqlite3 gpu_monitor.db "
SELECT gpu_id, AVG(utilization) as avg_util
FROM gpu_snapshots 
WHERE DATE(timestamp) = DATE('now')
GROUP BY gpu_id
"

# Top users by GPU time today
sqlite3 gpu_monitor.db "
SELECT username, COUNT(*) as samples, SUM(memory_usage) as total_mem
FROM process_snapshots
WHERE DATE(timestamp) = DATE('now')
GROUP BY username
ORDER BY samples DESC
"

# Busiest GPU today
sqlite3 gpu_monitor.db "
SELECT gpu_id, AVG(utilization) as avg_util, MAX(utilization) as max_util
FROM gpu_snapshots
WHERE DATE(timestamp) = DATE('now')
GROUP BY gpu_id
ORDER BY avg_util DESC
"

# Idle processes in last hour
sqlite3 gpu_monitor.db "
SELECT DISTINCT p.username, p.gpu_id, p.pid
FROM process_snapshots p
JOIN gpu_snapshots g ON p.gpu_id = g.gpu_id 
  AND datetime(p.timestamp) = datetime(g.timestamp)
WHERE g.timestamp > datetime('now', '-1 hour')
  AND g.utilization < 5
GROUP BY p.username, p.gpu_id, p.pid
"
```

## 📝 Configuration Quick Edits

```bash
# Disable email alerts temporarily
sed -i 's/"enabled": true/"enabled": false/' config.json

# Change update interval to 60 seconds
sed -i 's/"update_interval": 30/"update_interval": 60/' config.json

# Change idle threshold to 15 minutes
sed -i 's/"idle_threshold_minutes": 10/"idle_threshold_minutes": 15/' config.json
```

## 🎯 Common Workflows

### Morning Check
```bash
# Open Notion real-time page in browser, or:
nvidia-smi
```

### Before Running Job
```bash
# Check which GPUs are free
nvidia-smi

# Or check Notion dashboard
```

### Got Idle Process Alert?
```bash
# Check if process still running
ps aux | grep <PID>

# Check GPU usage
nvidia-smi

# Kill if done
kill <PID>
```

### Weekly Review
```bash
# Generate and view weekly charts
python3 gpu_visualizer.py -c config.json --period weekly

# Open weekly charts Notion page
```

## 🐛 Debug Mode

```bash
# Run monitor in foreground (see all output)
python3 gpu_monitor.py -c config.json

# Run chart generator with verbose output
python3 gpu_visualizer.py -c config.json --period daily 2>&1 | tee chart_debug.log
```

## 🔐 Security Notes

```bash
# Protect config file (contains passwords)
chmod 600 config.json

# Check who can read it
ls -l config.json

# Should show: -rw------- (only you can read/write)
```

## 📈 Performance

```bash
# Database size
du -h gpu_monitor.db

# Number of records per table
sqlite3 gpu_monitor.db "
SELECT 
  'gpu_snapshots' as table_name, COUNT(*) as records FROM gpu_snapshots
UNION ALL
SELECT 
  'process_snapshots', COUNT(*) FROM process_snapshots
UNION ALL
SELECT 
  'email_alerts', COUNT(*) FROM email_alerts
"

# Records per day
sqlite3 gpu_monitor.db "
SELECT DATE(timestamp) as date, COUNT(*) as records
FROM gpu_snapshots
GROUP BY DATE(timestamp)
ORDER BY date DESC
LIMIT 7
"
```

---

## 🆘 Emergency Commands

```bash
# Stop everything
pkill -f gpu_monitor.py
pkill -f gpu_visualizer.py

# Reset database (WARNING: deletes all data)
rm gpu_monitor.db
python3 gpu_monitor.py -c config.json  # Will recreate

# Clear all Notion pages manually
# Just delete and recreate the pages, then update config.json with new IDs

# Remove all generated charts
rm -rf charts/
mkdir -p charts/daily charts/weekly
```

---

**Pro tip**: Bookmark this page for quick reference!
