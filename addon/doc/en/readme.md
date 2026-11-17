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
- **Mixed language braille**: Each language on a line is shown in its own braille table, so an English sentence with a Russian phrase shows English braille for the English and Russian braille for the Russian
- **Input follows the cursor**: The braille input table follows the language of the text at the cursor
- **Follows the voice** (alternative mode): When the speech language changes, braille changes with it, whatever made it change: Dialingo, Enhanced Language Detection, document language tags, or any other add-on that switches speech language
- **Input too**: Optionally switches the braille input table along with the output table
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

## Language Source

The "Language source" combo box in the settings chooses where the language comes from.

### Show each language in its own table (default)

Each braille line is run through the installed language detectors (Dialingo, Enhanced Language Detection) without being spoken. Each part of the line is then shown in the braille table you configured for its language, and in your default table where no other language is found. Cursor routing, selection and panning work as normal across the parts.

The braille input table follows the language of the text at the cursor: with the cursor in a Russian phrase you type Russian braille, and moving back into English gives English input again. Uncheck "Also switch input table" to keep your default input table.

A part in another language needs at least the minimum number of words set in the settings, otherwise it is shown in your default table. Each line is detected once and remembered, so moving along a line does not detect it again.

### Follow the speech language

Language detection add-ons for NVDA all work the same way: they mark each piece of speech with its language, and the synthesizer switches voice on those marks. With this source, the add-on reads the same marks, so braille switches table whenever the voice switches language. It needs no setup for any particular detector, and works with:

- [Dialingo](https://github.com/rashadnaqeeb/nvda-dialingo), including its language lock
- Enhanced Language Detection
- Document language tags, when NVDA's "Automatic language switching" is on (or with Dialingo's language table synthesizer)

This works with speech mode set to off, beeps or on-demand too: NVDA still prepares the speech, which is all the add-on needs.

Braille that is not spoken, such as panning to the next line or routing, is run through the same detectors without being spoken, so it switches too.

Each spoken utterance switches braille to the language most of its words are in, and only when it has at least the minimum number of words set in the settings. Short speech such as typed characters or "button" leaves the table alone.

### Check the braille text

The braille text is checked on its own: document language tags, and the Enhanced Language Detection add-on if it is installed and its checkbox is checked. This is how version 1.1 worked.

## Requirements

- NVDA 2024.3 or later
- Windows 10/11

## Troubleshooting

### Braille table doesn't change

1. Make sure the add-on is enabled in settings
2. Check that you have configured and enabled the language in your profiles
3. With "Follow the speech language", check that the voice itself changes language: if it does not, the detector has not marked the text
4. With "Show each language in its own table" or "Follow the speech language", NVDA's "Automatic language switching" (Speech settings) must be on, unless Dialingo's language table is the synthesizer: Dialingo and Enhanced Language Detection mark nothing while it is off
5. Lower "Minimum words required to switch language" if short lines do not switch

### Settings not saving

1. Ensure you click OK (not Cancel) when closing the settings dialog
2. Check NVDA's configuration folder for write permissions

## Known Limitations

- Language detection depends on a detector or document tags providing language information
- Very short text segments do not switch the table (see the minimum word setting)
- Mixed language braille needs a detector add-on (Dialingo or Enhanced Language Detection); document language tags alone are only used by the other two sources
- With "Follow the speech language", speech that is not about the braille content (for example a notification in another language) also switches the table, until the next text is read
- Chinese word segmentation follows the table chosen in NVDA's braille settings, not the one switched to

## Changelog

### Version 2.0.0

- Mixed language braille: each language on a line is shown in its own table, and the input table follows the language at the cursor. This is the new default
- New "Language source" setting. "Follow the speech language" switches braille whenever the voice changes language, whatever detected it, and so supports Dialingo as well as Enhanced Language Detection and document tags
- Braille panned or routed to without speech is checked with the same detectors
- Fixed: switching tables no longer changes the default tables saved in NVDA's braille settings
- Changes to the default tables in NVDA's braille settings, or a configuration profile switch, are followed straight away
- While you type contracted braille, the input table never changes in the middle of a word
- Requires NVDA 2024.3 or later (earlier versions could not switch the output table at all)

### Version 1.1.0

- Enhanced Language Detection integration
- NVDA 2026.1 compatibility

### Version 1.0.0

- Initial release
- Per-language braille profile configuration
- Accessible settings panel

## License

This add-on is licensed under the GNU General Public License version 2 (GPL v2).

## Contributing

Contributions are welcome! Please submit issues and pull requests on GitHub.

## Credits

- Developed by Tobias
- Thanks to the NVDA community for testing and feedback
- Thanks to Emil-18 for the Enhanced Language Switching add-on that inspired this work
