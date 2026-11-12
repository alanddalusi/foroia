param([switch]$Toolbox)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& ./scripts/local.ps1 -Action Status -Toolbox:$Toolbox
$project = 'foroia-check-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$testPassword = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N')
$testEnv = [IO.File]::ReadAllText((Join-Path $PWD '.env.example')).Replace('CAMBIAR_CONTRASENA_LARGA', $testPassword)
$testEnv = $testEnv.Replace('EDITORIAL_API_TOKEN=', "EDITORIAL_API_TOKEN=$testPassword")
$testEnv = $testEnv.Replace('EDITORIAL_PASSWORD=', "EDITORIAL_PASSWORD=$testPassword")
[IO.File]::WriteAllText((Join-Path $PWD '.local/repro.env'), $testEnv, [Text.UTF8Encoding]::new($false))
$override = @'
services:
  api:
    image: foroia-codex-api
    pull_policy: never
    ports: !override []
  web:
    image: foroia-codex-web
    pull_policy: never
    ports: !override []
  mail-worker:
    image: foroia-codex-mail-worker
    pull_policy: never
  research-worker:
    image: foroia-codex-research-worker
    pull_policy: never
  mailpit:
    ports: !override []
'@
[IO.File]::WriteAllText((Join-Path $PWD '.local/repro.override.yml'), $override, [Text.UTF8Encoding]::new($false))
$composeArgs = @('--project-name', $project, '--env-file', '.local/repro.env', '-f', 'docker-compose.yml', '-f', '.local/repro.override.yml')
function Invoke-CheckCompose {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ComposeArguments)
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($Toolbox -and -not (Test-Path .local/compose-v2.exe)) {
            & py -3 -c 'import subprocess,sys; sys.exit(subprocess.call(sys.argv[1:]))' (Join-Path $PWD '.local/compose-v2.bin') --tls @composeArgs @ComposeArguments 2>&1 | ForEach-Object { "$_" }
        }
        elseif ($Toolbox) { & .local/compose-v2.exe --tls @composeArgs @ComposeArguments 2>&1 | ForEach-Object { "$_" } }
        else { & docker compose @composeArgs @ComposeArguments 2>&1 | ForEach-Object { "$_" } }
        $nativeExitCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
    if ($nativeExitCode -ne 0) { throw 'La comprobacion aislada ha fallado.' }
}
try {
    Invoke-CheckCompose -ComposeArguments @('up','--no-build','-d','--wait','--wait-timeout','120')
    Invoke-CheckCompose -ComposeArguments @('exec','-T','api','alembic','current')
    Invoke-CheckCompose -ComposeArguments @('exec','-T','api','python','-c', "import json,urllib.request; root='http://127.0.0.1:8000'; assert len(json.load(urllib.request.urlopen(root+'/categories')))==4; assert json.load(urllib.request.urlopen(root+'/articles'))['items']==[]; assert b'Foro' in urllib.request.urlopen('http://web:3000/').read(); print('Base nueva: migraciones, categorias y SSR correctos.')")
    Invoke-CheckCompose -ComposeArguments @('exec','-T','api','python','-m','app.manage','bootstrap')
    Invoke-CheckCompose -ComposeArguments @('restart','api','web')
    Invoke-CheckCompose -ComposeArguments @('up','--no-build','-d','--wait','--wait-timeout','120')
    Invoke-CheckCompose -ComposeArguments @('exec','-T','api','alembic','current')
    Write-Output 'Arranque limpio y reinicio verificados con volumen aislado.'
} finally {
    # Solo borra los volumenes de prueba del proyecto aleatorio creado arriba.
    Invoke-CheckCompose -ComposeArguments @('down','--volumes')
}
