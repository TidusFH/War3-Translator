"""
translator.py
Warcraft III Map Translation Tool with System Identifier & Cross-File Dependency Support
Version 8.0 - Fixed bytes literal syntax error
"""

import os
import re
import shutil
import hashlib
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
import chardet
import ftfy

# Import the string extractor module
try:
    import stringextractor as se
    STRING_EXTRACTOR_AVAILABLE = True
except ImportError:
    STRING_EXTRACTOR_AVAILABLE = False
    print(" ⚠️ Warning: stringextractor.py not found - system identifier features disabled")

# --- Configuration ---
UI_FUNCS = [
    b'DisplayTextToPlayer', b'DisplayTimedTextToPlayer',
    b'DisplayTextToForce', b'DisplayTimedTextToForce',
    b'BJDebugMsg', b'CreateTextTag', b'CreateTextTagUnitBJ',
    b'CreateTextTagLocBJ', b'TransmissionFromUnit', b'TransmissionFromUnitWithNameBJ',
    b'DialogSetMessage', b'DialogAddButton', b'TimerDialogSetTitle'
]

CODE_TOKENS = [
    b'GetHandleId', b'GetTriggeringTrigger', b'GetTriggerUnit', b'GetEnumUnit',
    b'GetManipulatingUnit', b'GetTriggerPlayer', b'GetOwningPlayer',
    b'LoadReal', b'LoadInteger', b'LoadBoolean', b'LoadStr', b'LoadUnit',
    b'SaveReal', b'SaveInteger', b'SaveBoolean', b'SaveStr',
    b'GetSpell', b'GetAbility', b'CreateUnit', b'RemoveUnit', b'KillUnit',
    b'function ', b'endfunction', b'local ', b'set ', b'call ',
    b'if ', b'then', b'endif', b'elseif', b'else',
    b'loop', b'endloop', b'exitwhen', b'return',
    b'native ', b'constant ', b'array ', b'takes ', b'returns ',
    b'globals', b'endglobals', b'type ', b'extends',
    b'integer ', b'real ', b'boolean ', b'string ', b'unit ',
    b'trigger ', b'timer ', b'location ', b'group ', b'player ',
    b'force ', b'effect ', b'sound ', b'handle ',
    b'hashtable', b'InitHashtable',
    b'udg_', b'gg_', b'Trig_', b'Unit_',
    b'==', b'!=', b'<=', b'>=', b'and ', b'or ', b'not ',
]

IDENTIFIER_PATTERNS = [
    re.compile(rb'^[a-zA-Z_][a-zA-Z0-9_]*$'),
    re.compile(rb'^udg_'),
    re.compile(rb'^gg_'),
    re.compile(rb'^Trig_'),
    re.compile(rb'^\w+_\w+$'),
]

FOURCC_PATTERN = re.compile(rb"^[A-Za-z0-9]{4}$")
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]')
TRY_CODECS = ['gb18030', 'gbk', 'gb2312', 'big5', 'utf-8', 'shift-jis', 'euc-kr']
JASS_ESCAPES = {b'\\', b'"', b'n', b'r', b't', b'b', b'f', b'v', b'a', b'0'}
CUSTOM_BOX_KEYS = ['Ubertip', 'Tip', 'Description', 'Hotkey']

# --- Data Classes ---
@dataclass
class ExtractedString:
    start: int
    end: int
    raw: bytes
    text: str
    encoding: str
    context: str = "unknown"

@dataclass
class ExtractionMetadata:
    file_hash: str
    file_size: int
    string_count: int
    restrict_ui: bool
    extraction_date: str
    version: str = "8.0"

@dataclass
class ChangeInfo:
    """Information about a changed string during reinsertion."""
    index: int
    byte_start: int
    byte_end: int
    line_number: int
    original: str
    translation: str
    context_before: str
    context_after: str
    auto_fixed: bool = False
    fixes_applied: List[str] = None

@dataclass
class SharedString:
    """Represents a string that must be synchronized across files."""
    chinese_original: str
    english_translation: str = ""
    found_in_jass: bool = False
    found_in_txt: bool = False
    jass_contexts: List[str] = field(default_factory=list)
    txt_contexts: List[Tuple[str, str]] = field(default_factory=list)  # (file, key)
    is_color_code: bool = False
    is_critical: bool = True

# --- Helper Functions ---
def create_backup(file_path: str, backup_dir: str = "backups") -> Optional[str]:
    """Create a timestamped backup of a file."""
    try:
        os.makedirs(backup_dir, exist_ok=True)
        if not os.path.exists(file_path):
            return None
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{Path(file_path).stem}_{timestamp}{Path(file_path).suffix}"
        backup_path = os.path.join(backup_dir, backup_name)
        shutil.copy2(file_path, backup_path)
        print(f" ✓ Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        print(f" ⚠️ Warning: Could not create backup: {e}")
        return None

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f" ⚠️ Warning: Could not hash file: {e}")
        return ""

def open_with_notepad(file_path: str):
    """Open file with notepad."""
    try:
        subprocess.Popen(['notepad.exe', file_path])
        print(f" ✓ Opened {file_path} in Notepad")
    except Exception as e:
        print(f" ⚠️ Could not open Notepad: {e}")

def count_lines_in_bytes(data: bytes) -> int:
    """Count number of lines in byte data."""
    return data.count(b'\n') + (1 if data and not data.endswith(b'\n') else 0)

def byte_offset_to_line_number(data: bytes, offset: int) -> int:
    """Convert byte offset to line number."""
    line_num = 1
    for i in range(min(offset, len(data))):
        if data[i:i+1] == b'\n':
            line_num += 1
    return line_num

def get_context_around_offset(data: bytes, offset: int, context_size: int = 80) -> Tuple[str, str]:
    """Get text context before and after a byte offset."""
    start = max(0, offset - context_size)
    end = min(len(data), offset + context_size)
    before = data[start:offset]
    after = data[offset:end]
    try:
        before_str = before.decode('utf-8', errors='replace').replace('\n', '\\n').replace('\r', '\\r')
        after_str = after.decode('utf-8', errors='replace').replace('\n', '\\n').replace('\r', '\\r')
    except:
        before_str = repr(before)
        after_str = repr(after)
    return before_str[-60:], after_str[:60]

def fix_jass_string(text: str, string_index: int) -> Tuple[str, List[str]]:
    """
    Auto-fix common issues in JASS strings.
    Returns: (fixed_text, list_of_fixes_applied)
    """
    fixes_applied = []
    
    # 1. Convert actual newlines to escaped sequences
    if '\r\n' in text:
        text = text.replace('\r\n', '\\n')
        fixes_applied.append("Converted Windows newlines to \\n")
    if '\n' in text:
        count = text.count('\n')
        text = text.replace('\n', '\\n')
        fixes_applied.append(f"Converted {count} newline(s) to \\n")
    if '\r' in text:
        text = text.replace('\r', '\\n')
        fixes_applied.append("Converted carriage returns to \\n")
    
    # 2. Fix unescaped quotes
    result = []
    i = 0
    quote_fixes = 0
    while i < len(text):
        if text[i] == '"':
            if i == 0 or text[i-1] != '\\':
                result.append('\\"')
                quote_fixes += 1
            else:
                result.append('"')
        else:
            result.append(text[i])
        i += 1
    
    if quote_fixes > 0:
        text = ''.join(result)
        fixes_applied.append(f"Escaped {quote_fixes} unescaped quote(s)")
    
    # 3. Remove control characters
    control_chars_removed = 0
    cleaned = []
    for char in text:
        char_code = ord(char)
        if char_code < 32 and char not in '\t':
            control_chars_removed += 1
        else:
            cleaned.append(char)
    
    if control_chars_removed > 0:
        text = ''.join(cleaned)
        fixes_applied.append(f"Removed {control_chars_removed} control character(s)")
    
    if fixes_applied:
        print(f" ✓ Auto-fixed string {string_index}: {', '.join(fixes_applied)}")
    
    return text, fixes_applied

def compare_line_counts(original_data: bytes, new_data: bytes) -> Dict:
    """Compare line counts between original and new data."""
    orig_lines = count_lines_in_bytes(original_data)
    new_lines = count_lines_in_bytes(new_data)
    return {
        'original': orig_lines,
        'new': new_lines,
        'difference': new_lines - orig_lines,
        'original_size': len(original_data),
        'new_size': len(new_data)
    }

def decode_cjk_advanced(b: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Advanced decoding using chardet and ftfy."""
    if not b:
        return None, None
    
    try:
        detection = chardet.detect(b)
        encoding = detection.get('encoding')
        confidence = detection.get('confidence', 0)
        if encoding and confidence > 0.7:
            try:
                s = b.decode(encoding, errors='strict')
                s_fixed = ftfy.fix_text(s)
                if CJK_RE.search(s_fixed):
                    return s_fixed, encoding
            except (UnicodeDecodeError, TypeError, LookupError):
                pass
    except Exception:
        pass
    
    for enc in TRY_CODECS:
        try:
            s = b.decode(enc, errors='strict')
            s_fixed = ftfy.fix_text(s)
            if CJK_RE.search(s_fixed):
                return s_fixed, enc
        except (UnicodeDecodeError, TypeError, LookupError):
            continue
    
    return None, None

def contains_chinese(text):
    """Check if text contains Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]+', text))

