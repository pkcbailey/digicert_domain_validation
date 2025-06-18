# Load the CredentialManager module
Import-Module CredentialManager

# Define the credential target
$targetName = "cert-manager.com"

# Set up logging
$logFile = "domain_processing.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== Processing started at $timestamp ===" | Out-File $logFile

# Retrieve the credential
$credential = Get-StoredCredential -Target $targetName

if ($credential -ne $null -and $credential.UserName -eq "automation") {
    $username = $credential.UserName
    $password = $credential.GetNetworkCredential().Password

    # Load variables from ~/.ApiVault (as PowerShell-style key=value)
    $vaultFile = "$HOME/.ApiVault"
    $vars = @{}
    Get-Content $vaultFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
            $key, $value = $matches[1].Trim(), $matches[2].Trim().Trim('"')
            $vars[$key] = $value
        }
    }

    $CustomerUri = $vars["CustomerUri"]
    $orgID       = $vars["orgID"]

    # Read domain list
    $csvPath = "data.csv"
    $domains = Import-Csv $csvPath
    $results = @()
    $totalDomains = $domains.Count
    $currentDomain = 0

    foreach ($entry in $domains) {
        $currentDomain++
        $domain = $entry.domain
        $dnsHost = ""
        $point = ""
        $message = ""

        Write-Host "`nProcessing domain $currentDomain of $totalDomains: $domain"
        "Processing domain $currentDomain of $totalDomains: $domain" | Out-File $logFile -Append

        try {
            # -----------------------------
            # 1. Create Domain via REST API
            # -----------------------------
            $domainUri = 'https://cert-manager.com/api/domain/v1'
            $headers = @{
                'Content-Type' = 'application/json;charset=utf-8'
                'login'        = $username
                'password'     = $password
                'customerUri'  = $CustomerUri
            }

            $domainBody = @{
                name              = $domain
                description       = 'Domain created via REST API'
                active            = $true
                enabled           = $true
                includeSubdomains = $true
                delegations       = @(
                    @{
                        orgId                              = $orgID
                        certTypes                          = @('SSL')
                        domainCertificateRequestPrivileges = @('SUBDOMAIN', 'DOMAIN')
                    }
                )
            } | ConvertTo-Json -Depth 5

            $domainResponse = Invoke-RestMethod -Uri $domainUri -Method Post -Headers $headers -Body $domainBody
            $domainLog = "Domain Creation Response for $domain:`n$domainResponse"
            Write-Host $domainLog
            $domainLog | Out-File $logFile -Append

            # -----------------------------
            # 2. Submit DNS TXT Validation
            # -----------------------------
            $dnsUri = 'https://cert-manager.com/api/dcv/v1/validation/submit/domain/txt'
            $dnsBody = @{ domain = $domain } | ConvertTo-Json -Compress

            $dnsResponse = Invoke-RestMethod -Uri $dnsUri -Method Post -Headers $headers -Body $dnsBody
            $dnsLog = "DNS TXT Validation Response for $domain:`n$dnsResponse"
            Write-Host $dnsLog
            $dnsLog | Out-File $logFile -Append

            # Capture DNS validation response
            $dnsHost = $dnsResponse.host
            $point   = $dnsResponse.point
            $message = $dnsResponse.message
        }
        catch {
            $errorMessage = "ERROR processing ${domain}: $($_.Exception.Message)"
            Write-Host $errorMessage -ForegroundColor Red
            $errorMessage | Out-File $logFile -Append
            $message = $errorMessage
        }

        # Merge original and new fields
        $results += [pscustomobject]@{
            domain  = $domain
            host    = $dnsHost
            point   = $point
            message = $message
        }

        # Save progress after each domain
        $results | Export-Csv -Path $csvPath -NoTypeInformation
        Write-Host "Progress saved: $currentDomain of $totalDomains domains processed"
    }

    # Backup original CSV
    Copy-Item $csvPath "$csvPath.bak" -Force
    Write-Host "`n✅ data.csv has been updated. Original backed up as data.csv.bak"
    "Processing completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $logFile -Append

} else {
    $errorMessage = "Credential not found or username mismatch."
    Write-Warning $errorMessage
    $errorMessage | Out-File $logFile -Append
}