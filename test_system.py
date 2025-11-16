#!/usr/bin/env python3
"""
GPU Monitor - System Test Script
Verifies configuration and dependencies before running the full system
"""

import sys
import json
import subprocess
import os

def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    if version.major >= 3 and version.minor >= 6:
        print("✅ Python version OK")
        return True
    else:
        print("❌ Python 3.6+ required")
        return False

def check_dependencies():
    """Check required Python packages"""
    print("\nChecking Python packages...")
    packages = ['requests', 'matplotlib']
    all_ok = True
    
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} NOT installed")
            print(f"   Install with: pip3 install --user {package}")
            all_ok = False
    
    # Check optional boto3 for S3
    try:
        __import__('boto3')
        print(f"✅ boto3 installed (for S3 uploads)")
    except ImportError:
        print(f"⚠️  boto3 NOT installed (optional, for S3 uploads)")
        print(f"   Install with: pip3 install --user boto3")
    
    return all_ok

def check_nvidia_smi():
    """Check if nvidia-smi is available"""
    print("\nChecking NVIDIA drivers...")
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, check=True)
        print("✅ nvidia-smi available")
        
        # Count GPUs
        gpu_count = result.stdout.count('NVIDIA')
        print(f"   Found {gpu_count} GPU(s)")
        return True
    except FileNotFoundError:
        print("❌ nvidia-smi not found")
        print("   NVIDIA drivers may not be installed or not in PATH")
        return False
    except subprocess.CalledProcessError:
        print("❌ nvidia-smi failed to run")
        return False

def check_config_file():
    """Check if configuration file exists and is valid"""
    print("\nChecking configuration file...")
    
    if not os.path.exists('config.json'):
        print("❌ config.json not found")
        print("   Copy config_minimal.json to config.json and edit it")
        return False
    
    print("✅ config.json exists")
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        print("✅ config.json is valid JSON")
        
        # Check required fields
        required_fields = {
            'notion': ['token', 'realtime_page_id'],
            'gpus': None,
            'email': ['enabled'],
            'aws_s3': ['enabled']
        }
        
        warnings = []
        
        for key, subkeys in required_fields.items():
            if key not in config:
                print(f"⚠️  Missing '{key}' section in config")
                warnings.append(key)
            elif subkeys:
                for subkey in subkeys:
                    if subkey not in config[key]:
                        print(f"⚠️  Missing '{key}.{subkey}' in config")
                        warnings.append(f"{key}.{subkey}")
        
        # Check if credentials look like placeholders
        if 'YOUR_NOTION_TOKEN_HERE' in config.get('notion', {}).get('token', ''):
            print("⚠️  Notion token looks like placeholder - update with real token")
            warnings.append('notion_token')
        
        if 'YOUR_REALTIME_PAGE_ID_HERE' in config.get('notion', {}).get('realtime_page_id', ''):
            print("⚠️  Notion page ID looks like placeholder - update with real ID")
            warnings.append('notion_page_id')
        
        if warnings:
            print(f"\n⚠️  Found {len(warnings)} configuration issue(s)")
            print("   System will not work until these are fixed")
            return False
        else:
            print("✅ Configuration looks good")
            return True
    
    except json.JSONDecodeError as e:
        print(f"❌ config.json has invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading config.json: {e}")
        return False

def test_notion_api():
    """Test Notion API connection"""
    print("\nTesting Notion API...")
    
    try:
        import requests
        
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        token = config['notion']['token']
        page_id = config['notion']['realtime_page_id']
        
        if 'YOUR_' in token or 'YOUR_' in page_id:
            print("⚠️  Skipping - placeholders detected in config")
            return None
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28"
        }
        
        # Test API connection
        response = requests.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Notion API connection successful")
            return True
        elif response.status_code == 401:
            print("❌ Notion API authentication failed")
            print("   Check your Notion token")
            return False
        elif response.status_code == 404:
            print("❌ Notion page not found")
            print("   Check your page ID or integration connection")
            return False
        else:
            print(f"❌ Notion API error: {response.status_code}")
            print(f"   {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error testing Notion API: {e}")
        return False

