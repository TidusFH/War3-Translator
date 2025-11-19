"""
Campaign Translator Module
Warcraft III Campaign (.w3n) Translation Tool with Google Translate API
Supports multi-language translation with automatic backup and protection detection
"""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import configparser

# Try to import free googletrans (no API key needed)
try:
    from googletrans import Translator as FreeTranslator
    FREE_TRANSLATE_AVAILABLE = True
except ImportError:
    FREE_TRANSLATE_AVAILABLE = False

# Try to import official Google Cloud Translation API (API key needed)
try:
    from google.cloud import translate_v2 as translate
    CLOUD_TRANSLATE_AVAILABLE = True
except ImportError:
    CLOUD_TRANSLATE_AVAILABLE = False

GOOGLE_TRANSLATE_AVAILABLE = FREE_TRANSLATE_AVAILABLE or CLOUD_TRANSLATE_AVAILABLE

if not GOOGLE_TRANSLATE_AVAILABLE:
    print("⚠️ Warning: No translation library installed.")
    print("   Option 1 (Free): pip install googletrans==4.0.0rc1")
    print("   Option 2 (Official): pip install google-cloud-translate")

# Language code mapping
LANGUAGE_CODES = {
    'chinese': 'zh-cn',
    'english': 'en',
    'russian': 'ru',
    'korean': 'ko',
    'spanish': 'es',
    'portuguese': 'pt',
    'japanese': 'ja'
}

