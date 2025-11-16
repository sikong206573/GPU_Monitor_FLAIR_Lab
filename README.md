# GPU Monitoring System

A comprehensive real-time GPU monitoring solution with Notion dashboard integration, automated alerting, and cloud-native AWS architecture.

## Features

- **Real-time Monitoring**: Tracks GPU utilization, memory usage, and temperature across multiple GPUs (30-second intervals)
- **Notion Integration**: Live dashboard with auto-updating status displays
- **Process Tracking**: SQLite database stores detailed process history with user attribution
- **Email Alerts**: Automated notifications for idle GPU processes
- **Visualization**: Daily and weekly usage charts with user color-coding
- **Cloud Integration**: AWS S3 for chart storage, designed for enterprise scalability

## Architecture

- **Local Data**: SQLite for process history and metrics
- **Dashboard**: Notion API for real-time status updates
- **Storage**: AWS S3 for chart image hosting
- **Notifications**: SMTP for email alerts
- **Monitoring**: 30-second polling interval with in-place updates (no page flickering)

## Setup

### Prerequisites
```bash
pip install requests pynvml boto3
```

### Configuration

1. Copy the template configuration:
```bash
cp config.template.json config.json
```

2. Fill in your credentials:
   - **Notion**: Create integration at https://www.notion.so/my-integrations
   - **AWS**: Create IAM user with S3 access
   - **Email**: Generate app password for Gmail

3. Update GPU list in `config.json` to match your hardware

### Running
```bash
# One-time run
python3 gpu_monitor.py -c config.json

# Background with auto-restart (recommended)
nohup python3 gpu_monitor.py -c config.json > monitor.log 2>&1 &

# Auto-start on server reboot (add to crontab)
@reboot cd /path/to/gpu_monitor && nohup python3 gpu_monitor.py -c config.json > monitor.log 2>&1 &
```

## Project Structure
```
gpu_monitor/
├── gpu_monitor.py          # Main monitoring script
├── config.json             # Configuration (not in repo)
├── config.template.json    # Template for setup
├── gpu_monitor.db          # SQLite database (auto-created)
├── charts/                 # Generated visualizations
└── README.md
```

## Technical Highlights

- **In-place Notion updates**: Prevents page flickering by updating existing blocks
- **User-level automation**: Works without root access via cron
- **Self-healing**: Automatic recovery from API failures
- **Scalable design**: Ready for extension to DynamoDB, Lambda, CloudWatch

## Use Case

Designed for shared research lab environments with 4+ GPUs where multiple users need:
- Visibility into GPU availability
- Process accountability and usage tracking
- Historical usage analysis
- Automated idle process notifications

## Future Enhancements

- [ ] Full AWS cloud-native architecture (DynamoDB, Lambda, CloudWatch)
- [ ] Web dashboard with real-time charts
- [ ] Advanced analytics and usage predictions
- [ ] Multi-server monitoring

## Author

Sicong Liu  
Texas A&M University

---

**Note**: This project demonstrates cloud engineering skills including API integration, database design, automation, and AWS services - valuable experience for cloud/DevOps roles.
