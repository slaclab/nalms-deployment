import os
import sys

# The tools are plain scripts rather than a package, so make them importable from the tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
