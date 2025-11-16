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

# Get all blocks
url = f"https://api.notion.com/v1/blocks/{page_id}/children"
response = requests.get(url, headers=headers)
blocks = response.json().get('results', [])

print(f"Found {len(blocks)} blocks on the page:\n")

for i, block in enumerate(blocks):
    block_type = block['type']
    block_id = block['id']
    
    print(f"Block {i}: Type = {block_type}, ID = {block_id}")
    
    if block_type == 'code':
        content = block['code']['rich_text'][0]['text']['content'] if block['code']['rich_text'] else ''
        print(f"  Content preview: {content[:100]}...")
    elif block_type == 'paragraph':
        content = block['paragraph']['rich_text'][0]['text']['content'] if block['paragraph']['rich_text'] else ''
        print(f"  Content: {content}")
    
    print()
