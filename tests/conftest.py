import sys
import os

# Add parent directory (where app.py is) to Python path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

print(f"Added {parent_dir} to Python path")

# Import app here to verify it works
try:
    import app
    print("✓ Successfully imported app module")
except ImportError as e:
    print(f"✗ Failed to import app: {e}")