def is_word_boundary(data: bytes, idx: int, word: bytes) -> bool:
    """Check if a word exists at a specific index with clear boundaries."""
    n = len(data)
    if idx < 0 or idx + len(word) > n:
        return False
    if data[idx:idx+len(word)].lower() != word:
        return False
    if idx > 0:
        prev = data[idx-1:idx]
        if prev.isalnum() or prev == b'_':
            return False
    end_idx = idx + len(word)
    if end_idx < n:
        next_char = data[end_idx:end_idx+1]
        if next_char.isalnum() or next_char == b'_':
            return False
    return True

def is_likely_code_identifier(raw: bytes) -> bool:
    """Check if a string is likely a code identifier."""
    for pattern in IDENTIFIER_PATTERNS:
        if pattern.match(raw):
            return True
    if FOURCC_PATTERN.match(raw):
        return True
    if len(raw) <= 3 and b' ' not in raw:
        return True
    if raw.isupper() and b'_' in raw:
        return True
    return False

def analyze_string_context(data: bytes, str_start: int, raw: bytes) -> str:
    """Analyze the context around a string."""
    context_before = data[max(0, str_start - 200):str_start]
    context_after = data[str_start + len(raw):min(len(data), str_start + len(raw) + 50)]
    
    for ui_func in UI_FUNCS:
        if ui_func in context_before:
            return "ui"
    
    suspicious_patterns = [
        b'function ', b'local ', b'set ', b'call ',
        b'hashtable', b'array', b'takes', b'returns'
    ]
    
    for pattern in suspicious_patterns:
        if pattern in context_before[-100:]:
            return "suspicious"
    
    if b'=' in context_before[-50:] and b'set ' in context_before[-100:]:
        return "suspicious"
    
    return "general"

def scan_strings(data: bytes, restrict_ui: bool = False, progress_callback=None) -> List[ExtractedString]:
    """Enhanced byte-level scan with improved code detection."""
    out = []
    n = len(data)
    i = 0
    in_string = False
    in_line_comment = False
    in_block_comment = False
    in_globals = False
    in_function = False
    function_depth = 0
    str_start = -1
    last_progress = 0
    
    try:
        while i < n:
            if progress_callback and i - last_progress > 100000:
                progress_callback(i, n)
                last_progress = i
            
            b0 = data[i:i+1]
            b1 = data[i+1:i+2]
            
            if in_line_comment:
                if b0 == b'\n':
                    in_line_comment = False
                i += 1
                continue
            
            if in_block_comment:
                if b0 == b'*' and b1 == b'/':
                    in_block_comment = False
                    i += 2
                else:
                    i += 1
                continue
            
            if not in_string:
                if b0 == b'/' and b1 == b'/':
                    in_line_comment = True
                    i += 2
                    continue
                
                if b0 == b'/' and b1 == b'*':
                    in_block_comment = True
                    i += 2
                    continue
                
                if not in_globals and is_word_boundary(data, i, b'globals'):
                    in_globals = True
                    i += 7
                    continue
                
                if in_globals and is_word_boundary(data, i, b'endglobals'):
                    in_globals = False
                    i += 10
                    continue
                
                if is_word_boundary(data, i, b'function'):
                    in_function = True
                    function_depth += 1
                    i += 8
                    continue
                
                if is_word_boundary(data, i, b'endfunction'):
                    function_depth -= 1
                    if function_depth <= 0:
                        in_function = False
                        function_depth = 0
                    i += 11
                    continue
                
                if b0 == b'"':
                    if in_globals:
                        i += 1
                        continue
                    in_string = True
                    str_start = i + 1
                    i += 1
                    continue
            
            else:
                if b0 == b'\\':
                    if b1 in JASS_ESCAPES:
                        i += 2
                        continue
                    i += 1
                    continue
                
                if b0 == b'"':
                    str_end = i
                    raw = data[str_start:str_end]
                    
                    if len(raw) < 2:
                        in_string = False
                        i += 1
                        continue
                    
                    if any(tok in raw for tok in CODE_TOKENS):
                        in_string = False
                        i += 1
                        continue
                    
                    if is_likely_code_identifier(raw):
                        in_string = False
                        i += 1
                        continue
                    
                    context = analyze_string_context(data, str_start, raw)
                    
                    if restrict_ui and context != "ui":
                        in_string = False
                        i += 1
                        continue
                    
                    if context == "suspicious":
                        in_string = False
                        i += 1
                        continue
                    
                    s, enc = decode_cjk_advanced(raw)
                    if s and enc:
                        out.append(ExtractedString(
                            start=str_start,
                            end=str_end,
                            raw=raw,
                            text=s,
                            encoding=enc,
                            context=context
                        ))
                    
                    in_string = False
                    i += 1
                    continue
            
            i += 1
    
    except Exception as e:
        print(f" ⚠️ Warning: Error during scan at byte {i}: {e}")
    
    return out

def sanitize_for_legacy_encoding(text: str) -> str:
    """Enhanced Unicode character replacement."""
    replacements = {
        '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'",
        '\u201e': '"', '\u201f': '"', '\u2032': "'", '\u2033': '"',
        '\u2013': '-', '\u2014': '--', '\u2015': '--', '\u2212': '-',
        '\u2026': '...', '\u22ef': '...',
        '\u00a0': ' ', '\u202f': ' ', '\u2000': ' ', '\u2001': ' ',
        '\u2002': ' ', '\u2003': ' ', '\u2004': ' ', '\u2005': ' ',
        '\u2022': '*', '\u2023': '*', '\u25e6': '*', '\u2043': '*',
        '\u00b7': '*', '\u30fb': '*',
        '\u00d7': 'x', '\u00f7': '/', '\u2260': '!=',
        '\u2192': '->', '\u2190': '<-',
    }
    
    result = text
    for unicode_char, replacement in replacements.items():
        result = result.replace(unicode_char, replacement)
    return result

def validate_encoding_compatibility(text: str, encoding: str) -> Tuple[bool, List[str]]:
    """Check if text can be encoded without loss."""
    try:
        text.encode(encoding, errors='strict')
        return True, []
    except UnicodeEncodeError as e:
        problematic = []
        for char in text:
            try:
                char.encode(encoding, errors='strict')
            except UnicodeEncodeError:
                if char not in problematic:
                    problematic.append(char)
        return False, problematic

