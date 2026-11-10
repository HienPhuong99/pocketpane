# Downloads a private copy of Python (the official "python" package on nuget.org), checks its
# SHA-256 and unpacks it. Called by install.bat when no Python 3.11+ is installed.
# Done in PowerShell because curl.exe, certutil and tar.exe are not reliable with paths
# outside the ANSI code page (e.g. a user folder with Vietnamese letters).
#
# Input (environment): PP_PY_URL, PP_PY_SHA256, PP_PY_DIR (destination folder).
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # the progress bar makes Invoke-WebRequest very slow
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$zip = Join-Path ([IO.Path]::GetTempPath()) ("pocketpane-python-{0}.zip" -f [guid]::NewGuid())
try {
    Invoke-WebRequest -UseBasicParsing -Uri $env:PP_PY_URL -OutFile $zip
    $hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
    if ($hash -ne $env:PP_PY_SHA256) {
        throw "The download does not match the expected SHA-256 checksum ($hash)."
    }
    Expand-Archive -LiteralPath $zip -DestinationPath $env:PP_PY_DIR -Force
} finally {
    Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
}