class CampaignTranslator:
    """Handles translation of Warcraft III campaign files using Google Translate API."""

    def __init__(self, mpqcli_path: str = "mpqcli.exe", listfile_path: str = "Listfilesbasico.txt",
                 api_key: str = None):
        """
        Initialize the campaign translator.

        Args:
            mpqcli_path: Path to mpqcli.exe executable
            listfile_path: Path to the listfile for MPQ extraction
            api_key: Google Cloud API key (optional, for official API)
        """
        self.mpqcli_path = mpqcli_path
        self.listfile_path = listfile_path
        self.api_key = api_key or self._load_api_key()
        self.use_cloud_api = False
        self.translator = None

        # Initialize translator
        if self.api_key and CLOUD_TRANSLATE_AVAILABLE:
            # Use official Google Cloud Translation API
            try:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.api_key
                self.translator = translate.Client()
                self.use_cloud_api = True
                print("✓ Using Google Cloud Translation API (Official)")
            except Exception as e:
                print(f"⚠️ Failed to initialize Cloud API: {e}")
                print("   Falling back to free translator...")
                if FREE_TRANSLATE_AVAILABLE:
                    self.translator = FreeTranslator()
                    self.use_cloud_api = False
        elif FREE_TRANSLATE_AVAILABLE:
            # Use free googletrans
            self.translator = FreeTranslator()
            self.use_cloud_api = False
            print("✓ Using free Google Translate (no API key)")
        else:
            print("❌ No translation service available")

        # Ensure required directories exist
        self.backup_dir = Path("backup")
        self.protected_dir = Path("protected")
        self.translated_dir = Path("translated")

        for directory in [self.backup_dir, self.protected_dir, self.translated_dir]:
            directory.mkdir(exist_ok=True)

    def _load_api_key(self) -> Optional[str]:
        """
        Load API key from config.ini file.

        Returns:
            API key string or None
        """
        config_file = Path("config.ini")
        if not config_file.exists():
            return None

        try:
            config = configparser.ConfigParser()
            config.read(config_file)

            if 'GoogleTranslate' in config and 'api_key' in config['GoogleTranslate']:
                api_key = config['GoogleTranslate']['api_key'].strip()
                if api_key and api_key != 'YOUR_API_KEY_HERE':
                    return api_key

            if 'GoogleTranslate' in config and 'credentials_path' in config['GoogleTranslate']:
                cred_path = config['GoogleTranslate']['credentials_path'].strip()
                if cred_path and os.path.exists(cred_path):
                    return cred_path

        except Exception as e:
            print(f"⚠️ Error reading config.ini: {e}")

        return None

    def translate_text(self, text: str, src_lang: str, dest_lang: str, max_retries: int = 3) -> str:
        """
        Translate text using Google Translate API with retry logic.

        Args:
            text: Text to translate
            src_lang: Source language code
            dest_lang: Destination language code
            max_retries: Maximum number of retry attempts

        Returns:
            Translated text or original text if translation fails
        """
        if not GOOGLE_TRANSLATE_AVAILABLE or not self.translator:
            print("❌ Google Translate not available")
            return text

        if not text.strip():
            return text

        for attempt in range(max_retries):
            try:
                if self.use_cloud_api:
                    # Official Google Cloud API
                    result = self.translator.translate(
                        text,
                        source_language=src_lang,
                        target_language=dest_lang
                    )
                    return result['translatedText']
                else:
                    # Free googletrans
                    result = self.translator.translate(text, src=src_lang, dest=dest_lang)
                    return result.text
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"⚠️ Translation error (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Translation failed after {max_retries} attempts: {e}")
                    return text

        return text

    def parse_wts_file(self, wts_path: str) -> Dict[str, str]:
        """
        Parse a .wts (World Editor Trigger Strings) file.

        Format:
        STRING 1
        {
        Original text here
        }

        Args:
            wts_path: Path to the .wts file

        Returns:
            Dictionary mapping string IDs to their content
        """
        strings = {}

        try:
            with open(wts_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try different encodings
            encodings = ['utf-8', 'gb18030', 'gbk', 'gb2312', 'big5', 'shift-jis', 'euc-kr']
            for enc in encodings:
                try:
                    with open(wts_path, 'r', encoding=enc, errors='ignore') as f:
                        content = f.read()
                    break
                except:
                    continue

        # Parse STRING entries
        pattern = r'STRING\s+(\d+)\s*\n\s*\{\s*\n(.*?)\n\s*\}'
        matches = re.finditer(pattern, content, re.DOTALL | re.MULTILINE)

        for match in matches:
            string_id = match.group(1)
            string_content = match.group(2).strip()
            strings[string_id] = string_content

        return strings

    def write_wts_file(self, wts_path: str, strings: Dict[str, str]):
        """
        Write translated strings back to a .wts file.

        Args:
            wts_path: Path to the output .wts file
            strings: Dictionary mapping string IDs to their content
        """
        with open(wts_path, 'w', encoding='utf-8') as f:
            for string_id in sorted(strings.keys(), key=int):
                f.write(f"STRING {string_id}\n")
                f.write("{\n")
                f.write(f"{strings[string_id]}\n")
                f.write("}\n\n")

    def translate_wts_file(self, wts_path: str, output_path: str, src_lang: str, dest_lang: str) -> int:
        """
        Translate a .wts file from source language to destination language.

        Args:
            wts_path: Path to the input .wts file
            output_path: Path to the output translated .wts file
            src_lang: Source language code
            dest_lang: Destination language code

        Returns:
            Number of strings translated
        """
        print(f"   📖 Reading {Path(wts_path).name}...")
        strings = self.parse_wts_file(wts_path)

        if not strings:
            print(f"   ⚠️ No strings found in {Path(wts_path).name}")
            return 0

        print(f"   🔤 Found {len(strings)} strings to translate")
        translated_strings = {}

        for idx, (string_id, content) in enumerate(strings.items(), 1):
            print(f"   [{idx}/{len(strings)}] Translating STRING {string_id}...", end='\r')
            translated_content = self.translate_text(content, src_lang, dest_lang)
            translated_strings[string_id] = translated_content

            # Small delay to avoid rate limiting
            if idx % 10 == 0:
                time.sleep(0.5)

        print(f"\n   ✅ Translated {len(translated_strings)} strings")

        # Write translated file
        self.write_wts_file(output_path, translated_strings)
        print(f"   💾 Saved to {output_path}")

        return len(translated_strings)

    def run_mpqcli(self, args: List[str]) -> Tuple[bool, str]:
        """
        Run mpqcli.exe with given arguments.

        Args:
            args: List of command-line arguments

        Returns:
            Tuple of (success, output)
        """
        try:
            cmd = [self.mpqcli_path] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "MPQ operation timed out"
        except Exception as e:
            return False, str(e)

    def extract_mpq(self, mpq_path: str, output_dir: str, file_pattern: str = "*") -> bool:
        """
        Extract files from an MPQ archive.

        Args:
            mpq_path: Path to the MPQ archive
            output_dir: Directory to extract files to
            file_pattern: Pattern of files to extract (default: all files)

        Returns:
            True if extraction succeeded
        """
        print(f"   📦 Extracting {Path(mpq_path).name}...")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Use listfile if available
        args = ['extract', mpq_path, file_pattern, '-o', output_dir]
        if os.path.exists(self.listfile_path):
            args.extend(['-f', self.listfile_path])

        success, output = self.run_mpqcli(args)

        if success:
            print(f"   ✅ Extracted to {output_dir}")
        else:
            print(f"   ⚠️ Extraction may have failed: {output}")

        return success

    def create_mpq(self, source_dir: str, mpq_path: str) -> bool:
        """
        Create an MPQ archive from a directory.

        Args:
            source_dir: Directory containing files to pack
            mpq_path: Path to output MPQ archive

        Returns:
            True if creation succeeded
        """
        print(f"   📦 Creating {Path(mpq_path).name}...")

        # Use listfile if available
        args = ['create', mpq_path, source_dir]
        if os.path.exists(self.listfile_path):
            args.extend(['-f', self.listfile_path])

        success, output = self.run_mpqcli(args)

        if success:
            print(f"   ✅ Created {mpq_path}")
        else:
            print(f"   ❌ Failed to create MPQ: {output}")

        return success

    def is_protected_map(self, map_dir: str) -> bool:
        """
        Check if a map is protected (missing important files).

        Args:
            map_dir: Directory containing extracted map files

        Returns:
            True if the map appears to be protected
        """
        # Check for common files that should exist in unprotected maps
        important_files = ['war3map.j', 'war3map.w3i', 'war3map.w3e']

        for file in important_files:
            if not os.path.exists(os.path.join(map_dir, file)):
                return True

        return False

    def translate_campaign(self, campaign_path: str, src_lang: str, dest_lang: str):
        """
        Translate a Warcraft III campaign file (.w3n).

        Args:
            campaign_path: Path to the .w3n campaign file
            src_lang: Source language code
            dest_lang: Destination language code
        """
        if not GOOGLE_TRANSLATE_AVAILABLE:
            print("❌ Google Translate is not available. Install with: pip install googletrans==4.0.0rc1")
            return

        campaign_file = Path(campaign_path)
        if not campaign_file.exists():
            print(f"❌ Campaign file not found: {campaign_path}")
            return

        print(f"\n{'='*70}")
        print(f"🌍 Translating Campaign: {campaign_file.name}")
        print(f"   {src_lang.upper()} → {dest_lang.upper()}")
        print(f"{'='*70}\n")

        # Create backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{campaign_file.stem}_{timestamp}{campaign_file.suffix}"
        shutil.copy2(campaign_path, backup_path)
        print(f"💾 Backup created: {backup_path}")

        # Create working directory
        work_dir = Path(f"temp_{campaign_file.stem}_{timestamp}")
        work_dir.mkdir(exist_ok=True)

        try:
            # Extract campaign
            print(f"\n📂 Step 1: Extracting campaign archive...")
            campaign_extract_dir = work_dir / "campaign"
            self.extract_mpq(str(campaign_path), str(campaign_extract_dir))

            # Translate war3campaign.wts if it exists
            campaign_wts = campaign_extract_dir / "war3campaign.wts"
            if campaign_wts.exists():
                print(f"\n📝 Step 2: Translating war3campaign.wts...")
                translated_campaign_wts = campaign_extract_dir / "war3campaign.wts"
                self.translate_wts_file(
                    str(campaign_wts),
                    str(translated_campaign_wts),
                    LANGUAGE_CODES[src_lang],
                    LANGUAGE_CODES[dest_lang]
                )

            # Find all .w3x and .w3m map files in the campaign
            print(f"\n📂 Step 3: Processing map files...")
            map_files = list(campaign_extract_dir.glob("*.w3x")) + list(campaign_extract_dir.glob("*.w3m"))

            for map_file in map_files:
                print(f"\n   🗺️  Processing: {map_file.name}")

                # Extract map
                map_extract_dir = work_dir / f"map_{map_file.stem}"
                self.extract_mpq(str(map_file), str(map_extract_dir))

                # Check if protected
                is_protected = self.is_protected_map(str(map_extract_dir))

                if is_protected:
                    print(f"   🔒 Map is protected - backing up to protected folder")
                    protected_path = self.protected_dir / map_file.name
                    shutil.copy2(map_file, protected_path)

                # Translate war3map.wts if it exists
                map_wts = map_extract_dir / "war3map.wts"
                if map_wts.exists():
                    print(f"   📝 Translating war3map.wts...")
                    self.translate_wts_file(
                        str(map_wts),
                        str(map_wts),  # Overwrite in place
                        LANGUAGE_CODES[src_lang],
                        LANGUAGE_CODES[dest_lang]
                    )

                    # Repack map
                    print(f"   📦 Repacking map...")
                    self.create_mpq(str(map_extract_dir), str(map_file))
                else:
                    print(f"   ⚠️ No war3map.wts found in {map_file.name}")

            # Repack campaign
            print(f"\n📦 Step 4: Repacking campaign...")
            translated_campaign_path = self.translated_dir / campaign_file.name
            self.create_mpq(str(campaign_extract_dir), str(translated_campaign_path))

            print(f"\n{'='*70}")
            print(f"✅ Translation Complete!")
            print(f"{'='*70}")
            print(f"📁 Original backup: {backup_path}")
            print(f"🌍 Translated file: {translated_campaign_path}")
            print(f"{'='*70}\n")

        except Exception as e:
            print(f"\n❌ Error during translation: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Cleanup working directory
            if work_dir.exists():
                try:
                    shutil.rmtree(work_dir)
                    print(f"🧹 Cleaned up temporary files")
                except:
                    print(f"⚠️ Could not remove temporary directory: {work_dir}")


def show_language_menu() -> Tuple[str, str]:
    """
    Display language selection menu and return source and destination languages.

    Returns:
        Tuple of (source_language, destination_language)
    """
    print("\n" + "="*70)
    print("LANGUAGE SELECTION")
    print("="*70)
    print("Available languages:")
    print("  1) Chinese (Simplified)")
    print("  2) English")
    print("  3) Russian")
    print("  4) Korean")
    print("  5) Spanish")
    print("  6) Portuguese")
    print("  7) Japanese")
    print()

    lang_map = {
        '1': 'chinese',
        '2': 'english',
        '3': 'russian',
        '4': 'korean',
        '5': 'spanish',
        '6': 'portuguese',
        '7': 'japanese'
    }

    # Source language
    while True:
        src = input("Select SOURCE language (1-7): ").strip()
        if src in lang_map:
            src_lang = lang_map[src]
            break
        print("❌ Invalid selection. Please choose 1-7.")

    # Destination language
    while True:
        dest = input("Select DESTINATION language (1-7): ").strip()
        if dest in lang_map:
            dest_lang = lang_map[dest]
            if dest_lang == src_lang:
                print("⚠️ Source and destination languages are the same. Please choose different languages.")
                continue
            break
        print("❌ Invalid selection. Please choose 1-7.")

    return src_lang, dest_lang


def campaign_translation_mode():
    """Main function for campaign translation mode."""
    print("\n" + "="*70)
    print("CAMPAIGN TRANSLATION MODE")
    print("="*70)
    print("This mode translates Warcraft III campaign files (.w3n)")
    print("using Google Translate API.")
    print()

    if not GOOGLE_TRANSLATE_AVAILABLE:
        print("❌ Google Translate is not installed!")
        print("   Install with: pip install googletrans==4.0.0rc1")
        return

    # Get language selection
    src_lang, dest_lang = show_language_menu()

    print(f"\n✓ Translation: {src_lang.upper()} → {dest_lang.upper()}")

    # Get campaign file path
    campaign_path = input("\nEnter path to .w3n campaign file: ").strip().strip('"')

    if not campaign_path:
        print("❌ No file path provided.")
        return

    # Initialize translator and run
    translator = CampaignTranslator()
    translator.translate_campaign(campaign_path, src_lang, dest_lang)


if __name__ == "__main__":
    campaign_translation_mode()
