"""
Configuration Manager for Warcraft III Translator
Handles loading of external data files and settings.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any

class ConfigManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.system_identifiers = {}
        self.jass_patterns = {}
        
        # Ensure data directory exists
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_system_identifiers(self) -> Dict[str, str]:
        """Load system identifiers from JSON."""
        file_path = self.data_dir / "system_identifiers.json"
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.system_identifiers = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading system identifiers: {e}")
        return self.system_identifiers

    def load_jass_patterns(self) -> Dict[str, Any]:
        """Load JASS patterns from JSON."""
        file_path = self.data_dir / "jass_patterns.json"
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.jass_patterns = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading JASS patterns: {e}")
        return self.jass_patterns

    def get_ui_funcs(self) -> List[bytes]:
        """Get UI functions as bytes for JASS scanning."""
        if not self.jass_patterns:
            self.load_jass_patterns()
        
        funcs = self.jass_patterns.get("ui_funcs", [])
        return [f.encode('utf-8') for f in funcs]

    def get_code_tokens(self) -> List[bytes]:
        """Get code tokens as bytes for JASS scanning."""
        if not self.jass_patterns:
            self.load_jass_patterns()
            
        tokens = self.jass_patterns.get("code_tokens", [])
        return [t.encode('utf-8') for t in tokens]

    def get_blacklisted_strings(self) -> set:
        """Get blacklisted strings."""
        if not self.jass_patterns:
            self.load_jass_patterns()
            
        return set(self.jass_patterns.get("blacklisted_strings", []))

# Global instance
config = ConfigManager()

