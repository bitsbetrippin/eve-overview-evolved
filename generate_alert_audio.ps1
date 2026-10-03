# Optional developer tool. Uses eSpeak NG 1.52.0; only WAVs ship to end users.
param([Parameter(Mandatory=$true)][string]$EspeakExe,
      [ValidateSet('scrambled', 'pointed', 'webbed', 'jammed')]
      [string[]]$Words = @('scrambled', 'pointed', 'webbed', 'jammed'))
$ErrorActionPreference = 'Stop'
$assetDir = Join-Path $PSScriptRoot 'assets'
New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
$synthPath = (Resolve-Path -LiteralPath $EspeakExe).Path
foreach ($word in $Words) {
    & $synthPath "--path=$(Split-Path $synthPath)" -v en -s 145 -p 30 -w (Join-Path $assetDir "$word.wav") "You are $word."
    if ($LASTEXITCODE -ne 0) { throw "Speech generation failed: $word" }
}
# Mild amplitude modulation gives the synthetic voice a robotic radio texture.
& (Join-Path $PSScriptRoot 'runtime/python.exe') (Join-Path $PSScriptRoot 'robotic_audio.py') --words $Words
if ($LASTEXITCODE -ne 0) { throw 'Audio processing failed' }
& (Join-Path $PSScriptRoot 'runtime/python.exe') (Join-Path $PSScriptRoot 'generate_voice_styles.py') --espeak $synthPath --words $Words
if ($LASTEXITCODE -ne 0) { throw 'Voice style generation failed' }
