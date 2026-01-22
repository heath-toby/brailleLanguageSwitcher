# -*- coding: UTF-8 -*-
# BrailleLanguageSwitcher: Settings Panel
# Provides accessible UI for configuring language-to-braille-table mappings

from typing import List, Dict, Optional, TYPE_CHECKING

import wx
import gui
from gui import guiHelper
from gui.settingsDialogs import SettingsPanel
from gui import nvdaControls
from logHandler import log

if TYPE_CHECKING:
    from .configManager import ConfigManager
    from .brailleTableManager import BrailleTableManager

# Translators: Settings panel title
PANEL_TITLE = _("Braille Language Switcher")

# Table type constants matching brailleTableManager
TABLE_TYPE_UNCONTRACTED = 0
TABLE_TYPE_CONTRACTED = 1
TABLE_TYPE_COMPUTER = 2


class BrailleLanguageSwitcherSettingsPanel(SettingsPanel):
    """
    Settings panel for Braille Language Switcher.

    Provides an accessible interface for:
    - Enabling/disabling automatic language switching
    - Selecting which languages to track
    - Configuring braille table profiles per language
    """

    # Translators: Title of the settings panel in NVDA settings
    title = PANEL_TITLE

    def __init__(self, parent):
        """Initialize the settings panel."""
        # Import here to avoid circular imports
        from .configManager import ConfigManager
        from .brailleTableManager import BrailleTableManager

        self._configManager = ConfigManager()
        self._tableManager = BrailleTableManager()
        # Track initial state to detect changes
        self._initialEnabled = self._configManager.enabled
        self._initialEnabledLanguages = set(self._configManager.getEnabledLanguages())
        super().__init__(parent)

    def makeSettings(self, settingsSizer: wx.BoxSizer) -> None:
        """
        Create the settings controls.

        Args:
            settingsSizer: The sizer to add controls to
        """
        sHelper = guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

        # Enable/Disable toggle
        # Translators: Checkbox to enable the add-on
        self._enabledCheckBox = sHelper.addItem(
            wx.CheckBox(
                self,
                label=_("&Enable automatic braille language switching")
            )
        )
        self._enabledCheckBox.SetValue(self._configManager.enabled)
        self._enabledCheckBox.Bind(wx.EVT_CHECKBOX, self._onEnabledToggle)

        # Language configuration panel (shown/hidden based on enabled state)
        self._languagePanel = wx.Panel(self)
        langPanelSizer = wx.BoxSizer(wx.VERTICAL)
        self._languagePanel.SetSizer(langPanelSizer)

        # Translators: Label for the language list
        langListLabel = wx.StaticText(
            self._languagePanel,
            label=_("Configured &languages (check to enable):")
        )
        langPanelSizer.Add(langListLabel, flag=wx.BOTTOM, border=5)

        # Use NVDA's accessible CustomCheckListBox for language selection
        self._languageListBox = nvdaControls.CustomCheckListBox(
            self._languagePanel,
            style=wx.LB_SINGLE
        )
        langPanelSizer.Add(
            self._languageListBox,
            proportion=1,
            flag=wx.EXPAND | wx.BOTTOM,
            border=10
        )

        # Populate the language list
        self._populateLanguageList()

        # Buttons panel
        buttonPanel = wx.Panel(self._languagePanel)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonPanel.SetSizer(buttonSizer)

        # Translators: Button to modify braille profile for selected language
        self._modifyButton = wx.Button(
            buttonPanel,
            label=_("&Modify braille profile...")
        )
        self._modifyButton.Bind(wx.EVT_BUTTON, self._onModify)
        buttonSizer.Add(self._modifyButton, flag=wx.RIGHT, border=10)

        # Translators: Button to reset all profiles to defaults
        self._resetButton = wx.Button(
            buttonPanel,
            label=_("&Reset all profiles")
        )
        self._resetButton.Bind(wx.EVT_BUTTON, self._onReset)
        buttonSizer.Add(self._resetButton)

        langPanelSizer.Add(buttonPanel, flag=wx.BOTTOM, border=10)

        # Status text
        # Translators: Status text showing Enhanced Language Switching integration
        elsStatus = (
            _("Enhanced Language Switching: Available")
            if self._isEnhancedLanguageSwitchingAvailable()
            else _("Enhanced Language Switching: Not installed (using native detection)")
        )
        self._statusText = wx.StaticText(self._languagePanel, label=elsStatus)
        langPanelSizer.Add(self._statusText, flag=wx.TOP, border=5)

        sHelper.addItem(self._languagePanel, flag=wx.EXPAND)

        # Update visibility based on enabled state
        self._updatePanelVisibility()

    def _isEnhancedLanguageSwitchingAvailable(self) -> bool:
        """Check if Enhanced Language Switching add-on is installed."""
        try:
            from globalPlugins import enhancedLanguageDetection
            return True
        except ImportError:
            pass
        try:
            from globalPlugins import enhanced_language_switching
            return True
        except ImportError:
            return False

    def _populateLanguageList(self) -> None:
        """Populate the language list with available languages."""
        self._languageListBox.Clear()
        self._languageCodes: List[str] = []

        # Get available languages from braille tables
        availableLanguages = self._tableManager.getAvailableLanguages()
        configuredProfiles = self._configManager.getAllLanguageProfiles()
        enabledLanguages = self._configManager.getEnabledLanguages()

        # Sort languages by display name
        sortedLanguages = sorted(
            availableLanguages.items(),
            key=lambda x: x[1].lower()
        )

        for langCode, langName in sortedLanguages:
            profile = configuredProfiles.get(langCode)

            # Build display text
            if profile:
                tableType = profile.get("tableType", "uncontracted")
                # Translators: Format for language entry with configured profile
                # {lang} is the language name, {type} is the braille type
                displayText = _("{lang} ({type})").format(
                    lang=langName,
                    type=self._getTableTypeDisplayName(tableType)
                )
            else:
                displayText = langName

            index = self._languageListBox.Append(displayText)
            self._languageCodes.append(langCode)

            # Check if enabled
            if langCode in enabledLanguages:
                self._languageListBox.Check(index, True)

    def _getTableTypeDisplayName(self, tableType: str) -> str:
        """Get display name for a table type."""
        typeNames = {
            # Translators: Braille table type name
            "uncontracted": _("Uncontracted"),
            # Translators: Braille table type name
            "contracted": _("Contracted"),
            # Translators: Braille table type name
            "computer": _("Computer Braille"),
        }
        return typeNames.get(tableType, tableType)

    def _updatePanelVisibility(self) -> None:
        """Show/hide language panel based on enabled state."""
        isEnabled = self._enabledCheckBox.GetValue()
        self._languagePanel.Show(isEnabled)
        self._languagePanel.GetParent().Layout()

    def _onEnabledToggle(self, evt: wx.CommandEvent) -> None:
        """Handle enable/disable toggle."""
        self._updatePanelVisibility()

    def _onModify(self, evt: wx.CommandEvent) -> None:
        """Open dialog to modify braille profile for selected language."""
        selection = self._languageListBox.GetSelection()
        if selection == wx.NOT_FOUND:
            # Translators: Error message when no language is selected
            gui.messageBox(
                _("Please select a language to modify."),
                # Translators: Error dialog title
                _("No Selection"),
                wx.OK | wx.ICON_WARNING
            )
            return

        langCode = self._languageCodes[selection]
        availableLanguages = self._tableManager.getAvailableLanguages()
        langName = availableLanguages.get(langCode, langCode)

        dialog = BrailleProfileDialog(
            self,
            langCode,
            langName,
            self._tableManager,
            self._configManager
        )

        if dialog.ShowModal() == wx.ID_OK:
            # Refresh the list to show updated profile
            self._populateLanguageList()
            # Re-select the same language
            if langCode in self._languageCodes:
                newIndex = self._languageCodes.index(langCode)
                self._languageListBox.SetSelection(newIndex)

        dialog.Destroy()

    def _onReset(self, evt: wx.CommandEvent) -> None:
        """Reset all language profiles."""
        # Translators: Confirmation message for resetting all profiles
        result = gui.messageBox(
            _("Are you sure you want to reset all braille profiles? "
              "This cannot be undone."),
            # Translators: Confirmation dialog title
            _("Confirm Reset"),
            wx.YES_NO | wx.ICON_QUESTION
        )

        if result == wx.YES:
            # Clear all profiles
            self._configManager._config["languageProfiles"] = {}
            self._populateLanguageList()

    def onSave(self) -> None:
        """Save settings when OK is pressed."""
        # Get current state
        currentEnabled = self._enabledCheckBox.GetValue()
        currentEnabledLanguages = set()
        for index, langCode in enumerate(self._languageCodes):
            if self._languageListBox.IsChecked(index):
                currentEnabledLanguages.add(langCode)

        # Check if anything changed
        settingsChanged = (
            currentEnabled != self._initialEnabled or
            currentEnabledLanguages != self._initialEnabledLanguages
        )

        # Save enabled state
        self._configManager.enabled = currentEnabled

        # Update enabled state for each language based on checkbox
        for index, langCode in enumerate(self._languageCodes):
            isChecked = self._languageListBox.IsChecked(index)
            self._configManager.updateLanguageEnabled(langCode, isChecked)

        # Persist to disk
        self._configManager.save()

        log.debug("BrailleLanguageSwitcher: Settings saved")

        # Only show restart reminder if settings actually changed
        if settingsChanged:
            # Translators: Message shown after saving settings
            gui.messageBox(
                _("Settings saved. Please restart NVDA for changes to take full effect."),
                # Translators: Title of restart reminder dialog
                _("Braille Language Switcher"),
                wx.OK | wx.ICON_INFORMATION
            )


