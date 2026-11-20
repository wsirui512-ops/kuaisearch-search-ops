<#
.SYNOPSIS
  Install Apache Spark for the local engine check (no admin rights needed).

.DESCRIPTION
  Downloads spark-4.3.0-bin-hadoop3 from a mirror, unpacks it into .spark/,
  and replaces bin/spark-submit.cmd with a direct-JVM launcher. The bundled
  launcher loses the classpath when SPARK_HOME contains non-ASCII characters
  (for example a Chinese project folder), which surfaces as
  "ClassNotFoundException: org.apache.spark.deploy.SparkSubmit".

  Requires Java 17+ on PATH or JAVA_HOME. No administrator rights, no Docker.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/setup_spark.ps1
#>
param(
    [string]$Version = "4.3.0",
    [string]$Mirror = "https://mirrors.huaweicloud.com/apache/spark"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root ".spark"
$sparkHome = Join-Path $target "spark-$Version-bin-hadoop3"
$archive = Join-Path $root ".work\spark-$Version-bin-hadoop3.tgz"

if (-not (Test-Path (Join-Path $sparkHome "jars"))) {
    New-Item -ItemType Directory -Force (Split-Path $archive) | Out-Null
    New-Item -ItemType Directory -Force $target | Out-Null
    $url = "$Mirror/spark-$Version/spark-$Version-bin-hadoop3.tgz"
    Write-Host "Downloading $url"
    if (-not (Test-Path $archive) -or (Get-Item $archive).Length -lt 500MB) {
        Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
    }
    Write-Host "Extracting to $target"
    tar -xzf $archive -C $target
}

$launcher = Join-Path $sparkHome "bin\spark-submit.cmd"
if (-not (Test-Path "$launcher.orig")) {
    Copy-Item $launcher "$launcher.orig" -Force
}
$javaHome = if ($env:JAVA_HOME) { $env:JAVA_HOME } else { "" }
$wrapper = @"
@echo off
rem Direct-JVM launcher: the stock launcher loses the classpath when SPARK_HOME
rem contains non-ASCII characters.
if "%JAVA_HOME%"=="" set "JAVA_HOME=$javaHome"
"%JAVA_HOME%\bin\java" -Xmx2g -cp "%SPARK_HOME%\jars\*" org.apache.spark.deploy.SparkSubmit %*
"@
Set-Content -Path $launcher -Value $wrapper -Encoding ASCII

Write-Host ""
Write-Host "SPARK_HOME = $sparkHome"
Write-Host "Next: python scripts/spark_check.py"
