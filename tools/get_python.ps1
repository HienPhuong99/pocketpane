# Downloads a private copy of Python (the official "python" package on nuget.org), checks its
# SHA-256 and unpacks it. Called by install.bat when no usable Python 3.11+ is installed.
# Done in PowerShell because curl.exe, certutil and tar.exe are not reliable with paths
# outside the ANSI code page (e.g. a user folder with Vietnamese letters).
#
# Input (environment): PP_PY_URL, PP_PY_SHA256, PP_PY_DIR (destination folder).
# The package is unpacked next to PP_PY_DIR first and only renamed into place when complete,
# so an interrupted run never leaves a half-unpacked Python that later runs would reuse.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # the progress bar makes Invoke-WebRequest very slow
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$dest = $env:PP_PY_DIR
$partial = "$dest.partial"
$zip = Join-Path ([IO.Path]::GetTempPath()) ("pocketpane-python-{0}.zip" -f [guid]::NewGuid())
try {
    Invoke-WebRequest -UseBasicParsing -Uri $env:PP_PY_URL -OutFile $zip
    $hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
    if ($hash -ne $env:PP_PY_SHA256) {
        throw "The download does not match the expected SHA-256 checksum ($hash)."
    }
    if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Recurse -Force }
    Expand-Archive -LiteralPath $zip -DestinationPath $partial
    if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }  # broken earlier copy
    Move-Item -LiteralPath $partial -Destination $dest
} finally {
    Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Recurse -Force -ErrorAction SilentlyContinue }
}
