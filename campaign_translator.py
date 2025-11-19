"""
Campaign Translator Module
Warcraft III Campaign (.w3n) Translation Tool
Supports Google Translate and LLM (OpenAI/OpenRouter)
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

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Import custom modules
try:
    from llm_translator import LLMTranslator
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

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
    """Handles translation of Warcraft III campaign files."""

    def __init__(self, mpqcli_path: str = "mpqcli.exe", listfile_path: str = "Listfilesbasico.txt", verbose: bool = True):
        """
        Initialize the campaign translator.

        Args:
            mpqcli_path: Path to mpqcli.exe
            listfile_path: Path to listfile for MPQ operations
            verbose: Enable verbose debugging output
        """
        self.mpqcli_path = mpqcli_path
        self.listfile_path = listfile_path
        self.verbose = verbose
        self.config = self._load_config()
        self.engine = 'google'
        if self.config and self.config.has_section('General'):
            try:
                self.engine = self.config.get('General', 'engine', fallback='google').strip().lower()
            except (configparser.NoSectionError, configparser.NoOptionError):
                self.engine = 'google'
        elif os.getenv("TRANSLATE_ENGINE"):
            self.engine = os.getenv("TRANSLATE_ENGINE").strip().lower()
        self.google_translator = None
        self.llm_translator = None

        self._init_translators()

        # Ensure required directories exist
        self.backup_dir = Path("backup")
        self.protected_dir = Path("protected")
        self.translated_dir = Path("translated")

        for directory in [self.backup_dir, self.protected_dir, self.translated_dir]:
            directory.mkdir(exist_ok=True)
            if self.verbose:
                print(f"📁 Directory ensured: {directory.absolute()}")

    def _load_config(self) -> configparser.ConfigParser:
        """Load configuration from config.ini."""
        config = configparser.ConfigParser()
        config_file = Path("config.ini")
        if config_file.exists():
            config.read(config_file)
        return config

    def _init_translators(self):
        """Initialize translation engines based on config."""
        # Initialize Google Translate first (or if LLM not available)
        if self.engine == 'google' or not LLM_AVAILABLE:
            self._init_google_translator()
            if self.engine == 'google' and not self.google_translator and LLM_AVAILABLE:
                print("⚠️ Google translator unavailable. Switching to LLM engine.")
                self.engine = 'llm'
        
        # Initialize LLM Translator
        if self.engine == 'llm' and LLM_AVAILABLE:
            try:
                self.llm_translator = LLMTranslator()
                if not self.llm_translator.client:
                    print("⚠️ LLM initialization failed. Falling back to Google.")
                    self.engine = 'google'
                    self._init_google_translator()
            except Exception as e:
                print(f"⚠️ LLM Error: {e}")
                self.engine = 'google'
                self._init_google_translator()
        elif self.engine == 'llm' and not LLM_AVAILABLE:
            print("⚠️ LLM engine requested but llm_translator.py is unavailable. Falling back to Google.")
            self.engine = 'google'
            self._init_google_translator()

    def _init_google_translator(self):
        """Initialize Google Translator (Cloud or Free)."""
        api_key = None
        if self.config and self.config.has_section('GoogleTranslate'):
            api_key = self.config['GoogleTranslate'].get('api_key')
        
        if api_key and api_key != 'YOUR_API_KEY_HERE' and CLOUD_TRANSLATE_AVAILABLE:
            try:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = api_key
                self.google_translator = translate.Client()
                self.use_cloud_api = True
                print("✓ Using Google Cloud Translation API (Official)")
            except Exception as e:
                print(f"⚠️ Failed to initialize Cloud API: {e}")
                self._init_free_google()
        else:
            self._init_free_google()

    def _init_free_google(self):
        """Initialize free googletrans."""
        if FREE_TRANSLATE_AVAILABLE:
            self.google_translator = FreeTranslator()
            self.use_cloud_api = False
            print("✓ Using free Google Translate (no API key)")
        else:
            print("❌ No Google Translate library available. Install with 'pip install googletrans==4.0.0rc1'.")

    def translate_text(self, text: str, src_lang: str, dest_lang: str) -> str:
        """Translate text using the selected engine."""
        if not text.strip():
            return text

        if self.engine == 'llm' and self.llm_translator:
            return self.llm_translator.translate_text(text, src_lang, dest_lang)
        
        # Fallback to Google
        return self._translate_google(text, src_lang, dest_lang)

    def _translate_google(self, text: str, src_lang: str, dest_lang: str, max_retries: int = 3) -> str:
        """Translate using Google API."""
        if not self.google_translator:
            return text

        for attempt in range(max_retries):
            try:
                if self.use_cloud_api:
                    result = self.google_translator.translate(
                        text, source_language=src_lang, target_language=dest_lang
                    )
                    return result['translatedText']
                else:
                    result = self.google_translator.translate(text, src=src_lang, dest=dest_lang)
                    return result.text
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"❌ Translation failed: {e}")
                    return text
        return text

    def parse_wts_file(self, wts_path: str) -> Dict[str, str]:
        """Parse a .wts file."""
        strings = {}
        try:
            with open(wts_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return {}

        pattern = r'STRING\s+(\d+)\s*\n\s*\{\s*\n(.*?)\n\s*\}'
        matches = re.finditer(pattern, content, re.DOTALL | re.MULTILINE)

        for match in matches:
            strings[match.group(1)] = match.group(2).strip()
        return strings

    def write_wts_file(self, wts_path: str, strings: Dict[str, str]):
        """Write translated strings back to a .wts file."""
        with open(wts_path, 'w', encoding='utf-8') as f:
            for string_id in sorted(strings.keys(), key=int):
                f.write(f"STRING {string_id}\n{{\n{strings[string_id]}\n}}\n\n")

    def translate_wts_file(self, wts_path: str, output_path: str, src_lang: str, dest_lang: str) -> int:
        """Translate a .wts file."""
        print(f"   📖 Reading {Path(wts_path).name}...")
        strings = self.parse_wts_file(wts_path)

        if not strings:
            print(f"   ⚠️ No strings found in {Path(wts_path).name}")
            return 0

        print(f"   🔤 Found {len(strings)} strings to translate")
        translated_strings = {}

        # Use batch translation for LLM if possible
        if self.engine == 'llm' and self.llm_translator:
            keys = list(strings.keys())
            values = list(strings.values())
            batch_size = 20
            
            iterator = range(0, len(keys), batch_size)
            if TQDM_AVAILABLE:
                iterator = tqdm(iterator, desc="Translating batches", unit="batch")
            
            for i in iterator:
                batch_keys = keys[i:i+batch_size]
                batch_values = values[i:i+batch_size]
                
                translated_batch = self.llm_translator.translate_batch(
                    batch_values, src_lang, dest_lang, context="Warcraft III Campaign Text"
                )
                
                for k, v in zip(batch_keys, translated_batch):
                    translated_strings[k] = v
        else:
            # Sequential translation for Google
            items = strings.items()
            if TQDM_AVAILABLE:
                items = tqdm(items, desc="Translating strings", unit="str")
            
            for string_id, content in items:
                translated_strings[string_id] = self.translate_text(content, src_lang, dest_lang)
                if not TQDM_AVAILABLE and int(string_id) % 10 == 0:
                    print(f"   Translating... {string_id}", end='\r')

        self.write_wts_file(output_path, translated_strings)
        print(f"   💾 Saved to {output_path}")
        return len(translated_strings)

    def run_mpqcli(self, args: List[str]) -> Tuple[bool, str]:
        """Run mpqcli.exe and return success flag with combined output."""
        if not os.path.exists(self.mpqcli_path):
            message = f"mpqcli.exe not found at '{self.mpqcli_path}'"
            print(f"❌ {message}")
            return False, message

        cmd = [self.mpqcli_path] + args

        if self.verbose:
            # Show command for debugging
            cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)
            print(f"🔧 Running: {cmd_str}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            output = (result.stdout or "") + (result.stderr or "")

            if self.verbose:
                print(f"   Return code: {result.returncode}")
                if output.strip():
                    print(f"   Output: {output.strip()}")

            return result.returncode == 0, output.strip()
        except FileNotFoundError:
            message = f"mpqcli.exe could not be executed (FileNotFoundError). Tried command: {' '.join(cmd)}"
            print(f"❌ {message}")
            return False, message
        except subprocess.TimeoutExpired:
            message = f"mpqcli.exe timed out (300s). Command: {' '.join(cmd)}"
            print(f"❌ {message}")
            return False, message
        except Exception as e:
            message = f"Unexpected error running mpqcli: {e}"
            print(f"❌ {message}")
            import traceback
            if self.verbose:
                traceback.print_exc()
            return False, message

    def extract_mpq(self, mpq_path: str, output_dir: str) -> bool:
        """Extract MPQ archive."""
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        if self.verbose:
            print(f"   Source MPQ: {os.path.abspath(mpq_path)}")
            print(f"   Output dir: {os.path.abspath(output_dir)}")
            print(f"   MPQ exists: {os.path.exists(mpq_path)}")
            print(f"   Output dir exists: {os.path.exists(output_dir)}")

        args = ['extract', mpq_path, '-o', output_dir]
        if os.path.exists(self.listfile_path):
            args.extend(['-f', self.listfile_path])

        success, output = self.run_mpqcli(args)
        if not success:
            print("❌ MPQ extraction failed.")
            print(f"   Command: {' '.join([self.mpqcli_path] + args)}")
            if output:
                for line in output.splitlines():
                    print(f"   → {line}")
        return success

    def create_mpq(self, source_dir: str, mpq_path: str) -> bool:
        """Create MPQ archive."""
        # Ensure the parent directory of the target MPQ exists
        mpq_path_obj = Path(mpq_path)
        if mpq_path_obj.parent != Path('.'):
            mpq_path_obj.parent.mkdir(parents=True, exist_ok=True)

        if self.verbose:
            print(f"   Source dir: {os.path.abspath(source_dir)}")
            print(f"   Target MPQ: {os.path.abspath(mpq_path)}")
            print(f"   Source exists: {os.path.exists(source_dir)}")
            print(f"   Parent dir exists: {mpq_path_obj.parent.exists()}")
            if os.path.exists(source_dir):
                files = list(Path(source_dir).rglob('*'))
                print(f"   Files in source: {len(files)}")
                if len(files) <= 10:
                    for f in files:
                        print(f"      - {f.relative_to(source_dir)}")

        args = ['create', mpq_path, source_dir]
        if os.path.exists(self.listfile_path):
            args.extend(['-f', self.listfile_path])

        success, output = self.run_mpqcli(args)
        if not success:
            print("❌ MPQ creation failed.")
            print(f"   Command: {' '.join([self.mpqcli_path] + args)}")
            if output:
                for line in output.splitlines():
                    print(f"   → {line}")
        else:
            if self.verbose and os.path.exists(mpq_path):
                print(f"   ✅ MPQ created successfully: {os.path.getsize(mpq_path)} bytes")
        return success

    def translate_campaign(self, campaign_path: str, src_lang: str, dest_lang: str):
        """Translate a Warcraft III campaign file (.w3n)."""
        campaign_file = Path(campaign_path)
        if not campaign_file.exists():
            print(f"❌ Campaign file not found: {campaign_path}")
            return

        print(f"\n{'='*70}")
        print(f"🌍 Translating Campaign: {campaign_file.name}")
        print(f"   Engine: {self.engine.upper()}")
        print(f"   {src_lang.upper()} → {dest_lang.upper()}")
        print(f"{'='*70}\n")

        # Backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{campaign_file.stem}_{timestamp}{campaign_file.suffix}"
        shutil.copy2(campaign_path, backup_path)
        print(f"💾 Backup created: {backup_path}")

        work_dir = Path(f"temp_{campaign_file.stem}_{timestamp}")
        work_dir.mkdir(exist_ok=True)

        try:
            # Extract
            print(f"\n📂 Step 1: Extracting campaign...")
            campaign_extract_dir = work_dir / "campaign"
            if not self.extract_mpq(str(campaign_path), str(campaign_extract_dir)):
                print("❌ Failed to extract campaign.")
                return

            # Translate campaign strings
            campaign_wts = campaign_extract_dir / "war3campaign.wts"
            if campaign_wts.exists():
                print(f"\n📝 Step 2: Translating war3campaign.wts...")
                self.translate_wts_file(
                    str(campaign_wts), str(campaign_wts),
                    LANGUAGE_CODES.get(src_lang, 'zh-cn'),
                    LANGUAGE_CODES.get(dest_lang, 'en')
                )

            # Process maps
            print(f"\n📂 Step 3: Processing map files...")
            map_files = list(campaign_extract_dir.glob("*.w3x")) + list(campaign_extract_dir.glob("*.w3m"))
            
            for map_file in map_files:
                print(f"\n   🗺️  Processing: {map_file.name}")
                map_extract_dir = work_dir / f"map_{map_file.stem}"
                if not self.extract_mpq(str(map_file), str(map_extract_dir)):
                    print("   ❌ Failed to extract map archive. Skipping this map.")
                    continue

                map_wts = map_extract_dir / "war3map.wts"
                if map_wts.exists():
                    self.translate_wts_file(
                        str(map_wts), str(map_wts),
                        LANGUAGE_CODES.get(src_lang, 'zh-cn'),
                        LANGUAGE_CODES.get(dest_lang, 'en')
                    )
                    if not self.create_mpq(str(map_extract_dir), str(map_file)):
                        print("   ❌ Failed to repack map archive. See details above.")
                else:
                    print(f"   ⚠️ No war3map.wts found.")

            # Repack
            print(f"\n📦 Step 4: Repacking campaign...")
            translated_path = self.translated_dir / campaign_file.name
            if self.create_mpq(str(campaign_extract_dir), str(translated_path)):
                print(f"\n✅ Translation Complete! Saved to: {translated_path}")
            else:
                print("\n❌ Failed to repack campaign.")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)

def show_language_menu() -> Tuple[str, str]:
    """Display language selection menu."""
    print("\n" + "="*70)
    print("LANGUAGE SELECTION")
    print("="*70)
    langs = list(LANGUAGE_CODES.keys())
    for i, lang in enumerate(langs, 1):
        print(f"  {i}) {lang.title()}")
    
    def get_choice(prompt):
        while True:
            try:
                choice = int(input(prompt))
                if 1 <= choice <= len(langs):
                    return langs[choice-1]
            except ValueError:
                pass
            print("Invalid selection.")

    src = get_choice("Select SOURCE language (1-7): ")
    dest = get_choice("Select DESTINATION language (1-7): ")
    return src, dest

def _list_campaigns(campaign_dir: Path) -> List[Path]:
    """Return available .w3n campaigns inside campaign_dir."""
    if not campaign_dir.exists():
        campaign_dir.mkdir(parents=True, exist_ok=True)
    return sorted([p for p in campaign_dir.glob("*.w3n") if p.is_file()])


def campaign_translation_mode():
    """Main entry point."""
    src, dest = show_language_menu()
    campaign_dir = Path("campaign")
    available_campaigns = _list_campaigns(campaign_dir)

    path: Optional[str] = None

    if available_campaigns:
        print("\nAvailable campaigns in 'campaign/' folder:")
        for idx, campaign_path in enumerate(available_campaigns, start=1):
            print(f"  {idx}) {campaign_path.name}")
        print("  0) Provide custom path")

        while True:
            selection = input("Select campaign (number) or enter custom path: ").strip()
            if not selection:
                # default to first entry
                path = str(available_campaigns[0])
                break
            if selection.isdigit():
                index = int(selection)
                if index == 0:
                    break
                if 1 <= index <= len(available_campaigns):
                    path = str(available_campaigns[index - 1])
                    break
            else:
                # treat as custom path
                path = selection
                break
            print("Invalid selection. Try again.")

    if path is None:
        path = input("\nEnter path to .w3n campaign file: ").strip()

    path = path.strip().strip('"') if path else ""

    if path:
        translator = CampaignTranslator()
        translator.translate_campaign(path, src, dest)

if __name__ == "__main__":
    campaign_translation_mode()
