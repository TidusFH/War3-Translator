# Campaign Translation Mode - User Guide

## Overview

The Campaign Translation Mode is a new feature that allows you to translate Warcraft III campaign files (.w3n) using Google Translate API. This mode automatically handles:

- **Campaign archives (.w3n)** - Full campaign translation
- **Map files (.w3x, .w3m)** - Individual maps within campaigns
- **String files (.wts)** - Both war3campaign.wts and war3map.wts
- **Automatic backups** - Original files are preserved
- **Protection detection** - Identifies and handles protected maps
- **Multi-language support** - 7 languages supported

## Features

### ✅ Supported Languages

1. **Chinese (Simplified)**
2. **English**
3. **Russian**
4. **Korean**
5. **Spanish**
6. **Portuguese**
7. **Japanese**

You can translate between any combination of these languages (e.g., Chinese → English, English → Russian, etc.)

### ✅ Automatic Backup System

The tool creates three folders to organize your files:

- **backup/** - Original campaign files with timestamps
- **protected/** - Maps that are detected as protected
- **translated/** - Fully translated campaign files

### ✅ Protection Detection

The tool automatically detects if maps inside the campaign are protected (missing important files like war3map.j). Protected maps are:
- Still backed up to the `protected/` folder
- Processed for .wts file translation if available
- Flagged in the console output

## Installation

### Prerequisites

1. **Python 3.7+** installed on your system
2. **mpqcli.exe** in the same directory (already included)
3. **Listfilesbasico.txt** for MPQ file listing (already included)

### Install Dependencies

Run the following command to install required Python packages:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install chardet ftfy googletrans==4.0.0rc1
```

## Usage

### Method 1: Run from Main Tool

1. Run the main translator:
   ```bash
   python translator2.py
   ```

2. Select **Mode 5 (campaign)** from the menu:
   ```
   Select mode (1-6): 5
   ```

3. Follow the prompts:
   - Select source language (1-7)
   - Select destination language (1-7)
   - Enter path to your .w3n campaign file

### Method 2: Run Standalone

You can also run the campaign translator directly:

```bash
python campaign_translator.py
```

Then follow the same prompts as above.

## Example Workflow

### Translating a Chinese Campaign to English

```
$ python translator2.py

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

Select mode (1-6): 5

======================================================================
CAMPAIGN TRANSLATION MODE
======================================================================
This mode translates Warcraft III campaign files (.w3n)
using Google Translate API.

======================================================================
LANGUAGE SELECTION
======================================================================
Available languages:
  1) Chinese (Simplified)
  2) English
  3) Russian
  4) Korean
  5) Spanish
  6) Portuguese
  7) Japanese

Select SOURCE language (1-7): 1
Select DESTINATION language (1-7): 2

✓ Translation: CHINESE → ENGLISH

Enter path to .w3n campaign file: C:\Games\MyChineseCampaign.w3n

======================================================================
🌍 Translating Campaign: MyChineseCampaign.w3n
   CHINESE → ENGLISH
======================================================================

💾 Backup created: backup\MyChineseCampaign_20250119_143022.w3n

📂 Step 1: Extracting campaign archive...
   📦 Extracting MyChineseCampaign.w3n...
   ✅ Extracted to temp_MyChineseCampaign_20250119_143022\campaign

📝 Step 2: Translating war3campaign.wts...
   📖 Reading war3campaign.wts...
   🔤 Found 45 strings to translate
   [45/45] Translating STRING 45...
   ✅ Translated 45 strings
   💾 Saved to temp_MyChineseCampaign_20250119_143022\campaign\war3campaign.wts

📂 Step 3: Processing map files...

   🗺️  Processing: Chapter01.w3x
   📦 Extracting Chapter01.w3x...
   📝 Translating war3map.wts...
   📖 Reading war3map.wts...
   🔤 Found 128 strings to translate
   [128/128] Translating STRING 128...
   ✅ Translated 128 strings
   💾 Saved to temp_MyChineseCampaign_20250119_143022\map_Chapter01\war3map.wts
   📦 Repacking map...
   ✅ Created temp_MyChineseCampaign_20250119_143022\campaign\Chapter01.w3x

   🗺️  Processing: Chapter02.w3x
   📦 Extracting Chapter02.w3x...
   🔒 Map is protected - backing up to protected folder
   📝 Translating war3map.wts...
   📖 Reading war3map.wts...
   🔤 Found 96 strings to translate
   [96/96] Translating STRING 96...
   ✅ Translated 96 strings
   💾 Saved to temp_MyChineseCampaign_20250119_143022\map_Chapter02\war3map.wts
   📦 Repacking map...
   ✅ Created temp_MyChineseCampaign_20250119_143022\campaign\Chapter02.w3x

📦 Step 4: Repacking campaign...
   📦 Creating MyChineseCampaign.w3n...
   ✅ Created translated\MyChineseCampaign.w3n

======================================================================
✅ Translation Complete!
======================================================================
📁 Original backup: backup\MyChineseCampaign_20250119_143022.w3n
🌍 Translated file: translated\MyChineseCampaign.w3n
======================================================================

🧹 Cleaned up temporary files
```

## How It Works

### Translation Process

1. **Backup Creation**
   - Original .w3n file is copied to `backup/` with timestamp
   - Ensures you never lose the original file

2. **Campaign Extraction**
   - Uses mpqcli.exe to extract the .w3n archive
   - Extracts all files including maps and campaign data

3. **Campaign String Translation**
   - Finds `war3campaign.wts` (campaign-level strings)
   - Parses all STRING entries
   - Translates each string using Google Translate API
   - Writes translated strings back to the file

4. **Map Processing**
   - Finds all .w3x and .w3m files within the campaign
   - Extracts each map using mpqcli.exe
   - Checks for protection (missing critical files)
   - Translates `war3map.wts` in each map
   - Repacks each map with translated strings

5. **Campaign Repacking**
   - Combines all translated components
   - Creates new .w3n file in `translated/` folder
   - Cleans up temporary files

### File Structure

```
War3-Translator/
├── translator2.py              # Main translation tool
├── campaign_translator.py      # NEW: Campaign translation module
├── stringextractor.py          # System identifier extraction
├── mpqcli.exe                  # MPQ archive tool
├── Listfilesbasico.txt         # MPQ file listing
├── requirements.txt            # Python dependencies
│
├── backup/                     # Original files
│   └── MyCampaign_20250119_143022.w3n
│
├── protected/                  # Protected maps
│   └── ProtectedMap.w3x
│
└── translated/                 # Translated campaigns
    └── MyCampaign.w3n
```

## WTS File Format

The tool processes Warcraft III Trigger String (.wts) files, which have the following format:

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

Each STRING entry consists of:
- **STRING** keyword + ID number
- Opening brace `{`
- Text content (can be multi-line)
- Closing brace `}`

## Troubleshooting

### "Google Translate is not available"

**Solution:** Install googletrans:
```bash
pip install googletrans==4.0.0rc1
```

### "MPQ operation timed out"

**Solution:** Large campaigns may take time. The timeout is set to 5 minutes per operation. If this happens:
- Check if mpqcli.exe is in the same directory
- Ensure the .w3n file is not corrupted
- Try with a smaller campaign first

### "No war3map.wts found"

**Explanation:** Some maps don't use .wts files for strings. This is normal and the tool will skip translation for these maps.

### Translation Rate Limiting

Google Translate may rate-limit requests if you're translating very large campaigns. The tool includes:
- Automatic retry with exponential backoff (3 attempts)
- Small delays every 10 strings to avoid rate limiting

If you encounter persistent rate limiting:
- Try translating smaller campaigns
- Wait a few minutes between translation runs
- Consider using a different Google Translate API method (requires API key)

### mpqcli.exe not found

**Solution:** Ensure `mpqcli.exe` is in the same directory as the Python scripts. This tool is required for MPQ archive operations.

## Language Code Reference

| Language | Code | Google Translate Code |
|----------|------|----------------------|
| Chinese (Simplified) | chinese | zh-cn |
| English | english | en |
| Russian | russian | ru |
| Korean | korean | ko |
| Spanish | spanish | es |
| Portuguese | portuguese | pt |
| Japanese | japanese | ja |

## Advanced Usage

### Running as a Module

```python
from campaign_translator import CampaignTranslator

# Create translator instance
translator = CampaignTranslator()

# Translate a campaign
translator.translate_campaign(
    campaign_path="path/to/campaign.w3n",
    src_lang="chinese",
    dest_lang="english"
)
```

### Custom MPQ Tool Path

```python
translator = CampaignTranslator(
    mpqcli_path="path/to/custom/mpqcli.exe",
    listfile_path="path/to/custom/listfile.txt"
)
```

## Limitations

1. **Protected Maps**: Maps with heavy protection may not be fully translatable, but .wts files will still be processed if available.

2. **Rate Limiting**: Google Translate may rate-limit frequent requests. The tool includes automatic retry logic.

3. **Translation Quality**: Automated translation may not be perfect. Manual review of critical campaign text is recommended.

4. **File Size**: Very large campaigns may take significant time to process.

5. **Windows Only**: mpqcli.exe is a Windows executable. Linux/Mac users need wine or alternative MPQ tools.

## Tips for Best Results

1. **Test First**: Try the tool on a small campaign first to verify it works for your setup.

2. **Backup Manually**: Although the tool creates backups, consider making your own backup of important campaigns.

3. **Review Translations**: Check the translated campaign in the World Editor to verify quality.

4. **Protected Maps**: If you encounter protected maps, use a map unprotector first if you need full translation.

5. **Network**: Ensure stable internet connection for Google Translate API access.

## Support

If you encounter issues:

1. Check this README for troubleshooting steps
2. Verify all dependencies are installed
3. Ensure mpqcli.exe is present and working
4. Check that the .w3n file is valid and not corrupted

## Version History

### Version 1.0 (2025-01-19)
- Initial release
- Support for .w3n campaign translation
- Google Translate API integration
- 7 languages supported
- Automatic backup and protection detection
- Integration with translator2.py main tool

---

**Happy Translating! 🌍🎮**
