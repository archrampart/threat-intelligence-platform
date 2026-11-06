"""Create a test watchlist with mixed IOC types for alert testing."""

import requests
import json
from uuid import uuid4

# Backend API URL
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Test credentials (adjust if needed)
USERNAME = "admin"
PASSWORD = "admin123"

def login():
    """Login and get access token."""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={
            "username": USERNAME,
            "password": PASSWORD,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.text}")
    return response.json()["access_token"]

def create_test_watchlist(token):
    """Create a test watchlist with mixed IOC types."""
    
    # Test IOCs - mix of URLs, domains, and IPs
    # These are test values that should trigger alerts when checked
    ioc_list = [
        # URLs
        "http://malicious-site.com/phishing",
        "https://suspicious-domain.net/download.exe",
        "http://192.168.1.100/malware",
        "http://test-malware.com/payload.bin",
        "https://evil-domain.org/stealer.exe",
        # Domains
        "malicious-domain.com",
        "suspicious-site.net",
        "phishing-attempt.org",
        "command-control.example",
        "bad-actor.io",
        # IPs
        "192.168.1.100",
        "10.0.0.50",
        "172.16.0.25",
        "203.0.113.42",
        "198.51.100.99",
    ]
    
    # Create a text file content with all IOCs
    ioc_file_content = "\n".join(ioc_list)
    
    # Create watchlist with file upload
    files = {
        "file": ("test_iocs.txt", ioc_file_content, "text/plain"),
    }
    
    data = {
        "name": "Test Alert Watchlist",
        "description": "Test watchlist with mixed IOC types (URL, domain, IP) for alert generation testing",
        "check_interval": "30",  # Check every 30 minutes
        "notification_enabled": "true",
    }
    
    url_count = sum(1 for ioc in ioc_list if ioc.startswith(('http://', 'https://')))
    domain_count = sum(1 for ioc in ioc_list if '.' in ioc and not ioc.startswith(('http://', 'https://')) and not any(c.isdigit() for c in ioc.split('.')[0] if '.' in ioc))
    ip_count = sum(1 for ioc in ioc_list if '.' in ioc and any(c.isdigit() for c in ioc.split('.')[0]))
    
    print(f"  Creating watchlist with {len(ioc_list)} IOCs...")
    print(f"  - URLs: {url_count}")
    print(f"  - Domains: {domain_count}")
    print(f"  - IPs: {ip_count}")
    
    response = requests.post(
        f"{API_BASE_URL}/watchlists/",
        data=data,
        files=files,
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    
    if response.status_code != 201:
        print(f"✗ Error creating watchlist: {response.status_code}")
        print(response.text)
        return None
    
    watchlist = response.json()
    print(f"✓ Watchlist created: {watchlist['name']} (ID: {watchlist['id']})")
    print(f"✓ Assets added: {len(watchlist.get('assets', []))}")
    
    return watchlist

def main():
    """Main function."""
    print("Creating test watchlist for alert testing...")
    print("=" * 50)
    
    try:
        # Login
        print("1. Logging in...")
        token = login()
        print("✓ Login successful")
        
        # Create watchlist
        print("\n2. Creating test watchlist...")
        watchlist = create_test_watchlist(token)
        
        if watchlist:
            print("\n" + "=" * 50)
            print("✓ Test watchlist created successfully!")
            print(f"\nWatchlist ID: {watchlist['id']}")
            print(f"Name: {watchlist['name']}")
            print(f"Assets: {len(watchlist.get('assets', []))}")
            print(f"\nTo check this watchlist and generate alerts, use:")
            print(f"  POST /api/v1/watchlists/{watchlist['id']}/check")
            print(f"\nOr check all watchlists:")
            print(f"  POST /api/v1/watchlists/check-all")
        else:
            print("\n✗ Failed to create watchlist")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

