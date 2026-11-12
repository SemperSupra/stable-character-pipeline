# Original public-safe R3 native target validation. Fixed inputs only; ephemeral runner workspaces.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$resultRoot = Join-Path $here 'results'
New-Item -ItemType Directory -Path $resultRoot -Force | Out-Null
$scratch = Join-Path $env:RUNNER_TEMP ("geom-r3-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
$env:GOPATH = Join-Path $scratch 'go'
$env:GOMODCACHE = Join-Path $scratch 'gomodcache'
$env:GOCACHE = Join-Path $scratch 'gocache'
$env:GOTOOLCHAIN = 'go1.25.0'
$env:GOWORK = 'off'
function Assert-Exit([string]$message) {
    if ($LASTEXITCODE -ne 0) { throw "$message : exit $LASTEXITCODE" }
}
try {
    & go version
    Assert-Exit 'go version'
    & git --version
    Assert-Exit 'git version'
    $src = Join-Path $scratch 'source-sdfx'
    New-Item -ItemType Directory -Path $src -Force | Out-Null
    & git -C $src init -q
    Assert-Exit 'git init'
    & git -C $src remote add origin https://github.com/deadsy/sdfx.git
    Assert-Exit 'git remote'
    $wanted = 'a63cfbad6c5a0fe634ee2b393e970aaa7af7b866'
    & git -C $src fetch --no-tags --depth 1 origin $wanted
    Assert-Exit 'git fetch exact source'
    & git -C $src checkout --quiet --detach FETCH_HEAD
    Assert-Exit 'git detached checkout'
    $got = (& git -C $src rev-parse HEAD).Trim()
    Assert-Exit 'git rev-parse'
    if ($got -ne $wanted) { throw 'UPSTREAM_SHA_MISMATCH' }
    Set-Content -Path (Join-Path $resultRoot 'source-sha.txt') -Value $got -Encoding utf8NoBOM
    $dst = Join-Path $scratch 'consumer'
    New-Item -ItemType Directory -Path $dst -Force | Out-Null
    Copy-Item (Join-Path $here 'consumer/main.go') (Join-Path $dst 'main.go')
    Push-Location $dst
    try {
        & go mod init example.org/geometry-native-portability
        Assert-Exit 'go mod init'
        & go mod edit '-require=github.com/deadsy/sdfx@v0.0.0' ("-replace=github.com/deadsy/sdfx=" + $src)
        Assert-Exit 'go mod edit'
        & go mod tidy
        Assert-Exit 'go mod tidy'
        $binary = Join-Path $dst ('consumer' + $(if($IsWindows){'.exe'}else{''}))
        & go build -trimpath -o $binary .
        Assert-Exit 'go build'
        $first = Join-Path $resultRoot 'sdfx-first.json'
        $again = Join-Path $resultRoot 'sdfx-repeat.json'
        & $binary | Set-Content -Path $first -Encoding utf8NoBOM
        Assert-Exit 'donor execution'
        & $binary | Set-Content -Path $again -Encoding utf8NoBOM
        Assert-Exit 'donor re-execution'
        $h1 = (Get-FileHash -Path $first -Algorithm SHA256).Hash
        $h2 = (Get-FileHash -Path $again -Algorithm SHA256).Hash
        if ($h1 -ne $h2){ throw 'NONDETERMINISTIC_OUTPUT' }
        $oracle = Join-Path $here 'oracle/main.go'
        & go run $oracle $first | Set-Content -Path (Join-Path $resultRoot 'oracle.json') -Encoding utf8NoBOM
        Assert-Exit 'independent oracle'
        Get-Content (Join-Path $resultRoot 'oracle.json')
        Write-Output "NATIVE_PORTABILITY_R3_PASS source=$got sha256=$h1"
    } finally { Pop-Location }
} finally {
    # Clearing this runner-scoped cache avoids immutable Go module file cleanup errors.
    & go clean -modcache 2>$null | Out-Null
    try {
        Remove-Item -Path $scratch -Recurse -Force -ErrorAction Stop
        Write-Output 'TEMP_WORK_CLEANUP_PASS'
    } catch {
        # The entire hosted runner is disposed; preserve evidence if module files resist deletion.
        Write-Output 'TEMP_WORK_CLEANUP_INCOMPLETE'
    }
}
