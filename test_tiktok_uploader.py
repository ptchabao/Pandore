#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

"""
Simplified test script for TikTok uploader module
Tests basic functionality without importing full project dependencies
"""

import os
import sys


def test_syntax_check():
    """Test that the tiktok_uploader.py file has valid Python syntax"""
    print("=" * 60)
    print("Test 1: Syntax Check")
    print("=" * 60)
    
    uploader_path = os.path.join(os.path.dirname(__file__), 'src', 'tiktok_uploader.py')
    
    try:
        with open(uploader_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        compile(code, uploader_path, 'exec')
        print(f"✅ {uploader_path} has valid Python syntax")
        print()
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {uploader_path}:")
        print(f"   Line {e.lineno}: {e.msg}")
        print()
        return False
    except Exception as e:
        print(f"❌ Error checking syntax: {e}")
        print()
        return False


def test_config_structure():
    """Test that config.ini has the TikTok upload section"""
    print("=" * 60)
    print("Test 2: Configuration Check")
    print("=" * 60)
    
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.ini')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        required_fields = [
            'TikTok上传配置',
            '启用TikTok自动上传',
            'TikTok访问令牌',
            'TikTok开放ID'
        ]
        
        missing = []
        for field in required_fields:
            if field not in config_content:
                missing.append(field)
        
        if missing:
            print(f"❌ Missing configuration fields: {missing}")
            return False
        else:
            print(f"✅ All required configuration fields present in {config_path}")
            print()
            return True
            
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        print()
        return False


def test_main_py_integration():
    """Test that main.py imports and uses the tiktok uploader"""
    print("=" * 60)
    print("Test 3: Main.py Integration Check")
    print("=" * 60)
    
    main_path = os.path.join(os.path.dirname(__file__), 'main.py')
    
    try:
        with open(main_path, 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        checks = {
            'Import statement': 'from src.tiktok_uploader import upload_to_tiktok_safe',
            'Config loading': 'enable_tiktok_upload',
            'Upload call': 'upload_to_tiktok_safe',
            'Threading': 'upload_thread.start()'
        }
        
        failed = []
        for check_name, check_string in checks.items():
            if check_string not in main_content:
                failed.append(check_name)
        
        if failed:
            print(f"❌ Missing integration components: {failed}")
            return False
        else:
            print(f"✅ TikTok uploader properly integrated into main.py")
            print()
            return True
            
    except Exception as e:
        print(f"❌ Error checking main.py: {e}")
        print()
        return False


def test_log_directory():
    """Test that logs directory exists for TikTok upload logs"""
    print("=" * 60)
    print("Test 4: Log Directory Check")
    print("=" * 60)
    
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    
    if os.path.exists(logs_dir):
        print(f"✅ Logs directory exists: {logs_dir}")
        print()
        return True
    else:
        print(f"⚠️  Logs directory will be created on first upload: {logs_dir}")
        print()
        return True  # Not a failure, will be created automatically


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TikTok Upload Integration Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_syntax_check,
        test_config_structure,
        test_main_py_integration,
        test_log_directory
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    print()
    
    if all(results):
        print("✅ All tests passed!")
        print()
        print("📝 Next steps:")
        print("   1. Get TikTok API credentials from https://developers.tiktok.com/")
        print("   2. Add credentials to config/config.ini:")
        print("      - TikTok访问令牌 = your_access_token")
        print("      - TikTok开放ID = your_open_id")
        print("   3. Enable auto-upload: 启用TikTok自动上传 = 是")
        print("   4. Run main.py to record and auto-upload videos")
        print("   5. Check logs/tiktok_upload.log for upload status")
        print()
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
