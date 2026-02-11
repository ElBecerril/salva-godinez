#Requires -Version 5.1
<#
.SYNOPSIS
    Buscador de Archivos Excel Perdidos
    by El_Becerril

.DESCRIPTION
    Busca archivos Excel perdidos usando multiples estrategias:
    papelera, disco completo, temporales, recientes y shadow copies.
#>

# ── Configuracion ──────────────────────────────────────────────────────────────

$ExcelExtensions = @('.xlsx', '.xls', '.xlsm', '.xlsb', '.csv')
$RecoveryPaths = @(
    "$env:APPDATA\Microsoft\Excel"
    "$env:LOCALAPPDATA\Microsoft\Office\UnsavedFiles"
    $env:TEMP
)
$RecentPath = "$env:APPDATA\Microsoft\Windows\Recent"
$SkipDirs = @('$Recycle.Bin', 'System Volume Information', 'Windows', '$WinREAgent', 'Recovery')

# ── Utilidades ─────────────────────────────────────────────────────────────────

function Format-FileSize {
    param([long]$Bytes)
    if ($Bytes -lt 1KB) { return "$Bytes B" }
    if ($Bytes -lt 1MB) { return "{0:N1} KB" -f ($Bytes / 1KB) }
    if ($Bytes -lt 1GB) { return "{0:N1} MB" -f ($Bytes / 1MB) }
    return "{0:N1} GB" -f ($Bytes / 1GB)
}

function Show-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "  ____                           _            " -ForegroundColor Cyan
    Write-Host " | __ ) _   _ ___  ___ __ _ ___| | ___  _ __ " -ForegroundColor Cyan
    Write-Host " |  _ \| | | / __|/ __/ _' / __| |/ _ \| '__|" -ForegroundColor Cyan
    Write-Host " | |_) | |_| \__ \ (_| (_| \__ \ | (_) | |   " -ForegroundColor Cyan
    Write-Host " |____/ \__,_|___/\___\__,_|___/_|\___/|_|   " -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Buscador de Archivos Excel Perdidos" -ForegroundColor White
    Write-Host "  by El_Becerril" -ForegroundColor DarkGray
    Write-Host ""
}

function Show-Results {
    param(
        [array]$Results,
        [string]$Title = "Resultados"
    )

    Write-Host ""
    Write-Host "  === $Title ===" -ForegroundColor Yellow
    Write-Host ""

    if ($Results.Count -eq 0) {
        Write-Host "  No se encontraron archivos." -ForegroundColor DarkYellow
        Write-Host ""
        return
    }

    # Header
    Write-Host ("  {0,-4} {1,-35} {2,-55} {3,10} {4,-17} {5}" -f "#", "Nombre", "Ruta", "Tamano", "Fecha", "Origen") -ForegroundColor Cyan
    Write-Host ("  " + ("-" * 140)) -ForegroundColor DarkGray

    for ($i = 0; $i -lt $Results.Count; $i++) {
        $r = $Results[$i]
        $nombre = $r.Nombre
        $ruta = $r.Ruta
        if ($nombre.Length -gt 33) { $nombre = $nombre.Substring(0, 30) + "..." }
        if ($ruta.Length -gt 53) { $ruta = "..." + $ruta.Substring($ruta.Length - 50) }

        $color = if ($r.Origen -match "Papelera") { "Red" }
                 elseif ($r.Origen -match "Temp|Auto") { "Magenta" }
                 elseif ($r.Origen -match "Recientes") { "DarkYellow" }
                 elseif ($r.Origen -match "Shadow") { "DarkCyan" }
                 else { "White" }

        Write-Host ("  {0,-4} {1,-35} {2,-55} {3,10} {4,-17} {5}" -f (($i+1).ToString()), $nombre, $ruta, $r.Tamano, $r.Fecha, $r.Origen) -ForegroundColor $color
    }

    Write-Host ""
    Write-Host "  Total: $($Results.Count) archivo(s) encontrado(s)" -ForegroundColor Green
    Write-Host ""
}

