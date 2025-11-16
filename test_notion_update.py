import requests
import json
from datetime import datetime

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

notion_token = config['notion']['token']
page_id = config['notion']['realtime_page_id']  # Fixed!

headers = {
    "Authorization": f"Bearer {notion_token}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Test 1: Read the page
print("📖 Reading current page content...")
url = f"https://api.notion.com/v1/blocks/{page_id}/children"
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
print(f"Current blocks: {len(response.json().get('results', []))}")
print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")

# Test 2: Try to append a test block
print("\n✍️ Attempting to add a test block...")
test_content = {
    "children": [{
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{
                "type": "text",
                "text": {"content": f"Test update at {datetime.now().strftime('%H:%M:%S')}"}
            }]
        }
    }]
}

response = requests.patch(url, headers=headers, json=test_content)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✅ Test block added successfully - check your Notion page!")
else:
    print(f"❌ Error: {response.text}")
