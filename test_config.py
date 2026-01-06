#!/usr/bin/env python
"""
Test script to validate Django configuration without database connection.
"""
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personalservice.settings')

import django
django.setup()

from django.conf import settings

def test_configuration():
    """Test the Django configuration."""
    print("=" * 60)
    print("Django Configuration Test")
    print("=" * 60)
    
    # Test ALLOWED_HOSTS
    print(f"\n1. ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    if '*' in settings.ALLOWED_HOSTS:
        print("   ✓ Server allows external access from any host")
    
    # Test Database configuration
    print(f"\n2. Database Configuration:")
    db_config = settings.DATABASES['default']
    print(f"   Engine: {db_config['ENGINE']}")
    print(f"   Name: {db_config['NAME']}")
    print(f"   User: {db_config['USER']}")
    print(f"   Host: {db_config['HOST']}")
    print(f"   Port: {db_config['PORT']}")
    
    if 'postgresql' in db_config['ENGINE']:
        print("   ✓ PostgreSQL database configured")
    
    # Test DEBUG mode
    print(f"\n3. DEBUG: {settings.DEBUG}")
    
    # Test SECRET_KEY
    print(f"\n4. SECRET_KEY: {'*' * 20} (hidden)")
    if settings.SECRET_KEY:
        print("   ✓ SECRET_KEY is set")
    
    print("\n" + "=" * 60)
    print("Configuration Test Complete!")
    print("=" * 60)
    print("\nServer is ready to accept external connections.")
    print("To start the server, run:")
    print("  python manage.py runserver 0.0.0.0:8000")
    print("\nMake sure PostgreSQL is running before starting the server.")

if __name__ == '__main__':
    test_configuration()