def write_change_report(changes: List[ChangeInfo], output_path: str):
    """Write a detailed report of all changes."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("WARCRAFT III MAP TRANSLATION CHANGE REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            from datetime import datetime
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total changes: {len(changes)}\n")
            
            auto_fixed = sum(1 for c in changes if c.auto_fixed)
            if auto_fixed > 0:
                f.write(f"Auto-fixed strings: {auto_fixed}\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
            
            for change in changes:
                f.write(f"STRING #{change.index}\n")
                f.write(f"{'─' * 80}\n")
                f.write(f"Line Number: {change.line_number}\n")
                f.write(f"Byte Range: {change.byte_start} - {change.byte_end}\n")
                
                if change.auto_fixed and change.fixes_applied:
                    f.write(f"✓ AUTO-FIXED: {', '.join(change.fixes_applied)}\n")
                f.write(f"\n")
                
                f.write(f"Context Before: ...{change.context_before}\n")
                f.write(f"Context After: {change.context_after}...\n\n")
                
                f.write("ORIGINAL:\n")
                f.write(f"  {change.original}\n\n")
                
                f.write("TRANSLATION:\n")
                f.write(f"  {change.translation}\n\n")
                
                orig_len = len(change.original.encode('utf-8', errors='ignore'))
                trans_len = len(change.translation.encode('utf-8', errors='ignore'))
                size_diff = trans_len - orig_len
                f.write(f"Size: {orig_len} → {trans_len} bytes ({size_diff:+d})\n")
                f.write("\n" + "=" * 80 + "\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("=" * 80 + "\n")
            total_orig_size = sum(len(c.original.encode('utf-8', errors='ignore')) for c in changes)
            total_trans_size = sum(len(c.translation.encode('utf-8', errors='ignore')) for c in changes)
            f.write(f"Total strings changed: {len(changes)}\n")
            if auto_fixed > 0:
                f.write(f"Auto-fixed strings: {auto_fixed}\n")
            f.write(f"Original total size: {total_orig_size:,} bytes\n")
            f.write(f"Translation total size: {total_trans_size:,} bytes\n")
            f.write(f"Size difference: {total_trans_size - total_orig_size:+,} bytes\n")
            
            lines = sorted(set(c.line_number for c in changes))
            f.write(f"\nLines affected: {len(lines)}\n")
            if len(lines) <= 20:
                f.write(f"Line numbers: {', '.join(map(str, lines))}\n")
            else:
                f.write(f"Line range: {min(lines)} - {max(lines)}\n")
        
        print(f" ✓ Change report written to: {output_path}")
    except Exception as e:
        print(f" ⚠️ Warning: Could not write change report: {e}")

# --- NEW: Dependency-Aware Translation Functions ---
def scan_jass_dependencies(data: bytes) -> Dict[str, List[str]]:
    """
    Detects strings in JASS that are used for lookups/comparisons.
    These MUST be synchronized with text files.
    """
    dependencies = {}
    
    # Patterns where strings are used as keys
    # FIX: Removed non-ASCII characters from bytes literal patterns
    CRITICAL_PATTERNS = [
        # String comparisons
        (re.compile(rb'if\s+.*==\s*"(.+?)"', re.IGNORECASE), "string_comparison"),
        (re.compile(rb'StringHash\s*\(\s*"(.+?)"\s*\)', re.IGNORECASE), "stringhash"),
        (re.compile(rb'SubString\s*\([^,]+,\s*\d+,\s*\d+\)\s*==\s*"(.+?)"', re.IGNORECASE), "substring_match"),
        
        # Hashtable saves (keys are often matched later)
        (re.compile(rb'SaveStr\s*\([^,]+,\s*\d+,\s*\d+,\s*"(.+?)"\)', re.IGNORECASE), "hashtable_key"),
        
        # Variable assignments that look like keys (FIXED: removed non-ASCII bytes literal)
        (re.compile(rb'set\s+\w+\s*=\s*"([^"]+)"', re.IGNORECASE), "variable_key"),
    ]
    
    # Get the JASS content as string for regex scanning
    try:
        jass_str = data.decode('utf-8', errors='ignore')
        jass_bytes = jass_str.encode('utf-8', errors='ignore')
    except:
        return dependencies
    
    for pattern, context in CRITICAL_PATTERNS:
        try:
            # Decode pattern to string for matching, then encode matches
            matches = pattern.finditer(jass_bytes)
            for match in matches:
                try:
                    # Decode the matched string properly
                    chinese_str = match.group(1).decode('utf-8', errors='ignore')
                    if contains_chinese(chinese_str):
                        # Extract function context
                        func_name = extract_surrounding_function_name(data, match.start())
                        if chinese_str not in dependencies:
                            dependencies[chinese_str] = []
                        if func_name and func_name not in dependencies[chinese_str]:
                            dependencies[chinese_str].append(func_name)
                except:
                    continue
        except Exception as e:
            print(f"⚠️ Warning: Pattern matching failed: {e}")
            continue
    
    return dependencies

def extract_surrounding_function_name(data: bytes, offset: int) -> Optional[str]:
    """Extract the function name containing the given offset."""
    # Look backwards for 'function' keyword
    search_window = data[max(0, offset - 500):offset]
    func_match = re.search(rb'function\s+([a-zA-Z_]\w*)', search_window)
    if func_match:
        return func_match.group(1).decode('utf-8', errors='ignore')
    return None

def build_dependency_graph(j_path: str, txt_files: List[str]) -> Dict[str, SharedString]:
    """
    Builds a graph of strings that must be translated identically
    across JASS and text files.
    """
    graph = {}
    
    # Scan JASS for critical strings
    print(f"🔍 Scanning JASS file for string dependencies...")
    with open(j_path, 'rb') as f:
        jass_data = f.read()
    jass_deps = scan_jass_dependencies(jass_data)
    
    if not jass_deps:
        print("✓ No critical string dependencies detected.")
        return graph
    
    print(f"⚠ Found {len(jass_deps)} strings used in JASS logic:")
    for chinese_str in list(jass_deps.keys())[:5]:
        print(f"  {chinese_str}")
    if len(jass_deps) > 5:
        print(f"  ... and {len(jass_deps) - 5} more")
    
    # Scan text files for matching strings
    for txt_file in txt_files:
        if not os.path.exists(txt_file):
            continue
            
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        current_section = None
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Section headers
            section_match = re.match(r'^\[(\w+)\]$', stripped)
            if section_match:
                current_section = section_match.group(1)
                continue
            
            # Key-value pairs (both quoted and unquoted)
            for match in re.finditer(r'(\w+)\s*=\s*"?([^"\n]+)"?', stripped):
                key = match.group(1)
                value = match.group(2)
                
                # Check if any JASS-critical strings appear in this value
                for chinese_str in jass_deps:
                    if chinese_str in value:
                        if chinese_str not in graph:
                            graph[chinese_str] = SharedString(
                                chinese_original=chinese_str,
                                found_in_jass=True,
                                found_in_txt=True,
                                jass_contexts=jass_deps[chinese_str],
                                is_color_code='|c' in value
                            )
                        graph[chinese_str].txt_contexts.append((os.path.basename(txt_file), key))
    
    return graph

def preserve_color_code_structure(original: str, chinese: str, translation: str) -> str:
    """
    Preserves Warcraft III color code structure when translating.
    Example: |c6fff0011奥达奇战刃|r → |c6fff0011Odaqi Blade|r
    """
    # Pattern: |c######<text>|r
    pattern = r'(\|c[0-9a-fA-F]{8})' + re.escape(chinese) + r'(\|r)'
    replacement = r'\1' + translation + r'\2'
    return re.sub(pattern, replacement, original)

def get_translation_for_string(chinese_str: str, tokens_dir: str, base_name: str) -> Optional[str]:
    """
    Retrieves the translation for a specific Chinese string from token files.
    Returns None if not found or translation is empty.
    """
    # This is a simplified version - would need extraction order mapping for perfect accuracy
    tokens_file = os.path.join(tokens_dir, f"{base_name}_chinese.txt")
    
    if not os.path.exists(tokens_file):
        return None
    
    try:
        with open(tokens_file, 'r', encoding='utf-8-sig', newline=None) as f:
            content = f.read()
    except:
        return None
    
    # Parse the numbered list format and search for the string
    # This is a simplified approach
    for line in content.split('\n'):
        if chinese_str in line and '->' in line:
            parts = line.split('->')
            if len(parts) > 1:
                return parts[1].strip()
    return None

def mode4_synchronized_dependency_translation(j_path: str, txt_files: List[str], tokens_dir: str, out_dir: str) -> bool:
    """
    Mode 4: Ensures critical strings are translated identically
    across JASS and text files to prevent breaking item/ability effects.
    """
    print("\n" + "="*70)
    print("MODE 4: DEPENDENCY-AWARE SYNCHRONIZED TRANSLATION")
    print("="*70)
    print("This mode detects strings used in JASS logic and ensures they")
    print("are translated identically in all text files to prevent")
    print("breaking item effects, abilities, and triggers.\n")
    
    # Step 1: Build dependency graph
    graph = build_dependency_graph(j_path, txt_files)
    
    if not graph:
        print("No dependencies to synchronize. Use Mode 2 or 3 instead.")
        return False
    
    # Step 2: Load translations from token files
    print("\n📥 Loading translations...")
    
    # Load JASS translations (these are the authoritative ones for logic strings)
    jass_tokens_file = os.path.join(tokens_dir, "war3map.j_chinese.txt")
    jass_json_file = os.path.join(tokens_dir, "war3map.j.json")
    
    if not os.path.exists(jass_tokens_file):
        print(f"✗ Error: {jass_tokens_file} not found!")
        print("  You must extract and translate war3map.j first.")
        return False
    
    if not os.path.exists(jass_json_file):
        print(f"✗ Error: {jass_json_file} not found!")
        return False
    
    try:
        with open(jass_json_file, 'r', encoding='utf-8') as f:
            jass_extraction = json.load(f)
        
        with open(jass_tokens_file, 'r', encoding='utf-8-sig', newline=None) as f:
            trans_content = f.read()
    except Exception as e:
        print(f"✗ Error reading JASS data: {e}")
        return False
    
    # Build translation map from extraction data
    trans_lines = trans_content.split('\n')
    line_map = {}
    current_num = None
    current_text = []
    
    for line in trans_lines:
        match = re.match(r'^(\d+)\.\s*(.*)', line)
        if match:
            if current_num is not None:
                line_map[current_num] = ' '.join(current_text)
            current_num = int(match.group(1))
            current_text = [match.group(2)]
        elif current_num is not None and line.strip():
            current_text.append(line.rstrip())
    
    if current_num is not None:
        line_map[current_num] = '\n'.join(current_text)
    
    # Map original strings to their translations
    for idx, extract in enumerate(jass_extraction, 1):
        if idx in line_map:
            original = extract.get('original', '')
            translation = line_map[idx]
            
            # Only add if translation is not empty and not identical to original
            if translation and translation.strip() and translation != original:
                # Check if this string is in our dependency graph
                for chinese_str in graph:
                    if chinese_str == original:
                        graph[chinese_str].english_translation = translation
                        break
    
    # Show what we found
    print("\n📋 Synchronization mapping:")
    synced = 0
    missing = 0
    for chinese_str, data in graph.items():
        if data.english_translation:
            print(f"  ✓ {chinese_str} → {data.english_translation}")
            synced += 1
        else:
            print(f"  ⚠ {chinese_str} - No translation found!")
            missing += 1
    
    if missing > 0:
        print(f"\n⚠️ Warning: {missing} critical strings lack translations.")
        if input("Continue anyway? (y/n): ").lower() != 'y':
            return False
    
    if synced == 0:
        print("No synchronized translations to apply.")
        return False
    
    # Step 3: Apply synchronized translations
    print("\n🔄 Applying synchronized translations...")
    
    # Backup files
    create_backup(j_path)
    for txt_file in txt_files:
        if os.path.exists(txt_file):
            create_backup(txt_file)
    
    # Update JASS file
    print("\n  Updating JASS...")
    with open(j_path, 'rb') as f:
        jass_content = f.read()
    
    # Decode to string for replacement, then re-encode
    jass_str = jass_content.decode('utf-8', errors='ignore')
    jass_replacements = 0
    
    for chinese_str, data in graph.items():
        if data.english_translation:
            # Replace in string literals (handle both simple and escaped quotes)
            old_pattern = f'"{chinese_str}"'
            new_pattern = f'"{data.english_translation}"'
            
            # Count occurrences before replacement
            count_before = jass_str.count(old_pattern)
            jass_str = jass_str.replace(old_pattern, new_pattern)
            
            # Also check for patterns with escaped quotes if needed
            if count_before == 0:
                old_escaped = chinese_str.replace('"', '\\"')
                new_escaped = data.english_translation.replace('"', '\\"')
                old_pattern_escaped = f'"{old_escaped}"'
                new_pattern_escaped = f'"{new_escaped}"'
                jass_str = jass_str.replace(old_pattern_escaped, new_pattern_escaped)
            
            jass_replacements += jass_str.count(data.english_translation)
    
    jass_output = os.path.join(out_dir, os.path.basename(j_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(jass_output, 'wb') as f:
        f.write(jass_str.encode('utf-8', errors='ignore'))
    
    print(f"  ✓ JASS: Applied synchronized translations")
    
    # Update text files
    txt_updated = 0
    for txt_file in txt_files:
        if not os.path.exists(txt_file):
            continue
        
        print(f"\n  Updating {os.path.basename(txt_file)}...")
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        replacements = 0
        for chinese_str, data in graph.items():
            if data.english_translation:
                # Handle both quoted and unquoted values
                # Pattern: key = "value" or key=value
                pattern = rf'(\w+\s*=\s*"?)({re.escape(chinese_str)})(.*?"?)'
                replacement = rf'\1{data.english_translation}\3'
                new_content = re.sub(pattern, replacement, content)
                
                if new_content != content:
                    replacements += new_content.count(data.english_translation) - content.count(data.english_translation)
                    content = new_content
                
                # Special handling for color-coded strings
                if data.is_color_code:
                    pattern = rf'(\|c[0-9a-fA-F]{{8}}){re.escape(chinese_str)}(\|r)'
                    replacement = rf'\1{data.english_translation}\2'
                    new_content = re.sub(pattern, replacement, content)
                    if new_content != content:
                        replacements += new_content.count(data.english_translation) - content.count(data.english_translation)
                        content = new_content
        
        if replacements > 0:
            output_file = os.path.join(out_dir, os.path.basename(txt_file))
            with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            print(f"  ✓ Applied {replacements} synchronized translations")
            txt_updated += 1
        else:
            print(f"  - No changes needed")
    
    # Step 4: Summary
    print("\n" + "="*70)
    print("SYNCHRONIZED TRANSLATION COMPLETE!")
    print("="*70)
    print(f"✓ {synced} critical strings synchronized")
    print(f"✓ {txt_updated} .txt files updated")
    print(f"✓ 1 war3map.j file updated")
    print(f"📁 Output directory: {out_dir}")
    print(f"💾 Backups saved in: backups/")
    print(f"\n⚠ IMPORTANT: All synchronized strings use the SAME")
    print(f"  translation in both JASS and text files to prevent bugs!")
    
    # Open the JASS file for verification
    print(f"\n📂 Opening {jass_output} in Notepad for verification...")
    open_with_notepad(jass_output)
    
    return True

def extract_chinese_from_txt_file(input_file: str, output_dir: str, preserve_custom_boxes: bool = True) -> int:
    """Extract Chinese text from .txt files."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        extractions = []
        chinese_only = []
        current_section = None
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            
            section_match = re.match(r'^\[(\w+)\]$', stripped)
            if section_match:
                current_section = section_match.group(1)
                continue
            
            match_kv = re.match(r'^(\w+)=(.*)$', stripped)
            if match_kv:
                key = match_kv.group(1)
                value = match_kv.group(2)
                if contains_chinese(value):
                    needs_custom_box = preserve_custom_boxes and key in CUSTOM_BOX_KEYS
                    extractions.append({
                        'line': line_num,
                        'section': current_section,
                        'key': key,
                        'original': value,
                        'format': 'unquoted',
                        'custom_box': needs_custom_box
                    })
                    chinese_only.append(value)
                continue
            
            matches = re.finditer(r'(\w+)\s*=\s*"([^"]*)"', line)
            for match in matches:
                key = match.group(1)
                value = match.group(2)
                if contains_chinese(value):
                    needs_custom_box = preserve_custom_boxes and key in CUSTOM_BOX_KEYS
                    extractions.append({
                        'line': line_num,
                        'section': current_section,
                        'key': key,
                        'original': value,
                        'format': 'quoted',
                        'custom_box': needs_custom_box
                    })
                    chinese_only.append(value)
        
        if not extractions:
            print(f" ⚠️ No Chinese text found in {input_file}")
            return 0
        
        base_name = os.path.basename(input_file)
        json_output = os.path.join(output_dir, f"{base_name}.json")
        txt_output = os.path.join(output_dir, f"{base_name}_chinese.txt")
        
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(extractions, f, ensure_ascii=False, indent=2)
        
        with open(txt_output, 'w', encoding='utf-8', newline='\n') as f:
            for idx, text in enumerate(chinese_only, 1):
                f.write(f"{idx}. {text}\n")
        
        custom_box_count = sum(1 for e in extractions if e.get('custom_box', False))
        print(f" ✓ Extracted {len(chinese_only)} entries from {base_name}")
        if custom_box_count > 0:
            print(f"   ({custom_box_count} custom box fields detected)")
        print(f"   JSON: {json_output}")
        print(f"   Text: {txt_output}")
        
        return len(chinese_only)
    
    except Exception as e:
        print(f" ✗ Error processing {input_file}: {e}")
        import traceback
        traceback.print_exc()
        return 0

