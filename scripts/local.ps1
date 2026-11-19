param(
    [ValidateSet('lancer','installer','arreter','sauvegarder','diagnostic')]
    [string]$Action = 'lancer',
    [switch]$SansNavigateur
)
$ErrorActionPreference = 'Stop'
$projet = Split-Path -Parent $PSScriptRoot
$pythonLocal = Join-Path $projet 'backend\.venv\Scripts\python.exe'
try {
    if (-not (Test-Path -LiteralPath $pythonLocal)) {
        $pythonBase = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
        if (-not (Test-Path -LiteralPath $pythonBase)) {
            $commande = Get-Command python.exe -ErrorAction SilentlyContinue
            if (-not $commande) { throw 'Python 3.12 ou plus recent doit etre installe.' }
            $pythonBase = $commande.Source
        }
        & $pythonBase -m venv (Join-Path $projet 'backend\.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Creation de Python local impossible.' }
    }
    & $pythonLocal -c 'import django, psycopg, reportlab, oracledb'
    if ($LASTEXITCODE -ne 0) {
        & $pythonLocal -m pip install -r (Join-Path $projet 'backend\requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Installation des dependances Python impossible.' }
    }
    if ($Action -in @('lancer','installer')) {
        $frontend = Join-Path $projet 'frontend'
        $index = Join-Path $frontend 'dist\index.html'
        $recompiler = $Action -eq 'installer' -or -not (Test-Path -LiteralPath $index)
        if (-not $recompiler) {
            $dateCompilation = (Get-Item -LiteralPath $index).LastWriteTimeUtc
            $modifies = Get-ChildItem -LiteralPath (Join-Path $frontend 'src') -Recurse -File |
                Where-Object { $_.LastWriteTimeUtc -gt $dateCompilation -and $_.Name -notmatch '\.test\.' } |
                Select-Object -First 1
            $recompiler = $null -ne $modifies
            foreach ($fichier in @('package.json','package-lock.json','vite.config.ts','tailwind.config.ts','tailwind.config.js','index.html')) {
                $chemin = Join-Path $frontend $fichier
                if ((Test-Path -LiteralPath $chemin) -and (Get-Item -LiteralPath $chemin).LastWriteTimeUtc -gt $dateCompilation) {
                    $recompiler = $true
                }
            }
        }
        if ($recompiler) {
            $npmLocal = Get-Command npm.cmd -ErrorAction SilentlyContinue
            if (-not $npmLocal) { throw 'Node.js avec npm doit etre installe pour compiler l interface.' }
            Push-Location $frontend
            try {
                if (-not (Test-Path -LiteralPath 'node_modules')) {
                    & $npmLocal.Source ci
                    if ($LASTEXITCODE -ne 0) { throw 'Installation de l interface impossible.' }
                }
                & $npmLocal.Source run build
                if ($LASTEXITCODE -ne 0) { throw 'Compilation de l interface impossible.' }
            } finally { Pop-Location }
        }
    }
    $arguments = @((Join-Path $PSScriptRoot 'local.py'), $Action)
    if ($SansNavigateur) { $arguments += '--sans-navigateur' }
    & $pythonLocal @arguments
    exit $LASTEXITCODE
} catch {
    Write-Host ('Erreur : ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
