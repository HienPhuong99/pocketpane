# Creates the PocketPane shortcuts (Desktop + Start menu). Called by install.bat.
# Uses the Unicode IShellLinkW interface directly: WScript.Shell is ANSI-only and fails on
# paths with characters outside the code page (e.g. a user name with Vietnamese letters).
#
# Input (environment): PP_EXE (pythonw.exe), PP_ARGS, PP_DIR (working folder), PP_ICON,
# PP_NAME (shortcut name without .lnk), PP_FOLDERS (optional, ';'-separated; default
# Desktop and Start menu).
$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;

[ComImport, Guid("00021401-0000-0000-C000-000000000046")]
public class PPShellLink {}

[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
public interface PPIShellLinkW {
    void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder file, int max, IntPtr data, int flags);
    void GetIDList(out IntPtr pidl);
    void SetIDList(IntPtr pidl);
    void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder name, int max);
    void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string name);
    void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder dir, int max);
    void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string dir);
    void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder args, int max);
    void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string args);
    void GetHotkey(out short hotkey);
    void SetHotkey(short hotkey);
    void GetShowCmd(out int cmd);
    void SetShowCmd(int cmd);
    void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int max, out int index);
    void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string path, int index);
    void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string path, int reserved);
    void Resolve(IntPtr hwnd, int flags);
    void SetPath([MarshalAs(UnmanagedType.LPWStr)] string file);
}

public static class PPLnk {
    public static void Save(string lnk, string target, string args, string dir, string icon, string desc) {
        var link = (PPIShellLinkW)new PPShellLink();
        link.SetPath(target);
        link.SetArguments(args);
        link.SetWorkingDirectory(dir);
        link.SetIconLocation(icon, 0);
        link.SetDescription(desc);
        ((IPersistFile)link).Save(lnk, true);
    }

    public static string Target(string lnk) {
        var link = (PPIShellLinkW)new PPShellLink();
        ((IPersistFile)link).Load(lnk, 0);
        var sb = new StringBuilder(1024);
        link.GetPath(sb, sb.Capacity, IntPtr.Zero, 0);
        return sb.ToString();
    }
}
"@

$folders = if ($env:PP_FOLDERS) { $env:PP_FOLDERS -split ';' } else {
    @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))
}
foreach ($dir in $folders) {
    $lnk = Join-Path $dir "$($env:PP_NAME).lnk"
    [PPLnk]::Save($lnk, $env:PP_EXE, $env:PP_ARGS, $env:PP_DIR, $env:PP_ICON, 'Mirror your iPhone screen on Windows')
    if ([PPLnk]::Target($lnk) -ne $env:PP_EXE) { throw "shortcut check failed: $lnk" }
}