def test_s3_connection():
    """Test AWS S3 connection if configured"""
    print("\nTesting AWS S3 connection...")
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        if not config.get('aws_s3', {}).get('enabled', False):
            print("⏭️  AWS S3 disabled in config - skipping")
            return None
        
        bucket = config.get('aws_s3', {}).get('bucket', '')
        access_key = config.get('aws_s3', {}).get('access_key', '')
        secret_key = config.get('aws_s3', {}).get('secret_key', '')
        region = config.get('aws_s3', {}).get('region', 'us-east-1')
        
        if not bucket or 'your-' in bucket.lower():
            print("⚠️  S3 bucket not configured")
            print("   Charts will be generated locally only")
            return None
        
        if 'YOUR_' in access_key or 'YOUR_' in secret_key:
            print("⚠️  AWS credentials look like placeholders")
            return None
        
        try:
            import boto3
        except ImportError:
            print("❌ boto3 not installed")
            print("   Install with: pip3 install --user boto3")
            return False
        
        # Test S3 connection
        if access_key and secret_key:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
        else:
            # Try default credentials
            s3_client = boto3.client('s3', region_name=region)
        
        # Test by listing buckets (lightweight operation)
        response = s3_client.list_buckets()
        
        # Check if our bucket exists
        bucket_exists = any(b['Name'] == bucket for b in response.get('Buckets', []))
        
        if bucket_exists:
            print(f"✅ S3 connection successful")
            print(f"   Bucket '{bucket}' exists and is accessible")
            return True
        else:
            print(f"⚠️  S3 connection successful, but bucket '{bucket}' not found")
            print(f"   Available buckets: {[b['Name'] for b in response.get('Buckets', [])]}")
            return None
    
    except Exception as e:
        print(f"❌ S3 connection test failed: {e}")
        return False

def test_email():
    """Test email configuration"""
    print("\nTesting email configuration...")
    
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        if not config.get('email', {}).get('enabled', False):
            print("⏭️  Email disabled in config - skipping")
            return None
        
        smtp_server = config['email'].get('smtp_server', '')
        smtp_port = config['email'].get('smtp_port', 587)
        sender_email = config['email'].get('sender_email', '')
        sender_password = config['email'].get('sender_password', '')
        
        if not smtp_server or not sender_email:
            print("⚠️  Email not fully configured")
            return None
        
        if 'YOUR_' in sender_password or not sender_password:
            print("⚠️  Email password looks like placeholder")
            return None
        
        import smtplib
        
        print(f"   Testing connection to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(sender_email, sender_password)
        server.quit()
        
        print("✅ Email configuration successful")
        return True
    
    except Exception as e:
        print(f"❌ Email test failed: {e}")
        return False

def check_file_permissions():
    """Check file permissions"""
    print("\nChecking file permissions...")
    
    files_to_check = ['gpu_monitor.py', 'gpu_visualizer.py', 'config.json']
    all_ok = True
    
    for filename in files_to_check:
        if os.path.exists(filename):
            if os.access(filename, os.R_OK):
                print(f"✅ {filename} is readable")
            else:
                print(f"❌ {filename} is not readable")
                all_ok = False
        else:
            print(f"⚠️  {filename} not found")
            all_ok = False
    
    # Check config.json permissions
    if os.path.exists('config.json'):
        stat_info = os.stat('config.json')
        mode = oct(stat_info.st_mode)[-3:]
        if mode == '600' or mode == '644':
            print(f"✅ config.json permissions OK ({mode})")
        else:
            print(f"⚠️  config.json has permissive permissions ({mode})")
            print("   Recommended: chmod 600 config.json")
    
    return all_ok

def main():
    """Run all tests"""
    print_header("GPU Monitor System Test")
    print("This script checks if your system is ready to run GPU monitoring.\n")
    
    results = {}
    
    # Run tests
    results['python'] = check_python_version()
    results['dependencies'] = check_dependencies()
    results['nvidia'] = check_nvidia_smi()
    results['config'] = check_config_file()
    results['permissions'] = check_file_permissions()
    
    # Optional tests (don't count as failures)
    results['notion'] = test_notion_api()
    results['s3'] = test_s3_connection()
    results['email'] = test_email()
    
    # Summary
    print_header("Test Summary")
    
    required_tests = ['python', 'dependencies', 'nvidia', 'config', 'permissions']
    required_passed = all(results[test] for test in required_tests if results[test] is not None)
    
    optional_tests = ['notion', 's3', 'email']
    optional_status = [results[test] for test in optional_tests if results[test] is not None]
    
    print(f"Required tests: {sum(1 for t in required_tests if results[t])}/{len(required_tests)} passed")
    if optional_status:
        print(f"Optional tests: {sum(1 for r in optional_status if r)}/{len(optional_status)} passed")
    
    if required_passed:
        print("\n✅ System is ready for monitoring!")
        print("\nNext steps:")
        print("1. Start monitoring:")
        print("   python3 gpu_monitor.py -c config.json")
        print("\n2. Or run in background:")
        print("   nohup python3 gpu_monitor.py -c config.json > monitor.log 2>&1 &")
        
        if results.get('s3'):
            print("\n3. Generate charts:")
            print("   python3 gpu_visualizer.py -c config.json")
        
        return 0
    else:
        print("\n❌ System has issues that need to be fixed")
        print("\nPlease fix the errors above and run this test again.")
        print("\nFor help, see SETUP_GUIDE.md")
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
