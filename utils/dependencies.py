"""Dependency validator - checks if required packages are installed"""

def validate_dependencies():
    """Check if all required packages are installed"""
    missing_packages = []
    
    # Check each required package
    required_packages = {
        'selenium': 'selenium',
        'pandas': 'pandas',
        'openpyxl': 'openpyxl',
        'bs4': 'beautifulsoup4',
        'webdriver_manager': 'webdriver-manager',
        'lxml': 'lxml'
    }
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ MISSING DEPENDENCIES:")
        print("\nThe following packages are required but not installed:\n")
        for pkg in missing_packages:
            print(f"  • {pkg}")
        print("\nInstall them using:")
        print(f"  pip install {' '.join(missing_packages)}")
        print()
        return False
    
    print("✅ All dependencies are installed\n")
    return True