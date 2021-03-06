; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Pthelma"
#define MyAppVersion "DEV"
#define MyAppPublisher "Antonis Christofides"
#define MyAppURL "http://pthelma.readthedocs.org/"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{990DB633-90DF-4E5F-B797-FBC92C211C8F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=LICENSE.txt
OutputBaseFilename=pthelma-{#MyAppVersion}-setup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\loggertodb.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\enhydris_cache.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\aggregate.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\_ctypes.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\_hashlib.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\_socket.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\_ssl.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\pyodbc.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\bz2.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\library.zip"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\pyexpat.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\python27.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\select.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\unicodedata.pyd"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\dickinson.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\vcredist_x86.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\cacert.pem"; DestDir: "{app}"; Flags: ignoreversion

; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\loggertodb.exe"
Name: "{group}\{#MyAppName}"; Filename: "{app}\enhydris_cache.exe"
Name: "{group}\{#MyAppName}"; Filename: "{app}\aggregate.exe"

[Run]
Filename: "{app}\vcredist_x86.exe"; Parameters: "/q /norestart"