def extract_chinese_tokens(files: List[str], output_dir: str, preserve_custom_boxes: bool = True) -> int:
    """Extract Chinese tokens from .txt files."""
    os.makedirs(output_dir, exist_ok=True)
    total_tokens = 0
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f" ⚠️ Warning: {file_path} not found, skipping...")
            continue
        count = extract_chinese_from_txt_file(file_path, output_dir, preserve_custom_boxes)
        total_tokens += count
    
    return total_tokens

def extract_war3map_j(j_path: str, out_dir: str, restrict_ui: bool = False, detect_identifiers: bool = True) -> bool:
    """
    Enhanced extraction with system identifier detection.
    
    Args:
        j_path: Path to war3map.j
        out_dir: Output directory
        restrict_ui: Only extract UI strings
        detect_identifiers: Use stringextractor to detect system identifiers
    """
    os.makedirs(out_dir, exist_ok=True)
    
    if not os.path.exists(j_path):
        print(f" ✗ Error: {j_path} not found!")
        return False
    
    print(f"\nProcessing {j_path}...")
    create_backup(j_path)
    
    try:
        with open(j_path, 'rb') as f:
            data = f.read()
        
        file_hash = hashlib.sha256(data).hexdigest()
        file_size = len(data)
        
        print(f" File size: {file_size:,} bytes")
        print(f" SHA256: {file_hash[:16]}...")
        
        # === SYSTEM IDENTIFIER DETECTION ===
        identifiers = None
        identifier_set = set()
        
        if detect_identifiers and STRING_EXTRACTOR_AVAILABLE:
            print(f"\n 🔍 Detecting system identifiers...")
            identifiers = se.StringExtractor.extract_identifiers_from_file(j_path, out_dir, verbose=True)
            if identifiers:
                identifier_set = se.StringExtractor.get_identifier_set(identifiers)
                
                # Generate clean translation template
                template_path = se.StringExtractor.generate_translation_template(out_dir, identifiers)
                
                print(f"\n 📝 IMPORTANT: Edit files in this order:")
                print(f"   1. {template_path} (EDIT THIS - simple format)")
                print(f"   2. {os.path.join(out_dir, 'identifier_dictionary.txt')} (reference)")
                print(f"   3. {os.path.join(out_dir, 'war3map.j_chinese.txt')} (main translations)")
        
        # === STRING EXTRACTION ===
        def progress(current, total):
            pct = (current / total) * 100
            print(f" Scanning strings: {pct:.1f}%", end='\r')
        
        tokens = scan_strings(data, restrict_ui=restrict_ui, progress_callback=progress)
        print(f" Scanning strings: 100.0%")
        
        if not tokens:
            print(" ⚠️ WARNING: No Chinese strings found!")
            return False
        
        filtered_tokens = []
        skipped = 0
        for t in tokens:
            if len(t.text) >= 2 and not is_likely_code_identifier(t.raw):
                filtered_tokens.append(t)
            else:
                skipped += 1
        
        if skipped > 0:
            print(f" Filtered out {skipped} suspicious code-like strings")
        
        tokens = filtered_tokens
        
        if not tokens:
            print(" ⚠️ WARNING: No valid Chinese strings after filtering!")
            return False
        
        base = os.path.basename(j_path)
        from datetime import datetime
        
        metadata = ExtractionMetadata(
            file_hash=file_hash,
            file_size=file_size,
            string_count=len(tokens),
            restrict_ui=restrict_ui,
            extraction_date=datetime.now().isoformat()
        )
        
        with open(os.path.join(out_dir, f"{base}_metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)
        
        # Write tokens with identifier warnings
        tokens_txt_path = os.path.join(out_dir, f"{base}_chinese.txt")
        with open(tokens_txt_path, 'w', encoding='utf-8', newline='\n') as f:
            for idx, t in enumerate(tokens, 1):
                escaped = t.text.replace('\n', '\\n').replace('\r', '\\r')
                
                # Mark strings containing identifiers
                if identifier_set:
                    found_ids = se.StringExtractor.check_string_for_identifiers(t.text, identifier_set)
                    if found_ids:
                        f.write(f"{idx}. {escaped} ⚠️ [{', '.join(found_ids)}]\n")
                    else:
                        f.write(f"{idx}. {escaped}\n")
                else:
                    f.write(f"{idx}. {escaped}\n")
        
        extractions_json = []
        for idx, t in enumerate(tokens, 1):
            extraction_data = {
                'index': idx,
                'byte_start': t.start,
                'byte_end': t.end,
                'encoding': t.encoding,
                'original': t.text,
                'raw_hex': t.raw.hex(),
                'length': len(t.raw),
                'context': t.context
            }
            
            if identifier_set:
                found_ids = se.StringExtractor.check_string_for_identifiers(t.text, identifier_set)
                if found_ids:
                    extraction_data['contains_identifiers'] = found_ids
            
            extractions_json.append(extraction_data)
        
        json_output = os.path.join(out_dir, f"{base}.json")
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(extractions_json, f, ensure_ascii=False, indent=2)
        
        map_data = []
        for t in tokens:
            map_data.append({
                'start': t.start,
                'end': t.end,
                'encoding': t.encoding,
                'raw_hex': t.raw.hex(),
                'length': len(t.raw)
            })
        
        with open(os.path.join(out_dir, f"{base}_map.json"), 'w', encoding='utf-8') as f:
            json.dump(map_data, f, indent=2)
        
        print(f"\n ✓ Extracted {len(tokens)} Chinese strings from {base}")
        
        context_counts = {}
        for t in tokens:
            context_counts[t.context] = context_counts.get(t.context, 0) + 1
        print(f" Context distribution:")
        for ctx, count in sorted(context_counts.items(), key=lambda x: -x[1]):
            print(f"   {ctx}: {count} strings")
        
        enc_counts = {}
        for t in tokens:
            enc_counts[t.encoding] = enc_counts.get(t.encoding, 0) + 1
        print(f" Encoding distribution:")
        for enc, count in sorted(enc_counts.items(), key=lambda x: -x[1]):
            print(f"   {enc}: {count} strings")
        
        print(f"\n Files created:")
        print(f"   {tokens_txt_path} (with identifier warnings if detected)")
        print(f"   {json_output} (extraction metadata)")
        if identifiers:
            print(f"   identifier_dictionary.txt (EDIT THIS for Mode 3)")
            print(f"   system_identifiers_detected.txt (detailed report)")
        
        print(f"\n 📂 Opening {tokens_txt_path} in Notepad...")
        open_with_notepad(tokens_txt_path)
        
        if identifiers:
            dict_path = os.path.join(out_dir, "identifier_dictionary.txt")
            if os.path.exists(dict_path):
                open_with_notepad(dict_path)
        
        return True
    
    except Exception as e:
        print(f" ✗ Fatal error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False

def reinsert_translations_txt(original_file: str, json_file: str, translated_file: str, output_dir: str) -> bool:
    """Reinsert translations into .txt file with identifier preservation."""
    if not os.path.exists(json_file):
        print(f" ✗ ERROR: {json_file} not found!")
        return False
    
    try:
        with open(json_file, 'r', encoding='utf-8-sig') as f:
            extractions = json.load(f)
    except json.JSONDecodeError as e:
        print(f" ✗ ERROR: {json_file} is not valid JSON!")
        print(f"   Details: {e}")
        return False
    
    if not os.path.exists(translated_file):
        print(f" ✗ ERROR: {translated_file} not found!")
        return False
    
    try:
        with open(translated_file, 'r', encoding='utf-8-sig', newline=None) as f:
            content = f.read()
    except Exception as e:
        print(f" ✗ ERROR reading {translated_file}: {e}")
        return False
    
    trans_lines = content.split('\n')
    line_map = {}
    current_num = None
    current_text = []
    
    for line in trans_lines:
        match = re.match(r'^(\d+)\.\s*(.*)$', line)
        if match:
            if current_num is not None:
                line_map[current_num] = '\n'.join(current_text)
            current_num = int(match.group(1))
            current_text = [match.group(2)]
        elif current_num is not None and line.strip():
            current_text.append(line.rstrip())
    
    if current_num is not None:
        line_map[current_num] = '\n'.join(current_text)
    
    translations = []
    for i in range(1, len(extractions) + 1):
        if i in line_map:
            trans = line_map[i].replace('\n', ' ')
            translations.append(trans)
        else:
            print(f" ⚠️ WARNING: Missing translation for entry {i}")
            translations.append("")
    
    # === IDENTIFIER PRESERVATION FOR MODE 2 ===
    identifier_map = {}
    if STRING_EXTRACTOR_AVAILABLE:
        # Try to load identifier dictionary from same directory
        base_dir = os.path.dirname(json_file)
        identifier_map = se.StringExtractor.load_identifier_dictionary(base_dir)
        
        if identifier_map:
            print(f" 🔍 Preserving {len(identifier_map)} identifiers...")
            identifier_preserved_count = 0
            
            # For each translation, check if original had identifiers
            for i in range(len(translations)):
                if i < len(extractions):
                    original_text = extractions[i].get('original', '')
                    
                    # Find which identifiers were in the original
                    found_ids = [ident for ident in identifier_map.keys() if ident in original_text]
                    
                    if found_ids and translations[i]:
                        # Replace English translations back to Chinese
                        for chinese_id in found_ids:
                            english_id = identifier_map[chinese_id]
                            if english_id in translations[i]:
                                translations[i] = translations[i].replace(english_id, chinese_id)
                                identifier_preserved_count += 1
            
            if identifier_preserved_count > 0:
                print(f" ✓ Preserved {identifier_preserved_count} identifier(s) in Chinese")
    
    print(f" Parsed {len([t for t in translations if t])} non-empty translations")
    print(f" Expected {len(extractions)} translations")
    
    if len(translations) != len(extractions):
        print(f" ✗ ERROR: Count mismatch!")
        missing = [i for i in range(1, len(extractions)+1) if i not in line_map]
        print(f"   Missing entries: {missing}")
        return False
    
    empty_indices = [i+1 for i, t in enumerate(translations) if not t]
    if empty_indices:
        print(f" ⚠️ WARNING: {len(empty_indices)} empty translations at: {empty_indices[:10]}")
        response = input("   Continue? (y/n): ")
        if response.lower() != 'y':
            return False
    
    try:
        with open(original_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f" ✗ ERROR reading {original_file}: {e}")
        return False
    
    custom_box_preserved = 0
    
       
    
    
    # Process each extraction in reverse order
    for idx in range(len(extractions) - 1, -1, -1):
        extract = extractions[idx]
        translation = translations[idx]
        line_idx = extract['line'] - 1
        
        if line_idx >= len(lines):
            print(f" ⚠️ ERROR: Line {extract['line']} out of range")
            continue
        
        original_line = lines[line_idx]
        key = extract['key']
        is_custom_box = extract.get('custom_box', False)
        
        if extract['format'] == 'unquoted':
            pattern = f'^{re.escape(key)}=.*$'
            if is_custom_box and translation and not translation.startswith('"'):
                replacement = f'{key}="{translation}"'
                custom_box_preserved += 1
            else:
                replacement = f'{key}={translation}'
        else:
            pattern = f'^{re.escape(key)}\\s*=\\s*".*"$'
            replacement = f'{key} = "{translation}"'
        
        new_line = re.sub(pattern, replacement, original_line.rstrip())
        if new_line == original_line.rstrip():
            print(f" ⚠️ WARNING: Line {extract['line']} pattern didn't match, using direct replacement")
            if is_custom_box and translation and not translation.startswith('"'):
                new_line = f'{key}="{translation}"'
            else:
                new_line = f'{key}={translation}'
        
        lines[line_idx] = new_line + '\n'
    
    output_file = os.path.join(output_dir, os.path.basename(original_file))
    os.makedirs(output_dir, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(lines)
    
    print(f" ✓ Success! Output: {output_file}")
    if custom_box_preserved > 0:
        print(f"   Custom box fields preserved: {custom_box_preserved}")
    
    return True


def insert_translations_txt(files: List[str], tokens_dir: str, output_dir: str) -> int:
    """Insert translations into .txt files."""
    os.makedirs(output_dir, exist_ok=True)
    translated_count = 0
    
    for file_path in files:
        base_name = os.path.basename(file_path)
        json_file = os.path.join(tokens_dir, f"{base_name}.json")
        translated_file = os.path.join(tokens_dir, f"{base_name}_chinese.txt")
        
        if not os.path.exists(json_file) or not os.path.exists(translated_file):
            print(f" ⚠️ Warning: Missing files for {base_name}, skipping...")
            continue
        
        if reinsert_translations_txt(file_path, json_file, translated_file, output_dir):
            translated_count += 1
    
    return translated_count

def reinsert_war3map_j(j_path: str, tokens_dir: str, out_dir: str, write_utf8: bool = False,
                       generate_report: bool = True, auto_fix: bool = True, 
                       preserve_identifiers: bool = True) -> bool:
    """Enhanced reinsertion with automatic fixing and identifier preservation."""
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.basename(j_path)
    tokens_file = os.path.join(tokens_dir, f"{base}_chinese.txt")
    metadata_file = os.path.join(tokens_dir, f"{base}_metadata.json")
    json_file = os.path.join(tokens_dir, f"{base}.json")
    map_file_json = os.path.join(tokens_dir, f"{base}_map.json")
    map_file = json_file if os.path.exists(json_file) else map_file_json
    
    if not os.path.exists(map_file):
        print(f" ✗ FATAL ERROR: {map_file} not found!")
        return False
    
    if not os.path.exists(tokens_file):
        print(f" ✗ Error: {tokens_file} not found!")
        return False
    
    print(f"\nProcessing {j_path} for reinsertion...")
    print(f" Auto-fix mode: {'ENABLED' if auto_fix else 'DISABLED'}")
    print(f" Preserve identifiers: {'ENABLED' if preserve_identifiers else 'DISABLED'}")
    
    create_backup(j_path)
    
    try:
        metadata = None
        restrict_ui = False
        
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                restrict_ui = metadata.get('restrict_ui', False)
            print(f" Loaded metadata from extraction")
            print(f" Original hash: {metadata.get('file_hash', 'N/A')[:16]}...")
            print(f" String count: {metadata.get('string_count', 'N/A')}")
        
        # Load original extraction data
        original_data = []
        with open(map_file, 'r', encoding='utf-8') as f:
            map_data = json.load(f)
        
        for item in map_data:
            if 'index' in item:
                original_data.append({
                    'start': item['byte_start'],
                    'end': item['byte_end'],
                    'encoding': item['encoding'],
                    'original_bytes': bytes.fromhex(item['raw_hex']),
                    'original_text': item.get('original', ''),
                    'context': item.get('context', 'unknown'),
                    'contains_identifiers': item.get('contains_identifiers', [])
                })
            else:
                original_data.append({
                    'start': item['start'],
                    'end': item['end'],
                    'encoding': item['encoding'],
                    'original_bytes': bytes.fromhex(item['raw_hex']),
                    'original_text': '',
                    'context': 'unknown',
                    'contains_identifiers': []
                })
        
        # Load identifier dictionary if preservation is enabled
        identifier_map = {}
        if preserve_identifiers and STRING_EXTRACTOR_AVAILABLE:
            print(f"\n 🔍 Loading identifier dictionary for preservation...")
            identifier_map = se.StringExtractor.load_identifier_dictionary(tokens_dir)
            if identifier_map:
                print(f" ✓ Loaded {len(identifier_map)} identifiers to preserve")
            else:
                print(f" ⚠️ No identifier dictionary found - skipping preservation")
        
        # Read translations
        with open(tokens_file, 'r', encoding='utf-8-sig', newline=None) as f:
            content = f.read()
        
        trans_lines = content.split('\n')
        line_map = {}
        current_num = None
        current_text = []
        
        for line in trans_lines:
            match = re.match(r'^(\d+)\.\s*(.*)', line)
            if match:
                if current_num is not None:
                    line_map[current_num] = ' '.join(current_text)
                current_num = int(match.group(1))
                current_text = [match.group(2)]
            elif current_num is not None and line.strip():
                current_text.append(line.rstrip())
        
        if current_num is not None:
            line_map[current_num] = '\n'.join(current_text)
        
        print(f"\n 🔄 Processing translations...")
        
        translations = []
        auto_fix_count = 0
        identifier_preserved_count = 0
        
        for i in range(1, len(original_data) + 1):
            if i in line_map:
                trans = line_map[i]
                
                # CRITICAL FIX: Preserve identifiers in Mode 2
                if preserve_identifiers and identifier_map and i-1 < len(original_data):
                    original_chinese = original_data[i-1]['original_text']
                    contains_ids = original_data[i-1].get('contains_identifiers', [])
                    
                    if original_chinese and contains_ids:
                        # Replace identifiers back to Chinese to preserve them
                        for chinese_id in contains_ids:
                            if chinese_id in identifier_map:
                                english_id = identifier_map[chinese_id]
                                # Replace English back to Chinese
                                if english_id in trans:
                                    trans = trans.replace(english_id, chinese_id)
                                    identifier_preserved_count += 1
                
                # Auto-fix if enabled
                if auto_fix:
                    fixed_trans, fixes = fix_jass_string(trans, i)
                    if fixes:
                        auto_fix_count += 1
                        trans = fixed_trans
                
                # Apply legacy encoding fixes
                trans = sanitize_for_legacy_encoding(trans)
                translations.append(trans)
            else:
                print(f" ⚠️ WARNING: Missing translation for entry {i}")
                translations.append("")
        
        if auto_fix_count > 0:
            print(f"\n ✓ Auto-fixed {auto_fix_count} string(s)")
        
        if identifier_preserved_count > 0:
            print(f" ✓ Preserved {identifier_preserved_count} identifier(s) in Chinese")
        
        # Continue with existing code for file verification, scanning, and reinsertion...
        with open(j_path, 'rb') as f:
            data = f.read()
        
        current_hash = hashlib.sha256(data).hexdigest()
        
        if metadata and metadata.get('file_hash') != current_hash:
            print(f" ⚠️ WARNING: File hash mismatch!")
            print(f"   Expected: {metadata.get('file_hash', 'N/A')[:16]}...")
            print(f"   Current: {current_hash[:16]}...")
            response = input("   Continue anyway? (y/n): ").strip().lower()
            if response != 'y':
                print(" Reinsertion cancelled.")
                return False
        
        tokens_now = scan_strings(data, restrict_ui=restrict_ui)
        
        if len(translations) != len(tokens_now):
            print(f"\n ✗ FATAL ERROR: COUNT MISMATCH")
            print(f"   Expected: {len(tokens_now)} strings")
            print(f"   Found: {len(translations)} translations")
            print(f"   Difference: {len(translations) - len(tokens_now):+d}")
            return False
        
        changes = []
        encoding_warnings = 0
        empty_translations = []
        
        for idx, (t, trans) in enumerate(zip(tokens_now, translations)):
            if not trans or trans.strip() == '':
                empty_translations.append(idx + 1)
                translations[idx] = t.text
                print(f" ⚠️ WARNING: Empty translation at string {idx+1}, using original text")
            
            # Track changes
            if generate_report and trans != t.text:
                line_num = byte_offset_to_line_number(data, t.start)
                ctx_before, ctx_after = get_context_around_offset(data, t.start)
                
                # Check if this was auto-fixed
                was_fixed = (idx + 1) <= len(line_map) and auto_fix
                fixes = []
                if was_fixed and (idx + 1) in line_map:
                    _, fixes = fix_jass_string(line_map[idx + 1], idx + 1)
                
                changes.append(ChangeInfo(
                    index=idx + 1,
                    byte_start=t.start,
                    byte_end=t.end,
                    line_number=line_num,
                    original=t.text,
                    translation=trans,
                    context_before=ctx_before,
                    context_after=ctx_after,
                    auto_fixed=len(fixes) > 0,
                    fixes_applied=fixes if fixes else None
                ))
            
            target_enc = original_data[idx]['encoding'] if idx < len(original_data) else 'gb18030'
            
            if not write_utf8:
                compatible, problematic = validate_encoding_compatibility(translations[idx], target_enc)
                if not compatible:
                    encoding_warnings += 1
                    if encoding_warnings <= 3:
                        print(f" ⚠️ String {idx+1}: Characters incompatible with {target_enc}: {problematic}")
        
        if encoding_warnings > 3:
            print(f" ⚠️ ... and {encoding_warnings - 3} more encoding warnings")
        
        if empty_translations:
            print(f" ⚠️ Found {len(empty_translations)} empty translations, replaced with originals")
        
        print(f"\n 🔧 Building output file...")
        
        out_bytes = bytearray()
        cursor = 0
        
        for idx, t in enumerate(tokens_now):
            out_bytes.extend(data[cursor:t.start])
            
            if write_utf8:
                target_enc = 'utf-8'
            elif idx < len(original_data):
                target_enc = original_data[idx]['encoding']
                if not target_enc or target_enc == 'None':
                    target_enc = 'gbk'
            else:
                target_enc = 'gbk'
            
            try:
                repl = translations[idx].encode(target_enc, errors='strict')
            except UnicodeEncodeError:
                print(f" ⚠️ String {idx+1}: Encoding to {target_enc} failed, using 'ignore' mode")
                repl = translations[idx].encode(target_enc, errors='ignore')
            
            out_bytes.extend(repl)
            cursor = t.end
        
        out_bytes.extend(data[cursor:])
        
        # LINE COUNT ANALYSIS
        line_comparison = compare_line_counts(data, out_bytes)
        
        print(f"\n{'='*70}")
        print(" LINE COUNT ANALYSIS")
        print(f"{'='*70}")
        print(f" Original file: {line_comparison['original']} lines")
        print(f" New file: {line_comparison['new']} lines")
        print(f" Difference: {line_comparison['difference']:+d} lines")
        
        if line_comparison['difference'] != 0:
            print(f"\n ⚠️ WARNING: Line count changed by {line_comparison['difference']:+d}!")
            if auto_fix:
                print(f"   This shouldn't happen with auto-fix enabled.")
                print(f"   There may be residual issues in the translations.")
        else:
            print(f" ✓ Line count preserved - safe to proceed!")
        
        out_path = os.path.join(out_dir, base)
        
        with open(out_path, 'wb') as f:
            if write_utf8:
                f.write(b'\xef\xbb\xbf')
            f.write(out_bytes)
        
        size_diff = len(out_bytes) - len(data)
        size_pct = (size_diff / len(data)) * 100
        
        print(f"\n ✅ Wrote translated file to {out_path}")
        print(f" Original size: {len(data):,} bytes")
        print(f" New size: {len(out_bytes):,} bytes")
        print(f" Difference: {size_diff:+,} bytes ({size_pct:+.2f}%)")
        
        if auto_fix_count > 0:
            print(f" Auto-fixed strings: {auto_fix_count}")
        
        if identifier_preserved_count > 0:
            print(f" Identifiers preserved: {identifier_preserved_count}")
        
        if encoding_warnings > 0:
            print(f" Encoding warnings: {encoding_warnings}")
        
        if empty_translations:
            print(f" Empty translations replaced: {len(empty_translations)}")
        
        # Generate reports
        if generate_report and len(changes) > 0:
            report_path = os.path.join(out_dir, f"{base}_changes.txt")
            write_change_report(changes, report_path)
        
        print(f"\n 📂 Opening {out_path} in Notepad for verification...")
        open_with_notepad(out_path)
        
        return True
    
    except Exception as e:
        print(f" ✗ Fatal error during reinsertion: {e}")
        import traceback
        traceback.print_exc()
        return False

def synchronized_translation_mode(jfile: str, txtfiles: List[str], tokens_dir: str, out_dir: str):
    """Mode 3: Hybrid translation (identifiers applied to manual translations)"""
    if not STRING_EXTRACTOR_AVAILABLE:
        print(" ✗ ERROR: stringextractor.py not found!")
        print("   Mode 3 requires the stringextractor module.")
        return False
    
    print("="*70)
    print("MODE 3: SYNCHRONIZED SYSTEM IDENTIFIER TRANSLATION")
    print("="*70)
    
    dict_path = tokens_dir
    print(f"\n🔍 Loading identifier translations...")
    
    # First, see if there's an edited template
    template_translations = se.StringExtractor.load_translation_template(dict_path)
    if template_translations:
        print(f" ✓ Found {len(template_translations)} translations in template")
        # Load the identifier dictionary
        identifier_map = se.StringExtractor.load_identifier_dictionary(dict_path)
        # Apply template translations
        updated, missing = se.StringExtractor.apply_template_translations(
            {k: se.SystemIdentifier(k, [], v, 0, []) for k, v in identifier_map.items()}, 
            template_translations
        )
        identifier_map = {k: v.translation for k, v in identifier_map.items()}
        print(f" ✓ Applied {updated} custom translations from template")
        if missing > 0:
            print(f" ⚠️ {missing} identifiers missing from template (using defaults)")
    else:
        # Fall back to original behavior
        identifier_map = se.StringExtractor.load_identifier_dictionary(dict_path)
    
    if not identifier_map:
        print(f" ✗ Error: No valid translations found in dictionary!")
        print(f"   Make sure you edited 'identifier_dictionary.txt'")
        return False
    
    print(f" ✓ Loaded {len(identifier_map)} translations")
    for chinese, english in sorted(identifier_map.items())[:10]:
        print(f"   {chinese} → {english}")
    if len(identifier_map) > 10:
        print(f"   ... and {len(identifier_map) - 10} more")
    
    print(f"\n📋 This will:")
    print(f"   1. Replace system identifiers in war3map.j code")
    print(f"   2. Apply HYBRID TRANSLATION for all .txt fields")
    print(f"   3. Identifiers detected in original → replaced in YOUR translations")
    print(f"\n⚠ Note: Your manual translations are PRESERVED with identifiers translated!")
    
    confirm = input("\n✅ Type 'yes' to proceed: ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return False
    
    os.makedirs(out_dir, exist_ok=True)
    
    # STEP 1: Update war3map.j
    print("="*70)
    print(f"STEP 1: Updating {jfile}...")
    print("="*70)
    
    create_backup(jfile)
    
    with open(jfile, 'rb') as f:
        j_data = f.read()
    
    j_data_translated, replacements = se.StringExtractor.replace_identifiers_in_code(j_data, identifier_map, verbose=True)

    
    j_output = os.path.join(out_dir, os.path.basename(jfile))
    with open(j_output, 'wb') as f:
        f.write(j_data_translated)
    
    print(f" ✓ Updated war3map.j saved to: {j_output}")
    
    # STEP 2: Update .txt files with HYBRID approach
    print("="*70)
    print(f"STEP 2: Updating item/unit .txt files (HYBRID translation)...")
    print("="*70)
    
    txt_updated = 0
    
    for txt_file in txtfiles:
        if not os.path.exists(txt_file):
            continue
        
        base_name = os.path.basename(txt_file)
        print(f"\n📝 Processing {base_name}...")
        
        json_file = os.path.join(tokens_dir, f"{base_name}.json")
        translated_txt = os.path.join(tokens_dir, f"{base_name}_chinese.txt")
        
        if not os.path.exists(json_file):
            print(f" ⚠ No extraction data found, skipping...")
            continue
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                extractions = json.load(f)
            
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Load manual translations if they exist
            line_map = {}
            if os.path.exists(translated_txt):
                with open(translated_txt, 'r', encoding='utf-8', newline=None) as f:
                    trans_content = f.read()
                
                trans_lines = trans_content.split('\n')
                current_num = None
                current_text = []
                
                for line in trans_lines:
                    match = re.match(r'^(\d+)\.\s*(.*)', line)
                    if match:
                        if current_num is not None:
                            line_map[current_num] = '\n'.join(current_text)
                        current_num = int(match.group(1))
                        current_text = [match.group(2)]
                    elif current_num is not None and line.strip():
                        current_text.append(line.rstrip())
                
                if current_num is not None:
                    line_map[current_num] = '\n'.join(current_text)
            else:
                print(f" ℹ No manual translations found, using identifier-only mode...")
            
            lines = content.split('\n')
            identifier_priority_count = 0
            normal_translation_count = 0
            
            for idx, extract in enumerate(extractions):
                original_chinese = extract.get('original', '')
                
                # HYBRID APPROACH: Apply identifier replacements to manual translation
                if idx + 1 in line_map:
                    # Have manual translation
                    translation = line_map[idx + 1]
                    
                    # Check if original contains identifiers
                    found_idents = [ident for ident in identifier_map.keys() if ident in original_chinese]
                    
                    if found_idents:
                        # Apply identifier translations TO the manual translation
                        translation, replaced = se.StringExtractor.apply_identifiers_to_translation(
                            original_chinese,
                            translation,
                            identifier_map
                        )
                        identifier_priority_count += 1
                    else:
                        # No identifiers, use manual translation as-is
                        normal_translation_count += 1
                else:
                    # No manual translation, just replace identifiers in original
                    translation, _ = se.StringExtractor.replace_identifiers_in_text(original_chinese, identifier_map)

                
                # Apply the translation
                line_idx = extract['line'] - 1
                if line_idx < len(lines):
                    key = extract['key']
                    is_custom_box = extract.get('custom_box', False)
                    
                    if extract['format'] == 'unquoted':
                        if is_custom_box and translation and not translation.startswith('"'):
                            new_line = f'{key}="{translation}"'
                        else:
                            new_line = f'{key}={translation}'
                    else:
                        new_line = f'{key}="{translation}"'
                    
                    lines[line_idx] = new_line
            
            content = '\n'.join(lines)
            output_file = os.path.join(out_dir, base_name)
            
            with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            
            print(f" ✓ Saved to: {output_file}")
            print(f"   {identifier_priority_count} fields with hybrid translation")
            print(f"   {normal_translation_count} fields with manual translation only")
            txt_updated += 1
        
        except Exception as e:
            print(f" ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # SUMMARY
    print("="*70)
    print("SYNCHRONIZED TRANSLATION COMPLETE!")
    print("="*70)
    print(f" ✓ {len(identifier_map)} system identifiers defined")
    print(f" ✓ {txt_updated} .txt files updated")
    print(f" ✓ 1 war3map.j file updated")
    print(f" 📁 Output directory: {out_dir}")
    print(f" 💾 Backups saved in: backups/")
    print(f"\n📋 HYBRID MODE:")
    print(f"   - Identifiers found in original → replaced in YOUR translations")
    print(f"   - Your manual translations are PRESERVED!")
    print(f"   - Ensures consistency with war3map.j code!")
    
    return True

def main():
    """Enhanced main interface with system identifier and dependency support."""
    txt_files = [
        "CampaignAbilityStrings.txt",
        "CampaignUnitStrings.txt",
        "Itemstrings.txt",
        "CommonAbilityStrings.txt",
        "CampaignUpgradeStrings.txt",
        "ItemAbilityStrings.txt"
    ]
    j_file = "war3map.j"
    
    print("=" * 70)
    print(" Warcraft III Map Translation Tool v8.0 - Dependency Support")
    print("=" * 70)
    
    if STRING_EXTRACTOR_AVAILABLE:
        print(" ✓ stringextractor.py loaded - Mode 3 & 4 available")
    else:
        print(" ⚠️ stringextractor.py not found - Mode 3 & 4 disabled")
    
    print()
    
    while True:
        print("Available modes:")
        print(" 1) extract   - Extract Chinese text & Detect system identifiers")
        print(" 2) translate - Standard translation (preserves identifiers)")
        if STRING_EXTRACTOR_AVAILABLE:
            print(" 3) sync      - Synchronized translation (translates identifiers)")
            print(" 4) depsync   - Dependency-aware synchronized translation")
        print(" 5) quit      - Exit")
        print()
        
        mode = input("Select mode (1-5): ").strip().lower()
        
        if mode in ('5', 'quit', 'exit', 'q'):
            print("👋 Goodbye!")
            break
        
        if mode in ('1', 'extract'):
            print("--- EXTRACTION MODE ---")
            output_dir = input("Output directory [chinese_tokens_folder]: ").strip() or "chinese_tokens_folder"
            
            # CREATE OUTPUT DIRECTORY
            os.makedirs(output_dir, exist_ok=True)
            print(f" ✓ Created/verified directory: {output_dir}")
            
            custombox_input = input("Preserve custom box formatting? (y/n) [y]: ").strip().lower()
            preserve_custom = custombox_input in ('y', 'yes', '')
            
            # Extract from .txt files
            print("\n📄 Extracting from .txt files...")
            txt_count = extract_chinese_tokens(txt_files, output_dir, preserve_custom)
            
            # Extract from war3map.j
            print("\n📄 Extracting from war3map.j...")
            restrict_input = input("Restrict to UI text only? (y/n) [y]: ").strip().lower()
            restrict = restrict_input in ('y', 'yes', '')
            
            detect_ids = STRING_EXTRACTOR_AVAILABLE
            if detect_ids:
                detect_input = input("Detect system identifiers? (y/n) [y]: ").strip().lower()
                detect_ids = detect_input in ('y', 'yes', '')
            
            success = extract_war3map_j(j_file, output_dir, restrict_ui=restrict, 
                                        detect_identifiers=detect_ids)
            
            if success:
                print("=" * 70)
                print(" EXTRACTION COMPLETE")
                print("=" * 70)
                print(" Next steps:")
                print(" 1. Review 'identifier_dictionary.txt' if generated")
                print(" 2. Edit translations in opened files")
                print(" 3. Run Mode 2 (preserve IDs), Mode 3 (translate IDs), or Mode 4 (sync deps)")
                print()
            else:
                print("❌ Extraction failed.")
        
        elif mode in ('2', 'translate'):
            print("--- MODE 2: STANDARD TRANSLATION ---")
            print("Preserves Chinese identifiers, translates descriptions")
            
            tokens_dir = input("Tokens directory [chinese_tokens_folder]: ").strip() or "chinese_tokens_folder"
            output_dir = input("Output directory [translated_files]: ").strip() or "translated_files"
            
            if not os.path.exists(tokens_dir):
                print(f" ✗ Error: {tokens_dir} not found!")
                continue
            
            # CREATE OUTPUT DIRECTORY
            os.makedirs(output_dir, exist_ok=True)
            print(f" ✓ Created/verified directory: {output_dir}")
            
            # .txt translations
            print("\n📥 Inserting translations...")
            txt_count = insert_translations_txt(txt_files, tokens_dir, output_dir)
            
            # war3map.j translation with IDENTIFIER PRESERVATION
            autofix = input("Enable auto-fix? (y/n) [y]: ").strip().lower() in ('y', 'yes', '')
            use_utf8 = input("UTF-8 output? (y/n) [y]: ").strip().lower() in ('y', 'yes', '')
            gen_report = input("Generate report? (y/n) [y]: ").strip().lower() in ('y', 'yes', '')
            
            success = reinsert_war3map_j(j_file, tokens_dir, output_dir, 
                                          write_utf8=use_utf8, 
                                          generate_report=gen_report, 
                                          auto_fix=autofix,
                                          preserve_identifiers=True)
            
            if success:
                print(f"\n✅ Translation complete! Identifiers preserved in Chinese.")
        
        elif mode in ('3', 'sync', 'synchronized'):
            if not STRING_EXTRACTOR_AVAILABLE:
                print("❌ Mode 3 requires stringextractor.py")
                continue
            
            print("--- MODE 3: SYNCHRONIZED TRANSLATION ---")
            tokens_dir = input("Tokens directory [chinese_tokens_folder]: ").strip() or "chinese_tokens_folder"
            output_dir = input("Output directory [synchronized_files]: ").strip() or "synchronized_files"
            
            # CREATE OUTPUT DIRECTORY
            os.makedirs(output_dir, exist_ok=True)
            print(f" ✓ Created/verified directory: {output_dir}")
            
            synchronized_translation_mode(j_file, txt_files, tokens_dir, output_dir)
        
        elif mode in ('4', 'depsync', 'dependency'):
            if not STRING_EXTRACTOR_AVAILABLE:
                print("❌ Mode 4 requires stringextractor.py")
                continue
            
            print("--- MODE 4: DEPENDENCY-AWARE TRANSLATION ---")
            print("Ensures critical strings match between JASS and text files")
            
            tokens_dir = input("Tokens directory [chinese_tokens_folder]: ").strip() or "chinese_tokens_folder"
            output_dir = input("Output directory [synced_files]: ").strip() or "synced_files"
            
            if not os.path.exists(tokens_dir):
                print(f" ✗ Error: {tokens_dir} not found!")
                continue
            
            # CREATE OUTPUT DIRECTORY
            os.makedirs(output_dir, exist_ok=True)
            print(f" ✓ Created/verified directory: {output_dir}")
            
            mode4_synchronized_dependency_translation(j_file, txt_files, tokens_dir, output_dir)
        
        else:
            print("❌ Invalid mode.")

if __name__ == "__main__":
    main()