function Invoke-RestoreFile {
    param([array]$Results)

    if ($Results.Count -eq 0) { return }

    Write-Host "  Puedes copiar un archivo encontrado a otra ubicacion." -ForegroundColor Cyan
    $choice = Read-Host "  Numero del archivo a copiar (0 para omitir)"

    if (-not $choice -or $choice -eq '0') { return }

    $idx = [int]$choice - 1
    if ($idx -lt 0 -or $idx -ge $Results.Count) {
        Write-Host "  Numero invalido." -ForegroundColor Red
        return
    }

    $selected = $Results[$idx]
    $source = $selected.Ruta

    if (-not (Test-Path $source)) {
        Write-Host "  El archivo ya no existe en: $source" -ForegroundColor Red
        return
    }

    $defaultDest = [Environment]::GetFolderPath('Desktop')
    $destDir = Read-Host "  Carpeta destino (Enter = $defaultDest)"
    if (-not $destDir) { $destDir = $defaultDest }

    if (-not (Test-Path $destDir -PathType Container)) {
        Write-Host "  La carpeta no existe: $destDir" -ForegroundColor Red
        return
    }

    $destFile = Join-Path $destDir $selected.Nombre

    # Evitar sobreescribir
    if (Test-Path $destFile) {
        $base = [System.IO.Path]::GetFileNameWithoutExtension($selected.Nombre)
        $ext = [System.IO.Path]::GetExtension($selected.Nombre)
        $counter = 1
        do {
            $destFile = Join-Path $destDir "${base}_recuperado${counter}${ext}"
            $counter++
        } while (Test-Path $destFile)
    }

    try {
        Copy-Item -Path $source -Destination $destFile -Force
        Write-Host ""
        Write-Host "  Archivo copiado exitosamente a: $destFile" -ForegroundColor Green
        Write-Host ""
    }
    catch {
        Write-Host "  Error al copiar: $_" -ForegroundColor Red
    }
}

# ── Buscadores ─────────────────────────────────────────────────────────────────

function Search-RecycleBin {
    param([string]$NameFilter = "")

    Write-Host "  Buscando en papelera de reciclaje..." -ForegroundColor Green
    $results = @()

    try {
        $shell = New-Object -ComObject Shell.Application
        $folder = $shell.NameSpace(0x0a)
        if ($null -eq $folder) { return $results }

        $items = $folder.Items()
        $nameLower = $NameFilter.ToLower()

        foreach ($item in $items) {
            $name = $folder.GetDetailsOf($item, 0)
            $ext = [System.IO.Path]::GetExtension($name).ToLower()

            if ($ext -notin $ExcelExtensions) { continue }
            if ($nameLower -and $name.ToLower() -notlike "*$nameLower*") { continue }

            $results += [PSCustomObject]@{
                Nombre = $name
                Ruta   = $folder.GetDetailsOf($item, 1)
                Tamano = $folder.GetDetailsOf($item, 3)
                Fecha  = $folder.GetDetailsOf($item, 2)
                Origen = "Papelera de reciclaje"
            }
        }
    }
    catch {
        Write-Host "  Error accediendo a la papelera: $_" -ForegroundColor DarkYellow
    }

    Write-Host "    $($results.Count) encontrado(s) en papelera" -ForegroundColor DarkGray
    return $results
}

