param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "check.ps1") -BackendOnly:$BackendOnly -FrontendOnly:$FrontendOnly
