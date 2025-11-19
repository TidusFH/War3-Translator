"""
stringextractor.py
Warcraft III Map System Identifier Extraction Engine
Version 2.2 - External Configuration Support
Standalone module for translator2.py
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
import chardet
import ftfy

# Import ConfigManager
try:
    from config_manager import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    print("⚠️ config_manager.py not found. Using default identifiers.")

@dataclass
class SystemIdentifier:
    identifier: str
    occurrences: List[int]
    translation: str = ""
    index: int = 0
    pattern_types: List[str] = None

    def __post_init__(self):
        if self.pattern_types is None:
            self.pattern_types = []

class StringExtractor:
    """Enhanced system identifier extraction engine for complex Warcraft III maps"""
    
    # Default fallback if config is missing
    DEFAULT_IDENTIFIERS = {
        '全属性': 'All Stats', '力量': 'STR', '敏捷': 'AGI', '智力': 'INT',
        '生命值': 'HP', '魔法值': 'MP', '生命回复': 'HP Regen', '魔法回复': 'MP Regen',
        '护甲': 'Armor', '法术抗性': 'Magic Resist', '攻击力': 'Attack Damage',
        '法强': 'Spell Power', '攻击速度': 'Attack Speed', '攻击间隔': 'Attack Interval'
    }

    # Enhanced detection patterns targeting correct parameters
    DETECTION_PATTERNS = [
        # String comparisons (critical for dependencies): LoadStr(...) == "text"
        (re.compile(rb'(?:LoadStr|GetStr)\s*\([^)]+\)\s*==\s*"([^"]+)"'), 'string_comparison'),
        
        # StringHash calls: StringHash("text")
        (re.compile(rb'StringHash\s*\(\s*"([^"]+)"\s*\)'), 'stringhash'),
        
        # LoadStr with string parameter: LoadStr(..., "text")
        (re.compile(rb'LoadStr\s*\([^)]+\s*,\s*"([^"]+)"\s*\)'), 'loadstr_param'),
        
        # SaveStr - capture the VALUE parameter (4th parameter): SaveStr(table, parentKey, key, "value")
        (re.compile(rb'SaveStr\s*\([^,]+,\s*[^,]+,\s*[^,]+,\s*"([^"]+)"\s*\)'), 'savestr_value'),
        
        # Hashtable operations where string is used as key: Save*(..., "key", value)
        (re.compile(rb'Save\w+\s*\([^,]+,\s*[^,]+,\s*"([^"]+)"\s*,', re.IGNORECASE), 'hashtable_key'),
        
        # Variable assignments: set var = "text"
        (re.compile(rb'set\s+\w+\s*=\s*"([^"]+)"'), 'variable_assign'),
        
        # Direct UI function calls
        (re.compile(rb'(?:DisplayTextToPlayer|BJDebugMsg|DialogSetMessage)\s*\([^,]+,\s*"([^"]+)"\s*\)'), 'ui_direct'),
        
        # Concatenated string parts: captures second part of "text" + "text"
        (re.compile(rb'"[^"]*"\s*\+\s*"([^"]+)"'), 'concat_part'),
    ]

    # Patterns that indicate a string is a file path and should be skipped
    PATH_PATTERNS = [
        re.compile(rb'^[A-Za-z]:[\\/]', re.IGNORECASE),  # Windows absolute path
        re.compile(rb'^[\\/][\\/]'),  # UNC path
        re.compile(rb'ReplaceableTextures[\\/]', re.IGNORECASE),
        re.compile(rb'Sound[s]?[\\/]', re.IGNORECASE),
        re.compile(rb'Model[s]?[\\/]', re.IGNORECASE),
        re.compile(rb'Texture[s]?[\\/]', re.IGNORECASE),
        re.compile(rb'\.(blp|mdl|mdx|tga|mp3|wav|w3m|w3x|slk|txt|ai|j)$', re.IGNORECASE),
    ]

    @staticmethod
    def get_identifiers() -> Dict[str, str]:
        """Get system identifiers from config or default."""
        if CONFIG_AVAILABLE:
            return config.load_system_identifiers() or StringExtractor.DEFAULT_IDENTIFIERS
        return StringExtractor.DEFAULT_IDENTIFIERS

    @staticmethod
    def get_blacklisted_strings() -> set:
        """Get blacklisted strings from config."""
        if CONFIG_AVAILABLE:
            return config.get_blacklisted_strings()
        return set()

    @staticmethod
    def is_path_like(s: bytes) -> bool:
        """Intelligently check if a string looks like a file path"""
        if not s or len(s) < 3:
            return False
        
        test_str = s[1:-1] if s.startswith(b'"') and s.endswith(b'"') else s
        
        for pattern in StringExtractor.PATH_PATTERNS:
            if pattern.search(test_str):
                return True
        
        if b'\\' in test_str or b'/' in test_str:
            if any(ext in test_str.lower() for ext in [b'.blp', b'.mdl', b'.mdx', b'.mp3']):
                return True
        
        return False

    @staticmethod
    def is_valid_ui_text(s: str) -> bool:
        """Validate if the string is meaningful UI text"""
        if not s or len(s.strip()) < 2:
            return False
        
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', s)
        if not chinese_chars:
            return False
        
        identifiers = StringExtractor.get_identifiers()
        if len(chinese_chars) < 2 and s not in identifiers:
            return False
        
        blacklist = StringExtractor.get_blacklisted_strings()
        if s in blacklist:
            return False
        
        return True

    @staticmethod
    def extract_identifiers_from_file(war3map_path: str, output_dir: str, verbose: bool = True) -> Optional[Dict[str, SystemIdentifier]]:
        """Extract system identifiers using enhanced detection patterns with intelligent filtering"""
        if not os.path.exists(war3map_path):
            if verbose:
                print(f" ✗ Error: {war3map_path} not found!")
            return None
        
        try:
            if verbose:
                print(f"=== SYSTEM IDENTIFIER EXTRACTION ===")
                print(f"Reading: {war3map_path}")
            
            with open(war3map_path, 'rb') as f:
                data = f.read()
            
            if verbose:
                print(f"File size: {len(data):,} bytes")
            
            identifiers = {}
            index_counter = 1
            
            system_identifiers = StringExtractor.get_identifiers()
            
            for chinese, english in system_identifiers.items():
                identifiers[chinese] = SystemIdentifier(
                    identifier=chinese,
                    occurrences=[],
                    translation=english,
                    index=index_counter,
                    pattern_types=[]
                )
                index_counter += 1
            
            if verbose:
                print(f"✓ Pre-loaded {len(identifiers)} standard identifiers")
            
            all_matches = []
            for pattern, ptype in StringExtractor.DETECTION_PATTERNS:
                try:
                    matches = list(pattern.finditer(data))
                    if matches and verbose:
                        print(f"Pattern '{ptype}': {len(matches)} raw match(es)")
                    all_matches.extend([(m, ptype) for m in matches])
                except Exception as e:
                    if verbose:
                        print(f"⚠ Pattern '{ptype}' failed: {e}")
            
            if not all_matches:
                if verbose:
                    print("ℹ No potential matches found")
                return {}
            
            processed = 0
            skipped_paths = 0
            skipped_invalid = 0
            
            for match, pattern_type in all_matches:
                identifier_bytes = match.group(1)
                
                if StringExtractor.is_path_like(identifier_bytes):
                    skipped_paths += 1
                    if verbose and skipped_paths <= 5:
                        print(f"  Skipping path: {identifier_bytes[:60]}...")
                    continue
                
                decoded_success = False
                for encoding in ['utf-8', 'gb18030', 'gbk', 'gb2312', 'big5']:
                    try:
                        identifier_str = identifier_bytes.decode(encoding)
                        
                        if not StringExtractor.is_valid_ui_text(identifier_str):
                            skipped_invalid += 1
                            continue
                        
                        if identifier_str in identifiers:
                            if verbose and len(identifiers[identifier_str].occurrences) == 0:
                                print(f"✓ Found in code: {identifiers[identifier_str].index}. '{identifier_str}' → '{identifiers[identifier_str].translation}'")
                        else:
                            identifiers[identifier_str] = SystemIdentifier(
                                identifier=identifier_str,
                                occurrences=[],
                                translation=identifier_str,
                                index=index_counter,
                                pattern_types=[]
                            )
                            index_counter += 1
                            if verbose:
                                print(f"⚠ {identifiers[identifier_str].index}. [{pattern_type}] '{identifier_str}' → '{identifier_str}' (not in standard list)")
                        
                        if pattern_type not in identifiers[identifier_str].pattern_types:
                            identifiers[identifier_str].pattern_types.append(pattern_type)
                        identifiers[identifier_str].occurrences.append(match.start())
                        processed += 1
                        decoded_success = True
                        break
                        
                    except (UnicodeDecodeError, LookupError):
                        continue
                
                if not decoded_success and verbose and len(identifier_bytes) > 10:
                    print(f"⚠ Failed to decode: {identifier_bytes[:50]}...")
            
            if verbose:
                print(f"\n✓ Processed {processed} valid identifiers")
                if skipped_paths > 0 or skipped_invalid > 0:
                    print(f"  Skipped {skipped_paths} paths, {skipped_invalid} invalid")
            
            if not identifiers:
                if verbose:
                    print("ℹ No valid system identifiers found after filtering")
                return {}
            
            os.makedirs(output_dir, exist_ok=True)
            
            chinese_path = os.path.join(output_dir, "identifier_chinese.txt")
            with open(chinese_path, 'w', encoding='utf-8') as f:
                for ident_obj in sorted(identifiers.values(), key=lambda x: x.index):
                    f.write(f"{ident_obj.index}. {ident_obj.identifier}\n")
            
            english_path = os.path.join(output_dir, "identifier_dictionary.txt")
            with open(english_path, 'w', encoding='utf-8') as f:
                f.write("# EDIT THIS FILE - Translate Chinese identifiers to English\n")
                f.write("# Format: Keep the number, translate the text after '->'\n")
                f.write("# Example: 1. 攻击力 -> Attack Damage\n\n")
                for ident_obj in sorted(identifiers.values(), key=lambda x: x.index):
                    f.write(f"{ident_obj.index}. {ident_obj.identifier} -> {ident_obj.translation}\n")
            
            json_path = os.path.join(output_dir, "identifier_dictionary.json")
            dict_data = {
                "extraction_date": datetime.now().isoformat(),
                "source_file": war3map_path,
                "total_identifiers": len(identifiers),
                "identifiers": [
                    {
                        "index": obj.index,
                        "chinese": obj.identifier,
                        "english": obj.translation,
                        "occurrences": len(obj.occurrences),
                        "patterns": obj.pattern_types
                    }
                    for obj in sorted(identifiers.values(), key=lambda x: x.index)
                ]
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(dict_data, f, ensure_ascii=False, indent=2)
            
            report_path = os.path.join(output_dir, "system_identifiers_detected.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("SYSTEM IDENTIFIER DETECTION REPORT\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source: {war3map_path}\n")
                f.write(f"Total Identifiers: {len(identifiers)}\n")
                f.write(f"Detection Patterns: {len(StringExtractor.DETECTION_PATTERNS)}\n")
                f.write("=" * 60 + "\n\n")
                
                for ident_obj in sorted(identifiers.values(), key=lambda x: x.index):
                    f.write(f"{ident_obj.index}. '{ident_obj.identifier}' → '{ident_obj.translation}'\n")
                    f.write(f"   Patterns: {', '.join(ident_obj.pattern_types)}\n")
                    f.write(f"   Occurrences: {len(ident_obj.occurrences)}\n\n")
            
            if verbose:
                print(f"\n✓ Saved outputs to {output_dir}")
                print(f"  - identifier_dictionary.txt (EDIT THIS)")
                print(f"  - system_identifiers_detected.txt (REFERENCE)")
                print(f"  - identifier_dictionary.json (DATA)")
            
            return identifiers
            
        except Exception as e:
            if verbose:
                print(f"✗ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
            return None

    @staticmethod
    def get_identifier_set(identifiers: Dict[str, SystemIdentifier]) -> set:
        """Convert identifiers dict to set of strings"""
        if not identifiers:
            return set()
        return set(identifiers.keys())

    @staticmethod
    def check_string_for_identifiers(text: str, identifier_set: set) -> List[str]:
        """Check if string contains any system identifiers"""
        if not text or not identifier_set:
            return []
        found = [ident for ident in identifier_set if ident in text]
        found.sort(key=len, reverse=True)
        return found

    @staticmethod
    def load_identifier_dictionary(output_dir: str) -> Dict[str, str]:
        """Load identifier dictionary from editable file (strips numbers)"""
        dict_file = os.path.join(output_dir, "identifier_dictionary.txt")
        
        if not os.path.exists(dict_file):
            return {}
        
        try:
            with open(dict_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            identifier_map = {}
            for line in lines:
                # Parse "1. 攻击力 -> Attack Damage"
                parts = line.split('->')
                if len(parts) >= 2:
                    chinese = re.sub(r'^\d+\.\s*', '', parts[0]).strip()
                    english = parts[1].strip()
                    if chinese and english:
                        identifier_map[chinese] = english
            
            return identifier_map
            
        except Exception as e:
            print(f"✗ Error loading identifier dictionary: {e}")
            return {}

    # === NEW METHODS FOR CLEAN TRANSLATION TEMPLATE ===
    @staticmethod
    def generate_translation_template(output_dir: str, identifiers: Dict[str, SystemIdentifier]) -> str:
        """
        Generate a clean translation template file with only English parts to edit.
        Format: index. EnglishTranslation
        """
        template_path = os.path.join(output_dir, "identifier_translations.txt")
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write("# TRANSLATION TEMPLATE - Edit the English text after each number\n")
            f.write("# This file contains ONLY the translations to edit.\n")
            f.write("# Example: 1. All Stats\n")
            f.write("#          2. STR\n\n")
            
            for ident_obj in sorted(identifiers.values(), key=lambda x: x.index):
                f.write(f"{ident_obj.index}. {ident_obj.translation}\n")
        
        return template_path

    @staticmethod
    def load_translation_template(output_dir: str) -> Dict[str, str]:
        """
        Load edited translations from template file.
        Returns: {index: translation}
        """
        template_path = os.path.join(output_dir, "identifier_translations.txt")
        
        if not os.path.exists(template_path):
            return {}
        
        translations = {}
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Match: "1. All Stats" or "1.All Stats"
                    match = re.match(r'^(\d+)\.\s*(.+)$', line)
                    if match:
                        idx = match.group(1)
                        translation = match.group(2).strip()
                        translations[idx] = translation
        except Exception as e:
            print(f"⚠️ Warning: Could not load translation template: {e}")
            return {}
        
        return translations

    @staticmethod
    def apply_template_translations(identifiers: Dict[str, SystemIdentifier], 
                                    template_translations: Dict[str, str]) -> Tuple[int, int]:
        """
        Update identifiers with translations from template.
        Returns: (updated_count, missing_count)
        """
        updated = 0
        missing = 0
        
        for ident_obj in identifiers.values():
            idx_str = str(ident_obj.index)
            if idx_str in template_translations:
                new_translation = template_translations[idx_str]
                if new_translation and new_translation != ident_obj.translation:
                    ident_obj.translation = new_translation
                    updated += 1
            else:
                missing += 1
        
        return updated, missing

    @staticmethod
    def replace_identifiers_in_code(war3map_data: bytes, identifier_map: Dict[str, str], 
                                      verbose: bool = True) -> Tuple[bytes, int]:
        """Replace identifiers in war3map.j binary data"""
        if not identifier_map:
            return war3map_data, 0
        
        modified_data = war3map_data
        total_replacements = 0
        
        # Sort by length (longest first)
        sorted_identifiers = sorted(identifier_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        for chinese, english in sorted_identifiers:
            try:
                chinese_bytes = chinese.encode('utf-8')
                english_bytes = english.encode('utf-8')
                
                count = modified_data.count(chinese_bytes)
                if count > 0:
                    modified_data = modified_data.replace(chinese_bytes, english_bytes)
                    total_replacements += count
                    if verbose:
                        print(f"  '{chinese}' → '{english}' ({count}x)")
            except Exception as e:
                if verbose:
                    print(f"  ✗ Error: {e}")
        
        return modified_data, total_replacements

    @staticmethod
    def replace_identifiers_in_text(text: str, identifier_map: Dict[str, str]) -> Tuple[str, int]:
        """Replace identifiers in plain text"""
        if not identifier_map:
            return text, 0
        
        modified_text = text
        total_replacements = 0
        
        # Sort by length (longest first)
        sorted_identifiers = sorted(identifier_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        for chinese, english in sorted_identifiers:
            count = modified_text.count(chinese)
            if count > 0:
                modified_text = modified_text.replace(chinese, english)
                total_replacements += count
        
        return modified_text, total_replacements

    @staticmethod
    def apply_identifiers_to_translation(original_chinese: str, manual_translation: str, 
                                          identifier_map: Dict[str, str]) -> Tuple[str, List[str]]:
        """Smart hybrid replacement for manual translations"""
        if not manual_translation or not identifier_map:
            return manual_translation, []
        
        found_identifiers = []
        for chinese, english in identifier_map.items():
            if chinese in original_chinese:
                found_identifiers.append((chinese, english))
        
        if not found_identifiers:
            return manual_translation, []
        
        result = manual_translation
        replaced = []
        
        # Direct Chinese replacement
        found_identifiers.sort(key=lambda x: len(x[0]), reverse=True)
        for chinese, standard_english in found_identifiers:
            if chinese in result:
                count = result.count(chinese)
                result = result.replace(chinese, standard_english)
                replaced.append(f"{chinese} ({count}x)")
        
        # Compound variation replacement
        compound_variations = {
            '攻击力': ['Attack Power', 'ATK Power', 'Atk Power', 'ATK', 'Atk'],
            '攻击速度': ['Attack Rate', 'Attack SPD', 'ATK Speed', 'ATK SPD', 'Atk SPD', 'ASPD'],
            '法强': ['Spell Power', 'Magic Power', 'AP', 'Spell Damage', 'Magic Damage'],
            '专精': ['Specialty', 'Expertise', 'Proficiency'],
            '护甲': ['Defence', 'Defense', 'ARM'],
            '法术抗性': ['Magic Resistance', 'MR', 'Spell Resistance', 'Spell Resist'],
            '全属性': ['All Attributes', 'Omnistats'],
            '物理吸血': ['Physical Lifesteal', 'Life Steal', 'Lifesteal', 'Physical Life Steal'],
            '法术吸血': ['Spell Lifesteal', 'Magic Vamp', 'Spell Life Steal'],
            '冷却缩减': ['CD Reduction', 'Cooldown Reduction'],
            '物理暴击': ['Physical Critical', 'Phys Crit'],
            '法术暴击': ['Spell Critical', 'Magic Crit'],
            '暴击': ['Critical', 'Critical Strike', 'Crit Strike'],
            '穿透': ['Pierce', 'Pen'],
            '物理穿透': ['Physical Pierce', 'Phys Pen'],
            '法术穿透': ['Spell Pierce', 'Magic Pen'],
            '法术穿透': ['Spell Pierce', 'Magic Pen'],
        }
        
        for chinese, standard_english in found_identifiers:
            if chinese not in original_chinese or chinese in replaced:
                continue
            
            variations = compound_variations.get(chinese, [])
            for variant in sorted(variations, key=len, reverse=True):
                if variant != standard_english and variant in result:
                    result = result.replace(variant, standard_english)
                    if chinese not in replaced:
                        replaced.append(f"{chinese} (variant: {variant}→{standard_english})")
                    break
        
        return result, replaced
