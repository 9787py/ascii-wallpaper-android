param(
    [string]$SdkPath,
    [string]$GradlePath,
    [string]$PythonPath,
    [string[]]$Task = @('assembleDebug')
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $SdkPath) {
    $adbCommand = Get-Command adb -ErrorAction SilentlyContinue
    if ($env:ANDROID_HOME) { $SdkPath = $env:ANDROID_HOME }
    elseif ($env:ANDROID_SDK_ROOT) { $SdkPath = $env:ANDROID_SDK_ROOT }
    elseif ($adbCommand) { $SdkPath = Split-Path (Split-Path $adbCommand.Source) }
}
if (-not $SdkPath -or -not (Test-Path -LiteralPath (Join-Path $SdkPath 'platforms/android-36'))) {
    throw 'Specify -SdkPath pointing to an Android SDK with platform android-36.'
}
if (-not $PythonPath) {
    $candidate = Join-Path $env:USERPROFILE '.local/bin/python3.13.exe'
    if (Test-Path -LiteralPath $candidate) { $PythonPath = $candidate }
    else { $PythonPath = (Get-Command python3.13 -ErrorAction Stop).Source }
}
if (-not $GradlePath) {
    $wrapper = Join-Path $PSScriptRoot 'gradlew.bat'
    if (Test-Path -LiteralPath $wrapper) { $GradlePath = $wrapper }
    $cached = Join-Path $env:USERPROFILE '.gradle/wrapper/dists/gradle-9.6.0-bin'
    if (-not $GradlePath -and (Test-Path -LiteralPath $cached)) {
        $GradlePath = Get-ChildItem -LiteralPath $cached -Filter gradle.bat -Recurse |
            Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $GradlePath) { $GradlePath = (Get-Command gradle -ErrorAction Stop).Source }
}
# Process-scoped only: no global environment or Python installation changes.
$previousAndroidHome = $env:ANDROID_HOME
try {
    $env:ANDROID_HOME = (Resolve-Path -LiteralPath $SdkPath).Path
    & $GradlePath --no-daemon --console=plain "-PbuildPython=$PythonPath" @Task
    if ($LASTEXITCODE -ne 0) { throw "Gradle failed with exit code $LASTEXITCODE" }
} finally {
    $env:ANDROID_HOME = $previousAndroidHome
}
