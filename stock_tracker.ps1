# Stock Tracker PowerShell Script
# Requires PowerShell 5.1 or later

# Configuration
$configFile = "config.json"
$stocksFile = "stocks.json"
$csvFile = "stocks.csv"
$reportFile = "$env:USERPROFILE\Desktop\stock_report.xlsx"
$textReportFile = "$env:USERPROFILE\Desktop\stock_report.txt"
$finnhubApiKey = "d09t8r9r01qus8rfa1ogd09t8r9r01qus8rfa1p0"

# Load configuration
function Load-Config {
    param (
        [string]$ConfigFile
    )
    try {
        return Get-Content $ConfigFile | ConvertFrom-Json
    }
    catch {
        Write-Error "Error loading config file: $_"
        exit 1
    }
}

# Load stocks from JSON or CSV
function Load-Stocks {
    if (Test-Path $csvFile) {
        $stocks = Import-Csv $csvFile
    }
    elseif (Test-Path $stocksFile) {
        $stocks = Get-Content $stocksFile | ConvertFrom-Json
    }
    else {
        Write-Error "No stock data found"
        exit 1
    }
    return $stocks
}

# Get current stock price from Yahoo Finance
function Get-CurrentPrice {
    param (
        [string]$Symbol
    )
    try {
        $stock = Invoke-RestMethod "https://query1.finance.yahoo.com/v8/finance/chart/$Symbol"
        $price = $stock.chart.result[0].meta.regularMarketPrice
        $change = $stock.chart.result[0].meta.regularMarketChange
        $changePercent = $stock.chart.result[0].meta.regularMarketChangePercent
        
        return @{
            Price = $price
            Change = $change
            ChangePercent = $changePercent
        }
    }
    catch {
        Write-Warning "Error fetching price for $Symbol : $_"
        return @{
            Price = 0
            Change = 0
            ChangePercent = 0
        }
    }
}

# Get Finnhub rating
function Get-FinnhubRating {
    param (
        [string]$Symbol
    )
    try {
        $url = "https://finnhub.io/api/v1/stock/recommendation?symbol=$Symbol&token=$finnhubApiKey"
        $response = Invoke-RestMethod $url
        
        if ($response) {
            $latest = $response[0]
            return @{
                StrongBuy = $latest.strongBuy
                Buy = $latest.buy
                Hold = $latest.hold
                Sell = $latest.sell
                StrongSell = $latest.strongSell
                Period = $latest.period
            }
        }
    }
    catch {
        Write-Warning "Error getting Finnhub rating for $Symbol : $_"
    }
    
    return @{
        StrongBuy = 0
        Buy = 0
        Hold = 0
        Sell = 0
        StrongSell = 0
        Period = "N/A"
    }
}

# Calculate consensus rating
function Get-ConsensusRating {
    param (
        [hashtable]$Rating
    )
    
    $totalRatings = $Rating.StrongBuy + $Rating.Buy + $Rating.Hold + $Rating.Sell + $Rating.StrongSell
    
    if ($totalRatings -gt 0) {
        $ratingScore = (
            ($Rating.StrongBuy * 5) +
            ($Rating.Buy * 4) +
            ($Rating.Hold * 3) +
            ($Rating.Sell * 2) +
            ($Rating.StrongSell * 1)
        ) / $totalRatings
        
        switch ($ratingScore) {
            { $_ -ge 4.5 } { return "Strong Buy" }
            { $_ -ge 3.5 } { return "Buy" }
            { $_ -ge 2.5 } { return "Hold" }
            { $_ -ge 1.5 } { return "Sell" }
            default { return "Strong Sell" }
        }
    }
    
    return "No Ratings"
}

# Generate Excel report
function Generate-ExcelReport {
    param (
        [array]$Performance
    )
    
    # Create Excel COM object
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $workbook = $excel.Workbooks.Add()
    $worksheet = $workbook.Worksheets.Item(1)
    
    # Write headers
    $headers = @(
        "Ticker", "Shares", "Purchase Date", "Purchase Price", "Current Price",
        "Change", "Change %", "Purchase Value", "Current Value", "Gain/Loss ($)",
        "Gain/Loss (%)", "Consensus Rating", "Strong Buy", "Buy", "Hold",
        "Sell", "Strong Sell", "Rating Period"
    )
    
    for ($i = 0; $i -lt $headers.Count; $i++) {
        $worksheet.Cells.Item(1, $i + 1) = $headers[$i]
    }
    
    # Write data
    $row = 2
    foreach ($stock in $Performance) {
        $col = 1
        foreach ($header in $headers) {
            $worksheet.Cells.Item($row, $col) = $stock.$header
            $col++
        }
        $row++
    }
    
    # Auto-fit columns
    $usedRange = $worksheet.UsedRange
    $usedRange.EntireColumn.AutoFit()
    
    # Save and close
    $workbook.SaveAs($reportFile)
    $workbook.Close()
    $excel.Quit()
    
    # Clean up COM objects
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($worksheet) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($workbook) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($excel) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}

