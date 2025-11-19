# Warcraft III Translation Tool

A comprehensive translation toolkit for Warcraft III maps and campaigns with support for multi-language translation, system identifier detection, and Google Translate API integration.

## 🌟 Features

### Map Translation (Modes 1-4)
- **Extract Chinese Text** - Extract and detect system identifiers from maps
- **Standard Translation** - Preserve identifiers while translating descriptions
- **Synchronized Translation** - Translate identifiers to standardize game terms
- **Dependency-Aware Translation** - Ensure critical strings match between JASS and text files

### 🆕 Campaign Translation (Mode 5)
- **Automatic Campaign Processing** - Translate entire .w3n campaign files
- **Google Translate Integration** - Powered by Google Translate API
- **Multi-Language Support** - 7 languages supported:
  - Chinese (Simplified) ↔ English
  - Russian, Korean, Spanish, Portuguese, Japanese
- **Smart Backup System** - Automatic backups with protection detection
- **MPQ Archive Handling** - Extract, translate, and repack campaign archives

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Translation Modes](#translation-modes)
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
- `googletrans==4.0.0rc1` - Google Translate API (free version, for campaign mode)

**Optional (for better performance):**
- `google-cloud-translate` - Official Google Cloud API (requires API key)

### 2b. Google Translate API Setup (Optional)

The campaign translator works with **two options**:

**🆓 Free Version (Default):** No setup needed, works immediately!

**🔑 Official Google Cloud API (Optional):** Better performance for large campaigns
- See [GOOGLE_API_SETUP.md](GOOGLE_API_SETUP.md) for complete setup guide
- Quick start:
  1. Get API key from Google Cloud Console
  2. `pip install google-cloud-translate`
  3. `copy config.ini.template config.ini`
  4. Add your API key to `config.ini`

### 3. Verify Files

Ensure these files are present:
- `translator2.py` - Main translation tool
- `stringextractor.py` - System identifier extraction
- `campaign_translator.py` - Campaign translation module (NEW!)
- `mpqcli.exe` - MPQ archive tool
- `Listfilesbasico.txt` - MPQ file listing

## 🎯 Quick Start

### Basic Usage

```bash
python translator2.py
```

You'll see a menu with available modes:

```
======================================================================
 Warcraft III Map Translation Tool v8.0 - Dependency Support
======================================================================
 ✓ stringextractor.py loaded - Mode 3 & 4 available
 ✓ campaign_translator.py loaded - Mode 5 (Campaign) available

Available modes:
 1) extract   - Extract Chinese text & Detect system identifiers
 2) translate - Standard translation (preserves identifiers)
 3) sync      - Synchronized translation (translates identifiers)
 4) depsync   - Dependency-aware synchronized translation
 5) campaign  - Campaign translation with Google Translate (.w3n)
 6) quit      - Exit

Select mode (1-6):
```

### Example: Translate a Campaign from Chinese to English

1. Run the tool: `python translator2.py`
2. Select mode: `5`
3. Choose source language: `1` (Chinese)
4. Choose destination language: `2` (English)
5. Enter campaign path: `C:\Games\MyCampaign.w3n`

The tool will automatically:
- Create a backup in `backup/`
- Extract the campaign
- Translate all .wts files
- Process maps inside the campaign
- Save the translated campaign to `translated/`

## 📖 Translation Modes

### Mode 1: Extract

Extract Chinese text from maps and detect system identifiers.

**Use Case:** First step in manual translation workflow

**Processes:**
- `.txt` files (CampaignAbilityStrings.txt, CampaignUnitStrings.txt, etc.)
- `war3map.j` (JASS script code)

**Options:**
- Preserve custom box formatting
- Restrict to UI text only
- Detect system identifiers (50+ game terms)

**Output:**
- `chinese_tokens_folder/` with extracted text
- `identifier_dictionary.txt` with detected game terms

### Mode 2: Translate (Standard)

Standard translation that preserves Chinese identifiers.

**Use Case:** When you want to keep game terms in original language

**Features:**
- Preserves system identifiers in Chinese
- Translates descriptions and UI text
- Auto-fixes JASS string issues
- Generates change reports

**Options:**
- Enable auto-fix
- UTF-8 output
- Generate detailed report

### Mode 3: Sync (Synchronized)

Translate identifiers to English while synchronizing across files.

**Use Case:** Standardize game terminology in English

**Features:**
- Translates system identifiers (攻击力 → Attack Damage)
- Hybrid approach: applies identifier translations to manual translations
- Preserves user's manual work

### Mode 4: DepSync (Dependency-Aware)

Ensures critical strings match between JASS and text files.

**Use Case:** Maps with complex item/ability systems

**Features:**
- Detects strings used in JASS logic
- Prevents breaking item effects and abilities
- Synchronized translation across JASS and text files

### 🆕 Mode 5: Campaign Translation

Automatically translate entire campaign files using Google Translate.

**Use Case:** Quick translation of campaigns with minimal manual work

**Features:**
- Processes .w3n campaign archives
- Translates war3campaign.wts and war3map.wts
- Handles protected maps gracefully
- Multi-language support (7 languages)
- Automatic backup and organization

**See [Campaign Translation Guide](CAMPAIGN_TRANSLATION_README.md) for detailed documentation.**

## 🌍 Campaign Translation

### Supported Languages

1. Chinese (Simplified)
2. English
3. Russian
4. Korean
5. Spanish
6. Portuguese
7. Japanese

You can translate between any combination of these languages.

### How It Works

```
.w3n Campaign File
       ↓
   Extract Archive
       ↓
Translate war3campaign.wts
       ↓
Process Each Map (.w3x/.w3m)
   ├── Extract Map
   ├── Check Protection
   ├── Translate war3map.wts
   └── Repack Map
       ↓
Repack Campaign
       ↓
Save to translated/
```

### Output Folders

- **backup/** - Original files with timestamps
- **protected/** - Maps detected as protected
- **translated/** - Fully translated campaigns

### Example

```bash
# Input
MyChineseCampaign.w3n

# After translation:
# backup/MyChineseCampaign_20250119_143022.w3n (original)
# translated/MyChineseCampaign.w3n (translated)
# protected/ProtectedMap.w3x (if protected maps found)
```

## 📁 File Structure

```
War3-Translator/
│
├── translator2.py                    # Main tool (Modes 1-4)
├── campaign_translator.py            # Campaign translation (Mode 5)
├── stringextractor.py                # System identifier detection
├── mpqcli.exe                        # MPQ archive handler
├── Listfilesbasico.txt               # MPQ file listing
├── requirements.txt                  # Python dependencies
│
├── README.md                         # This file
├── CAMPAIGN_TRANSLATION_README.md    # Detailed campaign guide
│
├── backup/                           # Original backups
├── protected/                        # Protected maps
├── translated/                       # Translated output
└── chinese_tokens_folder/            # Extracted tokens (Mode 1)
```

## 🔧 Requirements

### System Requirements
- **OS:** Windows (Linux/Mac with wine for mpqcli.exe)
- **Python:** 3.7 or higher
- **Internet:** Required for Google Translate API (Mode 5)

### Python Packages

```
chardet>=5.0.0
ftfy>=6.0.0
googletrans==4.0.0rc1
```

Install all dependencies:
```bash
pip install -r requirements.txt
```

### External Tools

- **mpqcli.exe** - Included in repository
- **Listfilesbasico.txt** - Included in repository

## 🛠️ Troubleshooting

### Common Issues

#### "Google Translate is not available"

**Solution:**
```bash
pip install googletrans==4.0.0rc1
```

#### "stringextractor.py not found"

**Solution:** Ensure `stringextractor.py` is in the same directory as `translator2.py`

#### "MPQ operation timed out"

**Causes:**
- Very large campaign files
- Corrupted .w3n file
- Missing mpqcli.exe

**Solutions:**
- Try with a smaller campaign first
- Verify the .w3n file is valid
- Check that mpqcli.exe is present

#### Translation Rate Limiting

Google Translate may rate-limit frequent requests.

**Solutions:**
- The tool includes automatic retry (3 attempts)
- Wait a few minutes between large translations
- Small delays are added every 10 strings

### Need More Help?

- Check [CAMPAIGN_TRANSLATION_README.md](CAMPAIGN_TRANSLATION_README.md) for campaign-specific issues
- Ensure all dependencies are installed
- Verify file paths are correct
- Check internet connection (for Mode 5)

## 🎮 Workflow Examples

### Example 1: Quick Campaign Translation

**Goal:** Translate a Chinese campaign to English

```bash
python translator2.py
# Select: 5 (campaign)
# Source: 1 (Chinese)
# Dest: 2 (English)
# Path: C:\Games\MyCampaign.w3n
```

**Result:**
- Original backed up to `backup/`
- Translated campaign in `translated/`
- Protected maps (if any) in `protected/`

### Example 2: Manual Map Translation

**Goal:** Carefully translate a map with custom identifiers

**Step 1:** Extract
```bash
python translator2.py
# Select: 1 (extract)
# Preserve formatting: y
# Restrict UI: y
# Detect identifiers: y
```

**Step 2:** Edit translations manually in `chinese_tokens_folder/`

**Step 3:** Apply translations
```bash
python translator2.py
# Select: 2 (translate) or 3 (sync)
# Auto-fix: y
# UTF-8: y
# Report: y
```

### Example 3: Dependency-Aware Translation

**Goal:** Translate a map with complex item/ability system

```bash
python translator2.py
# Select: 4 (depsync)
# This ensures strings used in JASS logic stay synchronized
```

## 🔍 Advanced Features

### System Identifier Detection

The tool recognizes 50+ Chinese game terms:

```
'全属性' → 'All Stats'
'攻击力' → 'Attack Damage'
'攻击速度' → 'Attack Speed'
'法强' → 'Spell Power'
'护甲' → 'Armor'
'法术抗性' → 'Magic Resist'
'冷却缩减' → 'CDR'
...and more
```

### Auto-Fix Features

Mode 2-4 include automatic fixes for:
- Newline conversion (`\n` escapes)
- Unescaped quotes
- Control character removal
- Encoding validation

### Change Reports

Detailed reports show:
- Original vs. translated text
- Byte positions
- Context before/after
- Auto-fixes applied

## 📝 WTS File Format

Warcraft III Trigger String files (.wts) use this format:

```
STRING 1
{
Welcome to the campaign!
}

STRING 2
{
Your quest begins here.
}
```

The campaign translator automatically parses and translates these files.

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Additional language support
- Better protection detection
- GUI interface
- Linux/Mac native MPQ tools
- Translation caching
- Batch processing

## 📜 License

This project is provided as-is for the Warcraft III community.

## 🙏 Credits

- **mpqcli.exe** - MPQ archive tool
- **Google Translate API** - Translation service
- **Warcraft III Community** - Continuous support and feedback

## 📊 Version History

### Version 8.0 (2025-01-19)
- ✨ **NEW:** Campaign translation mode (Mode 5)
- ✨ **NEW:** Google Translate API integration
- ✨ **NEW:** Multi-language support (7 languages)
- ✨ **NEW:** Automatic backup system
- ✨ **NEW:** Protection detection
- 🐛 Fixed bytes literal syntax error
- 📝 Comprehensive documentation

### Previous Versions
- Version 7.0 - Dependency-aware translation
- Version 6.0 - Synchronized translation
- Version 5.0 - System identifier detection
- Version 4.0 - Enhanced extraction
- Version 3.0 - JASS string processing
- Version 2.0 - Multi-file support
- Version 1.0 - Initial release

---

## 🚀 Getting Started Now!

1. **Install dependencies:** `pip install -r requirements.txt`
2. **Run the tool:** `python translator2.py`
3. **Choose your mode:**
   - For quick campaign translation: Mode 5
   - For manual control: Modes 1-4
4. **Enjoy translated Warcraft III content! 🎮**

---

**Questions? Issues? Check [CAMPAIGN_TRANSLATION_README.md](CAMPAIGN_TRANSLATION_README.md) for more details!**
