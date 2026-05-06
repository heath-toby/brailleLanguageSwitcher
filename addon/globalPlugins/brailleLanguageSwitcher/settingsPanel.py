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

        # Translators: Checkbox to enable input table switching
        self._inputSwitchingCheckBox = sHelper.addItem(
            wx.CheckBox(
                self,
                label=_("Also switch &input table when language changes")
            )
        )
        self._inputSwitchingCheckBox.SetValue(self._configManager.autoInputSwitching)

        # Enhanced Language Detection integration - only show if the add-on is installed
        from . import isEnhancedLanguageDetectionAvailable
        self._enhancedAvailable = isEnhancedLanguageDetectionAvailable()

        if self._enhancedAvailable:
            # Translators: Checkbox to enable Enhanced Language Detection integration
            self._useEnhancedCheckBox = sHelper.addItem(
                wx.CheckBox(
                    self,
                    label=_("Use Enhanced Language &Detection for text-based detection")
                )
            )
            self._useEnhancedCheckBox.SetValue(self._configManager.useEnhancedDetection)

            # Minimum word threshold
            # Translators: Label for minimum word threshold spin control
            self._wordThresholdCtrl = sHelper.addLabeledControl(
                _("Minimum &words required to switch language:"),
                wx.SpinCtrl,
                min=1,
                max=50,
                initial=self._configManager.minWordThreshold
            )
        else:
            self._useEnhancedCheckBox = None
            self._wordThresholdCtrl = None

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
        if self._enhancedAvailable:
            # Translators: Status text when Enhanced Language Detection is available
            statusText = _("Enhanced Language Detection: Available")
        else:
            # Translators: Status text when Enhanced Language Detection is not installed
            statusText = _("Enhanced Language Detection: Not installed (document tags only)")
        self._statusText = wx.StaticText(self._languagePanel, label=statusText)
        langPanelSizer.Add(self._statusText, flag=wx.TOP, border=5)

        sHelper.addItem(self._languagePanel, flag=wx.EXPAND)

        # Update visibility based on enabled state
        self._updatePanelVisibility()

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
        self._configManager.autoInputSwitching = self._inputSwitchingCheckBox.GetValue()

        # Only save enhanced detection settings if the controls exist
        if self._useEnhancedCheckBox is not None:
            self._configManager.useEnhancedDetection = self._useEnhancedCheckBox.GetValue()
        if self._wordThresholdCtrl is not None:
            self._configManager.minWordThreshold = self._wordThresholdCtrl.GetValue()

        # Update enabled state for each language based on checkbox
        for index, langCode in enumerate(self._languageCodes):
            isChecked = self._languageListBox.IsChecked(index)
            self._configManager.updateLanguageEnabled(langCode, isChecked)

        # Persist to disk
        self._configManager.save()

        log.debug("BrailleLanguageSwitcher: Settings saved")

    def postSave(self) -> None:
        """Called by NVDA after settings are saved - apply changes immediately."""
        # Get the global plugin instance and tell it to reload
        from . import _globalPlugin
        if _globalPlugin:
            _globalPlugin.reloadConfiguration()
            log.debug("BrailleLanguageSwitcher: Configuration reloaded")


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
        self._inputTableFileNames: List[str] = []

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

        # Specific output table selection
        # Translators: Label for braille output table selection
        tableLabel = _("&Output table:")
        self._tableCombo = sHelper.addLabeledControl(
            tableLabel,
            wx.Choice,
            choices=[]
        )

        # Populate tables for current type
        self._populateTables()

        # Input table selection
        # Translators: Label for input table type selection
        inputTableTypeLabel = _("Input table t&ype:")
        self._inputTableTypeCombo = sHelper.addLabeledControl(
            inputTableTypeLabel,
            wx.Choice,
            choices=self._tableTypeChoices
        )
        self._inputTableTypeCombo.SetSelection(0)
        self._inputTableTypeCombo.Bind(wx.EVT_CHOICE, self._onInputTableTypeChanged)

        # Translators: Label for braille input table selection
        inputTableLabel = _("&Input table:")
        self._inputTableCombo = sHelper.addLabeledControl(
            inputTableLabel,
            wx.Choice,
            choices=[]
        )

        # Populate input tables
        self._populateInputTables()

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
        """Populate output table combo based on selected type."""
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

    def _populateInputTables(self) -> None:
        """Populate input table combo based on selected type."""
        tableTypeIndex = self._inputTableTypeCombo.GetSelection()

        # Get tables for this language and type
        tables = self._tableManager.getTablesForLanguage(
            self._langCode,
            tableTypeIndex
        )

        self._inputTableCombo.Clear()
        self._inputTableFileNames = []

        # Add option to use same as output
        # Translators: Option to use same table as output for input
        self._inputTableCombo.Append(_("(Same as output table)"))
        self._inputTableFileNames.append(None)

        if not tables:
            # Also try getting all tables for this language
            tables = self._tableManager.getTablesForLanguage(self._langCode, None)

        for table in tables:
            self._inputTableCombo.Append(table.displayName)
            self._inputTableFileNames.append(table.fileName)

        self._inputTableCombo.SetSelection(0)

    def _onInputTableTypeChanged(self, evt: wx.CommandEvent) -> None:
        """Handle input table type selection change."""
        self._populateInputTables()

    def _loadExistingProfile(self) -> None:
        """Load existing profile settings if available."""
        profile = self._configManager.getLanguageProfile(self._langCode)
        if profile:
            # Set output table type
            tableType = profile.get("tableType", "uncontracted")
            typeIndex = {
                "uncontracted": 0,
                "contracted": 1,
                "computer": 2,
            }.get(tableType, 0)
            self._tableTypeCombo.SetSelection(typeIndex)

            # Refresh output table list for this type
            self._populateTables()

            # Select the configured output table
            tableFileName = profile.get("tableFileName")
            if tableFileName and tableFileName in self._tableFileNames:
                tableIndex = self._tableFileNames.index(tableFileName)
                self._tableCombo.SetSelection(tableIndex)

            # Load input table settings
            inputTableFileName = profile.get("inputTableFileName")
            if inputTableFileName:
                # Refresh input table list
                self._populateInputTables()
                # Try to find and select the input table
                if inputTableFileName in self._inputTableFileNames:
                    inputIndex = self._inputTableFileNames.index(inputTableFileName)
                    self._inputTableCombo.SetSelection(inputIndex)

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

            # Get input table selection (None means use same as output)
            inputTableIndex = self._inputTableCombo.GetSelection()
            inputTableFileName = None
            if inputTableIndex != wx.NOT_FOUND and inputTableIndex < len(self._inputTableFileNames):
                inputTableFileName = self._inputTableFileNames[inputTableIndex]

            # Save the profile
            self._configManager.setLanguageProfile(
                self._langCode,
                tableFileName,
                tableType,
                enabled=True,
                inputTableFileName=inputTableFileName
            )

            log.debug(
                f"BrailleLanguageSwitcher: Set profile for {self._langCode}: "
                f"{tableType} / {tableFileName} (input: {inputTableFileName})"
            )

        self.EndModal(wx.ID_OK)
