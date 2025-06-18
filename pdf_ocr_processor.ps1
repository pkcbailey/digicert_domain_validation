# PDF OCR Processor
# Requires: Tesseract OCR, Ghostscript, and PowerShell 5.1 or later

# Configuration
$config = @{
    InputDirectory = ".\Input"
    OutputDirectory = ".\Output"
    TempDirectory = ".\Temp"
    TesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"
    GhostscriptPath = "C:\Program Files\gs\gs10.02.1\bin\gswin64c.exe"
    Languages = @("eng", "fra", "deu")  # Add more languages as needed
    DPI = 300
    ThreadCount = 4
}

# Create necessary directories if they don't exist
function Initialize-Directories {
    foreach ($dir in $config.InputDirectory, $config.OutputDirectory, $config.TempDirectory) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir | Out-Null
            Write-Host "Created directory: $dir"
        }
    }
}

# Check for required dependencies
function Test-Dependencies {
    $missingDeps = @()
    
    if (-not (Test-Path $config.TesseractPath)) {
        $missingDeps += "Tesseract OCR"
    }
    
    if (-not (Test-Path $config.GhostscriptPath)) {
        $missingDeps += "Ghostscript"
    }
    
    if ($missingDeps.Count -gt 0) {
        Write-Error "Missing dependencies: $($missingDeps -join ', ')"
        Write-Host "Please install the missing dependencies:"
        Write-Host "1. Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki"
        Write-Host "2. Ghostscript: https://www.ghostscript.com/releases/gsdnld.html"
        exit 1
    }
}

# Convert PDF to high-resolution images
function Convert-PDFToImages {
    param (
        [string]$InputFile,
        [string]$OutputDir
    )
    
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($InputFile)
    $outputPattern = Join-Path $OutputDir "$baseName-%d.png"
    
    $arguments = @(
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=png16m",
        "-r$($config.DPI)",
        "-sOutputFile=$outputPattern",
        $InputFile
    )
    
    & $config.GhostscriptPath $arguments
    
    return Get-ChildItem -Path $OutputDir -Filter "$baseName-*.png"
}

# Process a single image with OCR
function Process-ImageWithOCR {
    param (
        [string]$ImageFile,
        [string]$OutputFile,
        [string[]]$Languages
    )
    
    $langParam = $Languages -join '+'
    $arguments = @(
        $ImageFile,
        $OutputFile,
        "-l $langParam",
        "--dpi $($config.DPI)",
        "--oem 1",  # Use LSTM neural net
        "--psm 3"   # Automatic page segmentation
    )
    
    & $config.TesseractPath $arguments
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "OCR processing failed for $ImageFile"
        return $false
    }
    
    return $true
}

# Process a single PDF file
function Process-PDF {
    param (
        [string]$PdfFile,
        [string]$OutputDir
    )
    
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($PdfFile)
    $tempDir = Join-Path $config.TempDirectory $baseName
    
    if (-not (Test-Path $tempDir)) {
        New-Item -ItemType Directory -Path $tempDir | Out-Null
    }
    
    try {
        Write-Host "Processing $PdfFile..."
        
        # Convert PDF to images
        $images = Convert-PDFToImages -InputFile $PdfFile -OutputDir $tempDir
        
        # Process each image with OCR
        $textFiles = @()
        foreach ($image in $images) {
            $outputFile = Join-Path $tempDir ([System.IO.Path]::GetFileNameWithoutExtension($image))
            if (Process-ImageWithOCR -ImageFile $image.FullName -OutputFile $outputFile -Languages $config.Languages) {
                $textFiles += "$outputFile.txt"
            }
        }
        
        # Combine all text files
        $finalOutput = Join-Path $OutputDir "$baseName.txt"
        Get-Content $textFiles | Set-Content $finalOutput
        
        Write-Host "Successfully processed $PdfFile"
        return $true
    }
    catch {
        Write-Error "Error processing $PdfFile : $_"
        return $false
    }
    finally {
        # Clean up temporary files
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force
        }
    }
}

# Main processing function
function Start-OCRProcessing {
    param (
        [string]$InputDir = $config.InputDirectory,
        [string]$OutputDir = $config.OutputDirectory
    )
    
    # Initialize
    Initialize-Directories
    Test-Dependencies
    
    # Get all PDF files
    $pdfFiles = Get-ChildItem -Path $InputDir -Filter "*.pdf"
    
    if ($pdfFiles.Count -eq 0) {
        Write-Host "No PDF files found in $InputDir"
        return
    }
    
    Write-Host "Found $($pdfFiles.Count) PDF files to process"
    
    # Process files in parallel
    $pdfFiles | ForEach-Object -ThrottleLimit $config.ThreadCount -Parallel {
        $script:config = $using:config
        Process-PDF -PdfFile $_.FullName -OutputDir $using:OutputDir
    }
    
    Write-Host "Processing complete!"
}

# Start the processing
Start-OCRProcessing 