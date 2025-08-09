#!/usr/bin/env python3
"""
Script to verify that the CV file is accessible in the container.
This can be used during the build process to ensure the CV is properly included.
"""

import os
import sys
from pathlib import Path

def verify_cv_access():
    """Verify that the CV file is accessible in the container."""
    print("🔍 Verifying CV file accessibility...")
    
    # Check multiple possible CV paths
    cv_paths = [
        "/app/shared/cv/resume.pdf",
        "/app/cv/resume.pdf", 
        "shared/cv/resume.pdf",
        "cv/resume.pdf"
    ]
    
    cv_found = False
    for path in cv_paths:
        if os.path.exists(path):
            file_size = os.path.getsize(path)
            print(f"✅ CV found at: {path}")
            print(f"📊 File size: {file_size} bytes")
            cv_found = True
            break
        else:
            print(f"❌ CV not found at: {path}")
    
    if not cv_found:
        print("❌ ERROR: CV file not found in any expected location!")
        print("Available files in /app:")
        if os.path.exists("/app"):
            for root, dirs, files in os.walk("/app"):
                for file in files:
                    if file.endswith('.pdf'):
                        print(f"  - {os.path.join(root, file)}")
        return False
    
    print("✅ CV verification successful!")
    return True

if __name__ == "__main__":
    success = verify_cv_access()
    sys.exit(0 if success else 1) 