function Search-DiskByName {
    param(
        [string]$NameFilter,
        [switch]$RecentOnly,
        [int]$Days = 30
    )

    Write-Host "  Escaneando discos..." -ForegroundColor Green
    $results = @()
    $nameLower = $NameFilter.ToLower()
    $cutoff = (Get-Date).AddDays(-$Days)
    $drives = [System.IO.DriveInfo]::GetDrives() | Where-Object { $_.IsReady -and $_.DriveType -ne 'Network' }
    $scanned = 0

    foreach ($drive in $drives) {
        $root = $drive.RootDirectory.FullName
        Write-Host "    Disco $root" -ForegroundColor DarkGray

        # Usar Get-ChildItem con -Recurse y filtrado eficiente
        foreach ($ext in $ExcelExtensions) {
            try {
                $files = Get-ChildItem -Path $root -Filter "*$ext" -Recurse -File -ErrorAction SilentlyContinue

                foreach ($f in $files) {
                    # Saltar directorios del sistema
                    $skip = $false
                    foreach ($sd in $SkipDirs) {
                        if ($f.FullName -like "*\$sd\*") { $skip = $true; break }
                    }
                    if ($skip) { continue }

                    if ($nameLower -and $f.Name.ToLower() -notlike "*$nameLower*") { continue }
                    if ($RecentOnly -and $f.LastWriteTime -lt $cutoff) { continue }

                    $scanned++
                    if ($scanned % 50 -eq 0) {
                        Write-Host "`r    Encontrados: $($results.Count) | Escaneados: $scanned   " -NoNewline -ForegroundColor DarkGray
                    }

                    $results += [PSCustomObject]@{
                        Nombre = $f.Name
                        Ruta   = $f.FullName
                        Tamano = Format-FileSize $f.Length
                        Fecha  = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
                        Origen = "Disco ($($drive.Name.TrimEnd('\')))"
                    }
                }
            }
            catch { }
        }
    }

    Write-Host "`r    $($results.Count) encontrado(s) en discos                " -ForegroundColor DarkGray
    return $results
}

function Search-TempFiles {
    param([string]$NameFilter = "")

    Write-Host "  Buscando en archivos temporales / autorecuperacion..." -ForegroundColor Green
    $results = @()
    $nameLower = $NameFilter.ToLower()

    foreach ($basePath in $RecoveryPaths) {
        if (-not (Test-Path $basePath)) { continue }

        try {
            $files = Get-ChildItem -Path $basePath -Recurse -File -ErrorAction SilentlyContinue

            foreach ($f in $files) {
                $ext = $f.Extension.ToLower()
                $name = $f.Name.ToLower()

                # Archivos Excel normales o temporales (~$*.xlsx, *.xar, *.asd)
                $isExcelTemp = ($ext -in $ExcelExtensions) -or
                               ($name -like '~`$*' -and ($ext -in $ExcelExtensions -or $ext -in '.tmp','.xlk')) -or
                               ($name -like '~*' -and ($ext -in $ExcelExtensions -or $ext -in '.tmp','.xlk')) -or
                               ($ext -in '.xar', '.asd')

                if (-not $isExcelTemp) { continue }
                if ($nameLower -and $name -notlike "*$nameLower*") { continue }

                $results += [PSCustomObject]@{
                    Nombre = $f.Name
                    Ruta   = $f.FullName
                    Tamano = Format-FileSize $f.Length
                    Fecha  = $f.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
                    Origen = "Autorecuperacion / Temp"
                }
            }
        }
        catch { }
    }

    Write-Host "    $($results.Count) encontrado(s) en temporales" -ForegroundColor DarkGray
    return $results
}

function Search-RecentFiles {
    param([string]$NameFilter = "")

    Write-Host "  Revisando archivos recientes de Windows..." -ForegroundColor Green
    $results = @()
    $nameLower = $NameFilter.ToLower()

    if (-not (Test-Path $RecentPath)) { return $results }

    try {
        $shell = New-Object -ComObject WScript.Shell
        $lnkFiles = Get-ChildItem -Path $RecentPath -Filter "*.lnk" -File -ErrorAction SilentlyContinue

        foreach ($lnk in $lnkFiles) {
            try {
                $shortcut = $shell.CreateShortcut($lnk.FullName)
                $target = $shortcut.TargetPath

                if (-not $target) { continue }

                $ext = [System.IO.Path]::GetExtension($target).ToLower()
                if ($ext -notin $ExcelExtensions) { continue }

                $targetName = [System.IO.Path]::GetFileName($target)
                if ($nameLower -and $targetName.ToLower() -notlike "*$nameLower*") { continue }

                $exists = Test-Path $target
                $estado = if ($exists) { "Existe" } else { "NO encontrado" }

                if ($exists) {
                    $fi = Get-Item $target -ErrorAction SilentlyContinue
                    $tamano = Format-FileSize $fi.Length
                    $fecha = $fi.LastWriteTime.ToString("yyyy-MM-dd HH:mm")
                }
                else {
                    $tamano = "N/A"
                    $fecha = "N/A"
                }

                $results += [PSCustomObject]@{
                    Nombre = $targetName
                    Ruta   = $target
                    Tamano = $tamano
                    Fecha  = $fecha
                    Origen = "Recientes ($estado)"
                    Existe = $exists
                }
            }
            catch { }
        }
    }
    catch {
        Write-Host "  Error leyendo recientes: $_" -ForegroundColor DarkYellow
    }

    Write-Host "    $($results.Count) encontrado(s) en recientes" -ForegroundColor DarkGray
    return $results
}

