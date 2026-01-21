# Braille Language Switcher for NVDA

An NVDA screen reader add-on that automatically switches braille output tables based on detected text language.

## Features

- Configure different braille profiles (contracted, uncontracted, computer braille) per language
- Automatic table switching when language changes are detected
- Integrates with Enhanced Language Switching add-on when available
- Accessible settings panel for easy configuration

## Building

### Prerequisites

- Python 3.11 or later
- SCons build system

### Install Dependencies

```bash
pip install scons
```

### Build the Add-on

```bash
cd brailleLanguageSwitcher
scons
```

This creates `brailleLanguageSwitcher-1.0.0.nvda-addon` in the project root.

### Install in NVDA

Double-click the `.nvda-addon` file or install via NVDA's Add-on Manager.

## Project Structure

```
brailleLanguageSwitcher/
├── addon/
│   ├── doc/en/readme.md              # User documentation
│   ├── globalPlugins/
│   │   └── brailleLanguageSwitcher/
│   │       ├── __init__.py           # GlobalPlugin class
│   │       ├── configManager.py      # Configuration persistence
│   │       ├── languageDetector.py   # Language detection
│   │       ├── brailleTableManager.py # Table enumeration
│   │       └── settingsPanel.py      # Settings UI
│   └── locale/                       # Translations
├── buildVars.py                      # Build configuration
├── manifest.ini.tpl                  # Manifest template
├── sconstruct                        # Build script
└── readme.md                         # This file
```

## Configuration

After installation:

1. Open NVDA Settings (NVDA+N > Preferences > Settings)
2. Select "Braille Language Switcher"
3. Enable the add-on
4. Configure braille profiles for each language you want to track

## License

GPL v2 - See LICENSE file for details.

## Contributing

Pull requests welcome! Please ensure your code follows NVDA add-on development guidelines.

## Links

- [NVDA Screen Reader](https://www.nvaccess.org/)
- [NVDA Add-on Development Guide](https://github.com/nvdaaddons/DevGuide/wiki/NVDA-Add-on-Development-Guide)
- [Enhanced Language Switching](https://github.com/Emil-18/enhanced_language_switching)