class BrailleProfileDialog(wx.Dialog):
    """
    Dialog to select braille profile for a language.

    Allows selecting:
    - Table type (Uncontracted, Contracted, Computer Braille)
    - Specific braille table from available tables
    """

    def __init__(
        self,
        parent: wx.Window,
        langCode: str,
        langName: str,
        tableManager: "BrailleTableManager",
        configManager: "ConfigManager"
    ):
        """
        Initialize the profile dialog.

        Args:
            parent: Parent window
            langCode: ISO 639-1 language code
            langName: Display name of the language
            tableManager: BrailleTableManager instance
            configManager: ConfigManager instance
        """
        # Translators: Title of the braille profile dialog
        # {lang} is the language name
        super().__init__(
            parent,
            title=_("Braille Profile for {lang}").format(lang=langName)
        )

        self._langCode = langCode
        self._tableManager = tableManager
        self._configManager = configManager
        self._tableFileNames: List[str] = []

        self._initUI()
        self._loadExistingProfile()

        self.CenterOnParent()

    def _initUI(self) -> None:
        """Initialize the dialog UI."""
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        sHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)

        # Table type selection
        # Translators: Label for table type selection
        tableTypeLabel = _("Braille table &type:")
        self._tableTypeChoices = [
            # Translators: Braille table type option
            _("Uncontracted"),
            # Translators: Braille table type option
            _("Contracted"),
            # Translators: Braille table type option
            _("Computer Braille"),
        ]
        self._tableTypeCombo = sHelper.addLabeledControl(
            tableTypeLabel,
            wx.Choice,
            choices=self._tableTypeChoices
        )
        self._tableTypeCombo.SetSelection(0)
        self._tableTypeCombo.Bind(wx.EVT_CHOICE, self._onTableTypeChanged)

        # Specific table selection
        # Translators: Label for braille table selection
        tableLabel = _("Braille &table:")
        self._tableCombo = sHelper.addLabeledControl(
            tableLabel,
            wx.Choice,
            choices=[]
        )

        # Populate tables for current type
        self._populateTables()

        # Dialog buttons
        buttonSizer = wx.StdDialogButtonSizer()

        okButton = wx.Button(self, wx.ID_OK)
        okButton.SetDefault()
        okButton.Bind(wx.EVT_BUTTON, self._onOk)
        buttonSizer.AddButton(okButton)

        cancelButton = wx.Button(self, wx.ID_CANCEL)
        buttonSizer.AddButton(cancelButton)

        buttonSizer.Realize()
        sHelper.addItem(buttonSizer, flag=wx.ALIGN_RIGHT)

        mainSizer.Add(
            sHelper.sizer,
            border=guiHelper.BORDER_FOR_DIALOGS,
            flag=wx.ALL | wx.EXPAND
        )

        self.SetSizer(mainSizer)
        mainSizer.Fit(self)

    def _populateTables(self) -> None:
        """Populate table combo based on selected type."""
        tableTypeIndex = self._tableTypeCombo.GetSelection()

        # Get tables for this language and type
        tables = self._tableManager.getTablesForLanguage(
            self._langCode,
            tableTypeIndex
        )

        self._tableCombo.Clear()
        self._tableFileNames = []

        if not tables:
            # Also try getting all tables for this language
            tables = self._tableManager.getTablesForLanguage(self._langCode, None)

        for table in tables:
            self._tableCombo.Append(table.displayName)
            self._tableFileNames.append(table.fileName)

        if self._tableCombo.GetCount() > 0:
            self._tableCombo.SetSelection(0)
        else:
            # Translators: Message shown when no tables are available
            self._tableCombo.Append(_("No tables available"))

    def _loadExistingProfile(self) -> None:
        """Load existing profile settings if available."""
        profile = self._configManager.getLanguageProfile(self._langCode)
        if profile:
            # Set table type
            tableType = profile.get("tableType", "uncontracted")
            typeIndex = {
                "uncontracted": 0,
                "contracted": 1,
                "computer": 2,
            }.get(tableType, 0)
            self._tableTypeCombo.SetSelection(typeIndex)

            # Refresh table list for this type
            self._populateTables()

            # Select the configured table
            tableFileName = profile.get("tableFileName")
            if tableFileName and tableFileName in self._tableFileNames:
                tableIndex = self._tableFileNames.index(tableFileName)
                self._tableCombo.SetSelection(tableIndex)

    def _onTableTypeChanged(self, evt: wx.CommandEvent) -> None:
        """Handle table type selection change."""
        self._populateTables()

    def _onOk(self, evt: wx.CommandEvent) -> None:
        """Save the selected profile and close dialog."""
        tableTypeIndex = self._tableTypeCombo.GetSelection()
        tableTypes = ["uncontracted", "contracted", "computer"]
        tableType = tableTypes[tableTypeIndex]

        tableIndex = self._tableCombo.GetSelection()
        if tableIndex != wx.NOT_FOUND and tableIndex < len(self._tableFileNames):
            tableFileName = self._tableFileNames[tableIndex]

            # Save the profile
            self._configManager.setLanguageProfile(
                self._langCode,
                tableFileName,
                tableType,
                enabled=True
            )

            log.debug(
                f"BrailleLanguageSwitcher: Set profile for {self._langCode}: "
                f"{tableType} / {tableFileName}"
            )

        self.EndModal(wx.ID_OK)