function Search-ShadowCopies {
    param(
        [string]$NameFilter,
        [string]$OriginalPath = ""
    )

    Write-Host "  Revisando shadow copies (VSS)..." -ForegroundColor Green
    $results = @()

    # Verificar si somos admin
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "    Requiere permisos de administrador - omitiendo" -ForegroundColor DarkYellow
        return $results
    }

    try {
        $shadows = Get-WmiObject Win32_ShadowCopy -ErrorAction SilentlyContinue
        if (-not $shadows) { return $results }

        $nameLower = $NameFilter.ToLower()

        foreach ($shadow in $shadows) {
            $shadowPath = $shadow.DeviceObject + "\"
            $shadowDate = $shadow.InstallDate.Substring(0, 8)
            $shadowDate = "$($shadowDate.Substring(0,4))-$($shadowDate.Substring(4,2))-$($shadowDate.Substring(6,2))"

            # Buscar en Users
            $searchRoot = "${shadowPath}Users"
            if (-not (Test-Path $searchRoot)) { continue }

            foreach ($ext in $ExcelExtensions) {
                try {
                    $files = Get-ChildItem -Path $searchRoot -Filter "*$ext" -Recurse -File -Depth 5 -ErrorAction SilentlyContinue

                    foreach ($f in $files) {
                        if ($nameLower -and $f.Name.ToLower() -notlike "*$nameLower*") { continue }

                        $results += [PSCustomObject]@{
                            Nombre = $f.Name
                            Ruta   = $f.FullName
                            Tamano = Format-FileSize $f.Length
                            Fecha  = $shadowDate
                            Origen = "Shadow Copy (VSS)"
                        }
                    }
                }
                catch { }
            }
        }
    }
    catch {
        Write-Host "    Error accediendo a shadow copies: $_" -ForegroundColor DarkYellow
    }

    Write-Host "    $($results.Count) encontrado(s) en shadow copies" -ForegroundColor DarkGray
    return $results
}

# ── Deduplicar ─────────────────────────────────────────────────────────────────

function Remove-Duplicates {
    param([array]$Results)
    $seen = @{}
    $unique = @()
    foreach ($r in $Results) {
        if (-not $seen.ContainsKey($r.Ruta)) {
            $seen[$r.Ruta] = $true
            $unique += $r
        }
    }
    return $unique
}

# ── Opciones del menu ─────────────────────────────────────────────────────────

function Invoke-SearchByName {
    $name = Read-Host "  Nombre (o parte del nombre) del archivo"
    if (-not $name) {
        Write-Host "  Debes ingresar un nombre." -ForegroundColor Red
        return
    }

    $all = @()
    $all += @(Search-RecycleBin -NameFilter $name)
    $all += @(Search-TempFiles -NameFilter $name)
    $all += @(Search-RecentFiles -NameFilter $name)
    $all += @(Search-DiskByName -NameFilter $name)
    $all += @(Search-ShadowCopies -NameFilter $name)
    $all = Remove-Duplicates $all

    Show-Results -Results $all -Title "Resultados para '$name'"
    Invoke-RestoreFile -Results $all
}