# Generate text report
function Generate-TextReport {
    param (
        [array]$Performance
    )
    
    $report = @"
==========================================
STOCK PORTFOLIO REPORT
==========================================
Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
==========================================

"@
    
    foreach ($stock in $Performance) {
        if ($stock.Ticker -ne "TOTAL") {
            $report += @"

Stock: $($stock.Ticker)
Shares: $($stock.Shares)
Purchase Date: $($stock.'Purchase Date')
Purchase Price: `$$($stock.'Purchase Price':N2)
Current Price: `$$($stock.'Current Price':N2)
Today's Change: $($stock.Change:N2) ($($stock.'Change %':N2)%)
Purchase Value: `$$($stock.'Purchase Value':N2)
Current Value: `$$($stock.'Current Value':N2)
Total Gain/Loss: `$$($stock.'Gain/Loss ($)':N2) ($($stock.'Gain/Loss (%)':N2)%)

Analyst Ratings:
Consensus: $($stock.'Consensus Rating')
Strong Buy: $($stock.'Strong Buy')
Buy: $($stock.Buy)
Hold: $($stock.Hold)
Sell: $($stock.Sell)
Strong Sell: $($stock.'Strong Sell')
Rating Period: $($stock.'Rating Period')
------------------------------------------
"@
        }
    }
    
    # Add summary
    $total = $Performance | Where-Object { $_.Ticker -eq "TOTAL" }
    $report += @"

PORTFOLIO SUMMARY
==========================================
Total Investment: `$$($total.'Purchase Value':N2)
Current Value: `$$($total.'Current Value':N2)
Total Gain/Loss: `$$($total.'Gain/Loss ($)':N2) ($($total.'Gain/Loss (%)':N2)%)
==========================================
"@
    
    $report | Out-File -FilePath $textReportFile -Encoding UTF8
}

# Main script
Write-Host "Starting stock tracker..."

# Load configuration and stocks
$config = Load-Config $configFile
$stocks = Load-Stocks

# Calculate performance
$performance = @()
foreach ($stock in $stocks) {
    $currentPrice = Get-CurrentPrice $stock.ticker
    $finnhubRating = Get-FinnhubRating $stock.ticker
    $consensusRating = Get-ConsensusRating $finnhubRating
    
    $purchaseValue = $stock.shares * $stock.purchase_price
    $currentValue = $stock.shares * $currentPrice.Price
    $gainLoss = $currentValue - $purchaseValue
    $gainLossPercent = ($gainLoss / $purchaseValue) * 100
    
    $performance += [PSCustomObject]@{
        "Ticker" = $stock.ticker
        "Shares" = $stock.shares
        "Purchase Date" = $stock.purchase_date
        "Purchase Price" = $stock.purchase_price
        "Current Price" = $currentPrice.Price
        "Change" = $currentPrice.Change
        "Change %" = $currentPrice.ChangePercent
        "Purchase Value" = $purchaseValue
        "Current Value" = $currentValue
        "Gain/Loss ($)" = $gainLoss
        "Gain/Loss (%)" = $gainLossPercent
        "Consensus Rating" = $consensusRating
        "Strong Buy" = $finnhubRating.StrongBuy
        "Buy" = $finnhubRating.Buy
        "Hold" = $finnhubRating.Hold
        "Sell" = $finnhubRating.Sell
        "Strong Sell" = $finnhubRating.StrongSell
        "Rating Period" = $finnhubRating.Period
    }
}

# Add total row
$totalPurchaseValue = ($performance | Measure-Object -Property "Purchase Value" -Sum).Sum
$totalCurrentValue = ($performance | Measure-Object -Property "Current Value" -Sum).Sum
$totalGainLoss = $totalCurrentValue - $totalPurchaseValue
$totalGainLossPercent = ($totalGainLoss / $totalPurchaseValue) * 100

$performance += [PSCustomObject]@{
    "Ticker" = "TOTAL"
    "Shares" = ""
    "Purchase Date" = ""
    "Purchase Price" = ""
    "Current Price" = ""
    "Change" = ""
    "Change %" = ""
    "Purchase Value" = $totalPurchaseValue
    "Current Value" = $totalCurrentValue
    "Gain/Loss ($)" = $totalGainLoss
    "Gain/Loss (%)" = $totalGainLossPercent
    "Consensus Rating" = ""
    "Strong Buy" = ""
    "Buy" = ""
    "Hold" = ""
    "Sell" = ""
    "Strong Sell" = ""
    "Rating Period" = ""
}

# Generate reports
Write-Host "Generating reports..."
Generate-ExcelReport $performance
Generate-TextReport $performance

Write-Host "Reports generated successfully!"
Write-Host "Excel report saved to: $reportFile"
Write-Host "Text report saved to: $textReportFile" 