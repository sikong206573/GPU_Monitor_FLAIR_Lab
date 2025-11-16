import requests
import json
from datetime import datetime

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

notion_token = config['notion']['token']
page_id = config['notion']['realtime_page_id']

headers = {
    "Authorization": f"Bearer {notion_token}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Get the GPU 0 code block (block 5 from our debug)
# Let's get all blocks and find GPU 0's block ID
url = f"https://api.notion.com/v1/blocks/{page_id}/children"
response = requests.get(url, headers=headers)
blocks = response.json().get('results', [])

# Find GPU 0 block
gpu0_block = None
for block in blocks:
    if block['type'] == 'code':
        content = block['code']['rich_text'][0]['text']['content'] if block['code']['rich_text'] else ''
        if 'GPU 0:' in content:
            gpu0_block = block
            break

if gpu0_block:
    block_id = gpu0_block['id']
    print(f"Found GPU 0 block: {block_id}")
    
    # Try to update it
    new_content = f"""GPU 0: NVIDIA H100 NVL
─────────────────────────────────────────
Utilization: 99.9%  ← UPDATED AT {datetime.now().strftime('%H:%M:%S')}
Memory: 50000 MB / 95000 MB (52.6%)
Temperature: 75°C
Running Processes:
  • TEST UPDATE - This should appear on Notion!"""
    
    update_data = {
        "code": {
            "rich_text": [{
                "type": "text",
                "text": {"content": new_content}
            }],
            "language": "plain text"
        }
    }
    
    update_url = f"https://api.notion.com/v1/blocks/{block_id}"
    response = requests.patch(update_url, headers=headers, json=update_data)
    
    print(f"Update status: {response.status_code}")
    if response.status_code == 200:
        print("✅ GPU 0 block updated! Check Notion page!")
    else:
        print(f"❌ Error: {response.text}")
else:
    print("Could not find GPU 0 block")
