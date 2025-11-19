# Warcraft III Translation Tool

A comprehensive translation toolkit for Warcraft III maps and campaigns with support for multi-language translation, system identifier detection, Google Translate API, and **LLM (OpenAI/OpenRouter)** integration.

## 🌟 Features

### Map Translation (Modes 1-4)
- **Extract Chinese Text** - Extract and detect system identifiers from maps
- **Standard Translation** - Preserve identifiers while translating descriptions
- **Synchronized Translation** - Translate identifiers to standardize game terms
- **Dependency-Aware Translation** - Ensure critical strings match between JASS and text files

### 🆕 Auto-Translate (Mode 7)
- **LLM-Powered Translation** - Automatically translate extracted text files using OpenAI, Claude, or Gemini (via OpenRouter)
- **Context-Aware** - Provides context to the AI for better translation quality
- **Batch Processing** - Efficiently translates large files

### Campaign Translation (Mode 5)
- **Automatic Campaign Processing** - Translate entire .w3n campaign files
- **Dual Engine Support** - Use Google Translate or LLM
- **Multi-Language Support** - 7 languages supported:
  - Chinese (Simplified) ↔ English
  - Russian, Korean, Spanish, Portuguese, Japanese
- **Smart Backup System** - Automatic backups with protection detection
- **MPQ Archive Handling** - Extract, translate, and repack campaign archives

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Translation Modes](#translation-modes)
- [Configuration](#configuration)
- [Campaign Translation](#campaign-translation)
- [File Structure](#file-structure)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)

## 🚀 Installation

### 1. Clone or Download

```bash
git clone https://github.com/TidusFH/War3-Translator.git
cd War3-Translator
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Required packages:**
- `chardet` - Character encoding detection
- `ftfy` - Unicode text fixing
- `googletrans==4.0.0rc1` - Google Translate API (free version)
- `openai` - LLM support
- `tqdm` - Progress bars

### 3. Configuration

Copy the template and add your API keys:

```bash
copy config.ini.template config.ini
```

Edit `config.ini`:
- **[GoogleTranslate]**: Add API key for official Google Cloud translation (optional)
- **[LLM]**: Add API key for OpenAI or OpenRouter (recommended for best quality)
- **[General]**: Set preferred engine (`google` or `llm`)

### 4. Verify Files

Ensure these files are present:
- `translator2.py` - Main translation tool
- `stringextractor.py` - System identifier extraction
- `campaign_translator.py` - Campaign translation module
- `llm_translator.py` - LLM integration module
- `config_manager.py` - Configuration handler
- `mpqcli.exe` - MPQ archive tool
- `Listfilesbasico.txt` - MPQ file listing
- `data/` - Configuration files (system identifiers, patterns)

## 🎯 Quick Start

### Basic Usage

```bash
python translator2.py
```

You'll see a menu with available modes:

```
======================================================================
 Warcraft III Map Translation Tool v9.0 - LLM & Config Support
======================================================================
 ✓ stringextractor.py loaded - Mode 3 & 4 available
 ✓ campaign_translator.py loaded - Mode 5 (Campaign) available
 ✓ llm_translator.py loaded - Mode 7 (Auto-Translate) available

Available modes:
 1) extract   - Extract Chinese text & Detect system identifiers
 2) translate - Standard translation (preserves identifiers)
 3) sync      - Synchronized translation (translates identifiers)
 4) depsync   - Dependency-aware synchronized translation
 5) campaign  - Campaign translation (.w3n)
 7) auto      - Auto-translate extracted files (LLM)
 6) quit      - Exit

Select mode (1-7):
```

### Example: Auto-Translate a Map

1. **Extract:** Run Mode 1 to extract text from your map (`war3map.j` and `.txt` files).
2. **Auto-Translate:** Run Mode 7.
   - Select source/destination languages.
   - The tool will use the configured LLM to translate all extracted text files in `chinese_tokens_folder/`.
3. **Reinsert:** Run Mode 2 (or 3/4) to insert the translations back into the map.

## 📖 Translation Modes

### Mode 1: Extract
Extract Chinese text from maps and detect system identifiers.
**Output:** `chinese_tokens_folder/` with extracted text.

### Mode 2: Translate (Standard)
Standard translation that preserves Chinese identifiers.
**Use Case:** When you want to keep game terms in original language but translate descriptions.

### Mode 3: Sync (Synchronized)
Translate identifiers to English while synchronizing across files.
**Use Case:** Standardize game terminology in English.

### Mode 4: DepSync (Dependency-Aware)
Ensures critical strings match between JASS and text files.
**Use Case:** Maps with complex item/ability systems where code relies on specific string values.

### Mode 5: Campaign Translation
Automatically translate entire campaign files (.w3n).
**Use Case:** Quick translation of campaigns with minimal manual work.
- **Tip:** Drop `.w3n` files into the `campaign/` folder to pick them from the menu instantly, or provide a custom path.

### 🆕 Mode 7: Auto-Translate (LLM)
Automatically translates the extracted text files using an LLM.
**Use Case:** Replaces manual editing of text files. Much higher quality than Google Translate.

## ⚙️ Configuration

The tool now uses external configuration files in the `data/` directory:

- `data/system_identifiers.json`: List of game terms to detect (e.g., "攻击力": "Attack Damage"). You can add your own terms here!
- `data/jass_patterns.json`: Regex patterns for JASS code analysis.

## 🌍 Campaign Translation

### Supported Languages
1. Chinese (Simplified)
2. English
3. Russian
4. Korean
5. Spanish
6. Portuguese
7. Japanese

### How It Works
1. Extracts the `.w3n` archive.
2. Translates `war3campaign.wts`.
3. Iterates through every map (`.w3x`/`.w3m`) in the campaign.
4. Extracts, translates, and repacks each map.
5. Repacks the entire campaign.

## 📁 File Structure

```
War3-Translator/
│
├── translator2.py                    # Main tool
├── campaign_translator.py            # Campaign module
├── llm_translator.py                 # LLM module
├── config_manager.py                 # Config module
├── stringextractor.py                # Identifier extraction
├── mpqcli.exe                        # MPQ tool
├── config.ini                        # User configuration
│
├── data/                             # Data files
│   ├── system_identifiers.json       # Editable game terms
│   └── jass_patterns.json            # JASS patterns
│
├── campaign/                         # Place .w3n campaigns here
├── backup/                           # Original backups
├── protected/                        # Protected maps
├── translated/                       # Translated output
└── chinese_tokens_folder/            # Extracted tokens
```

## 📊 Version History

### Version 9.0 (Current)
- ✨ **NEW:** LLM Support (OpenAI/OpenRouter)
- ✨ **NEW:** Auto-Translate Mode (Mode 7)
- ✨ **NEW:** External Configuration (data/ folder)
- ✨ **NEW:** Progress bars for long operations
- 🔧 Refactored codebase for better maintainability

### Version 8.0
- ✨ **NEW:** Campaign translation mode (Mode 5)
- ✨ **NEW:** Google Translate API integration

---

## 🚀 Getting Started Now!

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Configure:** Set up `config.ini` with your API keys.
3. **Run the tool:** `python translator2.py`
4. **Enjoy translated Warcraft III content! 🎮**
