#!/usr/bin/env python3
import gi

try:
    gi.require_version('EDataServer', '1.2')
    gi.require_version('ECal', '2.0')
    from gi.repository import ECal, EDataServer
    print("available")
except (ImportError, ValueError) as e:
    print(f"unavailable: {e}")
