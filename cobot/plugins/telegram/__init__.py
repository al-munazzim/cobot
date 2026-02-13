"""Telegram plugin - multi-group message logging and archival.

Implements session.* extension points for cobot channel integration.
"""

# Don't import from plugin.py here - causes circular import during discovery
# Plugin loader uses create_plugin() directly from plugin.py
