; =============================================================================
; City of Mist Importer - NSIS Installer Script
; =============================================================================
; Requires NSIS 3.x: https://nsis.sourceforge.io/
; Run after build_windows.sh:  makensis com_importer.nsi
; Output: dist\CoM-Importer-0.1.0-windows.exe
; =============================================================================

Unicode true

!define APP_NAME      "CoM-Importer"
!define APP_FULLNAME  "City of Mist Importer"
!define APP_VERSION   "0.1.0"
!define APP_PUBLISHER "CoM Importer"
!define APP_URL       "https://github.com"
!define APP_EXE       "com-importer.exe"
!define INSTALL_DIR   "$PROGRAMFILES64\${APP_NAME}"
!define REG_KEY       "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"

; ── General ───────────────────────────────────────────────────────────────────

Name        "${APP_FULLNAME} ${APP_VERSION}"
OutFile     "dist\${APP_NAME}-${APP_VERSION}-windows.exe"
InstallDir  "${INSTALL_DIR}"
InstallDirRegKey HKLM "${REG_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
BrandingText "${APP_FULLNAME} ${APP_VERSION}"

; ── Modern UI ─────────────────────────────────────────────────────────────────

!include "MUI2.nsh"

!define MUI_ICON   "assets\icons\com_importer.ico"
!define MUI_UNICON "assets\icons\com_importer.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN          "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch ${APP_FULLNAME}"
!define MUI_FINISHPAGE_SHOWREADME   ""
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ── Version Info (shown in file properties) ───────────────────────────────────

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey  "ProductName"     "${APP_FULLNAME}"
VIAddVersionKey  "ProductVersion"  "${APP_VERSION}"
VIAddVersionKey  "CompanyName"     "${APP_PUBLISHER}"
VIAddVersionKey  "FileDescription" "${APP_FULLNAME} Installer"
VIAddVersionKey  "FileVersion"     "${APP_VERSION}"
VIAddVersionKey  "LegalCopyright"  "© 2026 ${APP_PUBLISHER}"

; ── Install ───────────────────────────────────────────────────────────────────

Section "Install"
    SetOutPath "$INSTDIR"

    ; Main executable (single-file build from PyInstaller)
    File "dist\${APP_EXE}"

    ; Config files
    File /r "config"

    ; Uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_FULLNAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" "" \
                    "$INSTDIR\${APP_EXE}" 0
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" \
                    "$INSTDIR\Uninstall.exe"

    ; Desktop shortcut
    CreateShortcut  "$DESKTOP\${APP_FULLNAME}.lnk" \
                    "$INSTDIR\${APP_EXE}" "" \
                    "$INSTDIR\${APP_EXE}" 0

    ; Add/Remove Programs registry entry
    WriteRegStr   HKLM "${REG_KEY}" "DisplayName"      "${APP_FULLNAME}"
    WriteRegStr   HKLM "${REG_KEY}" "DisplayVersion"   "${APP_VERSION}"
    WriteRegStr   HKLM "${REG_KEY}" "Publisher"        "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${REG_KEY}" "URLInfoAbout"     "${APP_URL}"
    WriteRegStr   HKLM "${REG_KEY}" "InstallLocation"  "$INSTDIR"
    WriteRegStr   HKLM "${REG_KEY}" "UninstallString"  '"$INSTDIR\Uninstall.exe"'
    WriteRegStr   HKLM "${REG_KEY}" "DisplayIcon"      "$INSTDIR\${APP_EXE}"
    WriteRegDWORD HKLM "${REG_KEY}" "NoModify"         1
    WriteRegDWORD HKLM "${REG_KEY}" "NoRepair"         1

    ; Estimate install size (KB) for Add/Remove Programs
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "${REG_KEY}" "EstimatedSize" "$0"

SectionEnd

; ── Uninstall ─────────────────────────────────────────────────────────────────

Section "Uninstall"
    ; Remove files
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir  /r "$INSTDIR\config"
    RMDir  "$INSTDIR"

    ; Remove shortcuts
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_FULLNAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir  "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_FULLNAME}.lnk"

    ; Remove registry key
    DeleteRegKey HKLM "${REG_KEY}"

SectionEnd

; ── Helper: get install size ──────────────────────────────────────────────────

!include "FileFunc.nsh"
!insertmacro GetSize
