#!/usr/bin/env python
"""
Compile translation files for the Xsens Sensor Data Collection application
"""

import os
import subprocess

def compile_translations():
    """Compile .po files to .mo files"""
    
    languages = ['zh', 'en']
    
    for lang in languages:
        po_file = f'translations/{lang}/LC_MESSAGES/messages.po'
        mo_file = f'translations/{lang}/LC_MESSAGES/messages.mo'
        
        if not os.path.exists(po_file):
            print(f"Warning: {po_file} not found, skipping...")
            continue
        
        print(f"Compiling {lang} translations...")
        
        try:
            # Try using msgfmt command
            result = subprocess.run(
                ['msgfmt', po_file, '-o', mo_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"  ✓ Successfully compiled {mo_file}")
            else:
                print(f"  ✗ Error compiling {lang}: {result.stderr}")
        
        except FileNotFoundError:
            # If msgfmt not found, try using pybabel
            print("  msgfmt not found, trying pybabel...")
            try:
                result = subprocess.run(
                    ['pybabel', 'compile', '-f', '-i', po_file, '-o', mo_file],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    print(f"  ✓ Successfully compiled {mo_file}")
                else:
                    print(f"  ✗ Error compiling {lang}: {result.stderr}")
            
            except FileNotFoundError:
                print("  ✗ Neither msgfmt nor pybabel found!")
                print("  Install gettext tools or run: pip install babel")
                return False
    
    print("\n✓ Translation compilation complete!")
    return True


if __name__ == '__main__':
    success = compile_translations()
    if not success:
        exit(1)