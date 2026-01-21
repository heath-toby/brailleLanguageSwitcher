# Braille Language Switcher

## Overview

Braille Language Switcher is an NVDA add-on that automatically switches the braille output table based on the detected language of the text being read.

While NVDA has an "Automatic" option for braille language, it only selects a table based on NVDA's UI language and doesn't allow you to configure which braille profile (contracted, uncontracted, or computer braille) is used for each language. This add-on fills that gap.

## Features

- **Per-language braille profiles**: Configure different braille table types for each language:
  - Uncontracted (Grade 1)
  - Contracted (Grade 2)
  - Computer Braille
- **Automatic switching**: When the language of the text changes, the braille table automatically switches to your configured profile
- **Enhanced Language Switching integration**: Works with the Enhanced Language Switching add-on if installed for improved language detection
- **Fallback behavior**: Uses NVDA's default braille table for languages you haven't configured

## Installation

1. Download the `.nvda-addon` file
2. Double-click the file to install, or use NVDA's Add-on Manager
3. Restart NVDA when prompted

## Configuration

### Opening Settings

1. Open NVDA menu (NVDA+N)
2. Go to Preferences > Settings
3. Select "Braille Language Switcher" from the categories

### First-time Setup

1. **Enable the add-on**: Check "Enable automatic braille language switching"
2. **Configure languages**:
   - The list shows all languages that have braille tables available in NVDA
   - Check the checkbox next to each language you want to track
   - For each language, click "Modify braille profile..." to configure:
     - **Table type**: Uncontracted, Contracted, or Computer Braille
     - **Specific table**: Choose from available tables for that language and type
3. **Save settings**: Click OK to save and apply your configuration

### Example Configuration

- English: Contracted (UEB Grade 2)
- German: Uncontracted (Grade 1)
- French: Computer Braille

## How It Works

1. NVDA detects language changes in the text being read (either natively or via Enhanced Language Switching)
2. When a language change is detected, the add-on checks if you have a profile configured for that language
3. If a profile exists and is enabled, it switches the braille output table accordingly
4. If no profile exists for the detected language, it falls back to NVDA's default table

## Recommended NVDA Settings

For the best experience with braille panning, configure NVDA to announce text when panning:

1. Open NVDA menu (NVDA+N)
2. Go to Preferences > Settings > Braille
3. Under "Read by paragraph", set to your preference
4. **Important**: Set "Announce when panning by" to "Line" or "Paragraph"

This setting causes NVDA to speak the text when you pan the braille display, which triggers language detection and allows the braille table to switch automatically even when navigating with braille panning keys.

## Enhanced Language Switching Integration

If you have the [Enhanced Language Switching](https://github.com/Emil-18/enhanced_language_switching) add-on installed, this add-on will automatically use its superior language detection capabilities. This provides:

- More accurate language detection
- Support for multiple languages in the same text
- Better handling of mixed-language content

If Enhanced Language Switching is not installed, the add-on uses NVDA's native language detection.

## Requirements

- NVDA 2024.1 or later
- Windows 10/11

## Troubleshooting

### Braille table doesn't change

1. Make sure the add-on is enabled in settings
2. Check that you have configured and enabled the language in your profiles
3. Verify that the text actually contains language change markers (not all content does)

### Settings not saving

1. Ensure you click OK (not Cancel) when closing the settings dialog
2. Check NVDA's configuration folder for write permissions

### Enhanced Language Switching not detected

1. Make sure Enhanced Language Switching is properly installed and enabled
2. Restart NVDA after installing both add-ons

## Known Limitations

- Language detection depends on NVDA or Enhanced Language Switching providing language information
- Some content may not include language markers
- Very short text segments may not trigger language detection
- **Braille panning alone does not trigger language switching** unless you enable "Announce when panning by" in NVDA's braille settings (see Recommended NVDA Settings above)

## Changelog

### Version 1.0.0

- Initial release
- Per-language braille profile configuration
- Enhanced Language Switching integration
- Accessible settings panel

## License

This add-on is licensed under the GNU General Public License version 2 (GPL v2).

## Contributing

Contributions are welcome! Please submit issues and pull requests on GitHub.

## Credits

- Developed by Tobias
- Thanks to the NVDA community for testing and feedback
- Thanks to Emil-18 for the Enhanced Language Switching add-on that inspired this work
