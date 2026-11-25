; Inno Setup: the installer of «Азимут» for Windows (0.91.57), made from dist\Azimuth of packaging/azimuth.spec.
; iscc /DAppVersion=0.91.57 packaging\azimuth.iss  ->  dist\installer\Azimuth-Setup-0.91.57.exe
; Installed for the user who runs it (no administrator rights asked): %LOCALAPPDATA%\Programs\Azimuth; the settings,
; the logs and the programs installed from Sextant (xtb, MOPAC, MS-MPI) are in the folders of the user, not here.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6E3C2A47-9B1D-4C8E-A5F2-0D7B3E914A61}
AppName=Азимут
AppVerName=Азимут {#AppVersion}
AppVersion={#AppVersion}
AppPublisher=Сергей Собалев
DefaultDirName={localappdata}\Programs\Azimuth
DefaultGroupName=Азимут
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\installer
OutputBaseFilename=Azimuth-Setup-{#AppVersion}
SetupIconFile=..\assets\app-icon\Azimuth.ico
UninstallDisplayIcon={app}\Azimuth.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Azimuth\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Азимут"; Filename: "{app}\Azimuth.exe"
Name: "{group}\{cm:UninstallProgram,Азимут}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Азимут"; Filename: "{app}\Azimuth.exe"; Tasks: desktopicon

[Registry]
; 0.131.0: links azimuth:// of the site open the program (azimuth/links.py; the program writes the same at its start)
Root: HKCU; Subkey: "Software\Classes\azimuth"; ValueType: string; ValueName: ""; ValueData: "URL:Azimuth"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\azimuth"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\azimuth\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Azimuth.exe"" ""%1"""

[Run]
Filename: "{app}\Azimuth.exe"; Description: "{cm:LaunchProgram,Азимут}"; Flags: nowait postinstall skipifsilent
