# This script adds header update logic to gpu_monitor.py

import re

# Read the file
with open('/home/lsc206573/gpu_monitor/gpu_monitor.py', 'r') as f:
    content = f.read()

# Find the section after "Find and update each GPU's code block"
# We'll add header update code right after the timestamp is defined

search_pattern = r"(timestamp = datetime\.now\(\)\.strftime\('%Y-%m-%d %H:%M:%S'\)\n)"

replacement = r'''\1
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

'''

# Apply the replacement
new_content = re.sub(search_pattern, replacement, content)

# Write back
with open('/home/lsc206573/gpu_monitor/gpu_monitor.py', 'w') as f:
    f.write(new_content)

print("✅ Header update logic added!")