function Invoke-RecentExcel {
    $all = @()
    $all += @(Search-DiskByName -NameFilter "" -RecentOnly -Days 30)
    if ($all.Count -gt 0) {
        $all = $all | Sort-Object Fecha -Descending
    }
    Show-Results -Results $all -Title "Archivos Excel recientes (ultimos 30 dias)"
    Invoke-RestoreFile -Results $all
}

function Invoke-RecycleBinOnly {
    $name = Read-Host "  Filtrar por nombre (dejar vacio para ver todos)"
    $results = @(Search-RecycleBin -NameFilter $name)
    Show-Results -Results $results -Title "Archivos Excel en la Papelera"
    Invoke-RestoreFile -Results $results
}

function Invoke-TempFilesOnly {
    $name = Read-Host "  Filtrar por nombre (dejar vacio para ver todos)"
    $results = @(Search-TempFiles -NameFilter $name)
    Show-Results -Results $results -Title "Archivos Temporales / Autorecuperacion"
    Invoke-RestoreFile -Results $results
}

function Invoke-RecentWindowsOnly {
    $name = Read-Host "  Filtrar por nombre (dejar vacio para ver todos)"
    $results = @(Search-RecentFiles -NameFilter $name)
    Show-Results -Results $results -Title "Archivos Recientes de Windows"
    Invoke-RestoreFile -Results $results
}

function Invoke-FullSearch {
    $name = Read-Host "  Nombre (o parte del nombre) del archivo"
    if (-not $name) {
        Write-Host "  Debes ingresar un nombre." -ForegroundColor Red
        return
    }

    $all = @()
    $all += @(Search-RecycleBin -NameFilter $name)
    $all += @(Search-TempFiles -NameFilter $name)
    $all += @(Search-RecentFiles -NameFilter $name)
    $all += @(Search-DiskByName -NameFilter $name)
    $all += @(Search-ShadowCopies -NameFilter $name)
    $all = Remove-Duplicates $all

    Show-Results -Results $all -Title "Busqueda completa para '$name'"
    Invoke-RestoreFile -Results $all
}

# ── Main ───────────────────────────────────────────────────────────────────────

function Main {
    while ($true) {
        Show-Banner

        Write-Host "  +---------------------------------------------------+" -ForegroundColor DarkGray
        Write-Host "  |             Menu Principal                        |" -ForegroundColor Yellow
        Write-Host "  +---------------------------------------------------+" -ForegroundColor DarkGray
        Write-Host "  |  1 - Buscar por nombre de archivo                 |" -ForegroundColor White
        Write-Host "  |  2 - Buscar todos los Excel recientes (30 dias)   |" -ForegroundColor White
        Write-Host "  |  3 - Revisar papelera de reciclaje                |" -ForegroundColor White
        Write-Host "  |  4 - Revisar archivos temporales / autorecup.     |" -ForegroundColor White
        Write-Host "  |  5 - Revisar archivos recientes de Windows        |" -ForegroundColor White
        Write-Host "  |  6 - Busqueda completa (todas las opciones)       |" -ForegroundColor White
        Write-Host "  |  0 - Salir                                        |" -ForegroundColor White
        Write-Host "  +---------------------------------------------------+" -ForegroundColor DarkGray
        Write-Host ""

        $choice = Read-Host "  Selecciona una opcion"

        switch ($choice) {
            '1' { Invoke-SearchByName }
            '2' { Invoke-RecentExcel }
            '3' { Invoke-RecycleBinOnly }
            '4' { Invoke-TempFilesOnly }
            '5' { Invoke-RecentWindowsOnly }
            '6' { Invoke-FullSearch }
            '0' {
                Write-Host ""
                Write-Host "  Hasta luego!" -ForegroundColor Cyan
                return
            }
            default { Write-Host "  Opcion no valida." -ForegroundColor Red }
        }

        Write-Host ""
        Read-Host "  Presiona Enter para volver al menu"
    }
}

# Ejecutar
Main
