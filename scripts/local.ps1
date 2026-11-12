param(
    [ValidateSet('Start', 'Stop', 'Status', 'Bootstrap', 'Tests', 'Browser')]
    [string]$Action = 'Start',
    [switch]$Toolbox
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Force .local | Out-Null
$operationLock = $null
try {
if ($Action -in @('Start', 'Stop', 'Bootstrap')) {
    try {
        $operationLock = [IO.File]::Open((Join-Path $PWD '.local/operation.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    } catch [IO.IOException] {
        throw 'Ya hay otra operacion local en curso. Espera a que termine antes de arrancar o parar.'
    }
}

function New-LocalSecret {
    $buffer = New-Object byte[] 36
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($buffer) } finally { $generator.Dispose() }
    return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+','-').Replace('/','_')
}

if (-not (Test-Path .env)) {
    $template = [IO.File]::ReadAllText((Join-Path $PWD '.env.example'))
    $template = $template.Replace('CAMBIAR_CONTRASENA_LARGA', (New-LocalSecret))
    $template = $template.Replace("EDITORIAL_API_TOKEN=", "EDITORIAL_API_TOKEN=$(New-LocalSecret)")
    $template = $template.Replace("EDITORIAL_PASSWORD=", "EDITORIAL_PASSWORD=$(New-LocalSecret)")
    [IO.File]::WriteAllText((Join-Path $PWD '.env'), $template, [Text.UTF8Encoding]::new($false))
    Write-Output 'Configuracion local creada; las credenciales no se muestran.'
}

if ($Toolbox) {
    $composeVersion = 'v2.39.4'
    $composePath = Join-Path $PWD '.local/compose-v2.exe'
    # En este equipo el nombre .exe no admite escritura; el mismo PE verificado
    # puede conservarse como .bin y lanzarse con CreateProcess desde Python.
    if (-not (Test-Path $composePath) -and (Test-Path .local/compose-v2.bin)) {
        $composePath = Join-Path $PWD '.local/compose-v2.bin'
    }
    $checksumPath = Join-Path $PWD '.local/compose-v2.sha256'
    $release = "https://github.com/docker/compose/releases/download/$composeVersion/docker-compose-windows-x86_64.exe"
    if (-not (Test-Path $composePath)) {
        & curl.exe -fL --silent --show-error $release -o "$composePath.download"
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar Compose.' }
        Move-Item -LiteralPath "$composePath.download" -Destination $composePath
    }
    if (-not (Test-Path $checksumPath)) {
        & curl.exe -fL --silent --show-error "$release.sha256" -o $checksumPath
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar el checksum.' }
    }
    $expected = [regex]::Match([IO.File]::ReadAllText($checksumPath), '[a-fA-F0-9]{64}').Value
    if (-not $expected -or (Get-FileHash -LiteralPath $composePath -Algorithm SHA256).Hash -ne $expected) {
        throw 'La comprobacion SHA256 de Compose ha fallado.'
    }
    $machineState = & docker-machine status default
    if ($machineState -ne 'Running') {
        & docker-machine start default
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo arrancar Docker Toolbox.' }
    }
    # El DNS guardado de esta VM queda obsoleto al cambiar de red.
    & docker-machine ssh default 'test -f /tmp/foroia-resolv.conf.before || sudo cp /etc/resolv.conf /tmp/foroia-resolv.conf.before'
    & docker-machine ssh default 'echo nameserver 10.0.2.3 | sudo tee /etc/resolv.conf' | Out-Null
    $machine = (& docker-machine inspect default | ConvertFrom-Json)
    $sshArgs = @('-N','-T','-p',"$($machine.Driver.SSHPort)",'-i', $machine.Driver.SSHKeyPath,
        '-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','ExitOnForwardFailure=yes')
    foreach ($mapping in @(@(23762,2376), @(3000,3000), @(8000,8000), @(8025,8025))) {
        if (-not (Get-NetTCPConnection -LocalPort $mapping[0] -State Listen -ErrorAction SilentlyContinue)) {
            $sshArgs += @('-L', "127.0.0.1:$($mapping[0]):127.0.0.1:$($mapping[1])")
        }
    }
    if ($sshArgs -contains '-L') {
        $sshArgs += 'docker@127.0.0.1'
        $tunnel = Start-Process ssh.exe -ArgumentList $sshArgs -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput .local/start-tunnel.out.log -RedirectStandardError .local/start-tunnel.err.log
        $tunnel.Id | Set-Content .local/start-tunnel.pid
        Start-Sleep -Milliseconds 500
        if ($tunnel.HasExited) { throw 'No se pudo establecer el tunel SSH. Revisa .local/start-tunnel.err.log.' }
    }
    $env:DOCKER_HOST = 'tcp://127.0.0.1:23762'
    Remove-Item Env:DOCKER_TLS_VERIFY -ErrorAction SilentlyContinue
}

function Invoke-LocalCompose {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ComposeArguments)
    # PowerShell 5.1 trata el progreso por stderr como error al redirigir logs.
    # La fuente de verdad para comandos nativos es su codigo de salida.
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($Toolbox -and $composePath.EndsWith('.bin')) {
            & py -3 -c 'import subprocess,sys; sys.exit(subprocess.call(sys.argv[1:]))' $composePath --tls @ComposeArguments 2>&1 | ForEach-Object { "$_" }
        }
        elseif ($Toolbox) { & $composePath --tls @ComposeArguments 2>&1 | ForEach-Object { "$_" } }
        else { & docker compose @ComposeArguments 2>&1 | ForEach-Object { "$_" } }
        $nativeExitCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
    if ($nativeExitCode -ne 0) { throw 'La operacion de Compose ha fallado.' }
}

switch ($Action) {
    'Start' {
        Invoke-LocalCompose -ComposeArguments @('up', '--build', '-d')
        Invoke-LocalCompose -ComposeArguments @('exec', '-T', 'api', 'python', '-m', 'app.manage', 'bootstrap')
        Invoke-LocalCompose -ComposeArguments @('ps')
        Write-Output 'Web: http://localhost:3000 | Cuenta: /cuenta | Correo local: http://localhost:8025'
    }
    'Bootstrap' { Invoke-LocalCompose -ComposeArguments @('exec', '-T', 'api', 'python', '-m', 'app.manage', 'bootstrap') }
    'Stop' { Invoke-LocalCompose -ComposeArguments @('down') }
    'Status' { Invoke-LocalCompose -ComposeArguments @('ps') }
    { $_ -in @('Tests','Browser') } {
        if (-not (Test-Path .local/venv/Scripts/python.exe)) { & py -3 -m venv .local/venv }
        & .local/venv/Scripts/python.exe -m pip install -r api/requirements-dev.txt
        if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de pruebas.' }
        $env:PYTHONPATH = Join-Path $PWD 'api'
        $env:FOROIA_LOCAL_HTTP = '1'
        if ($Action -eq 'Browser') {
            & .local/venv/Scripts/python.exe -m playwright install chromium
            if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar Chromium; revisa los certificados de confianza.' }
            $env:FOROIA_BROWSER = '1'
        }
        try {
            & .local/venv/Scripts/python.exe -m pytest -q
            if ($LASTEXITCODE -ne 0) { throw 'Hay pruebas fallidas.' }
        } finally {
            Remove-Item Env:FOROIA_LOCAL_HTTP -ErrorAction SilentlyContinue
            Remove-Item Env:FOROIA_BROWSER -ErrorAction SilentlyContinue
        }
    }
}
} finally {
    if ($null -ne $operationLock) { $operationLock.Dispose() }
}
