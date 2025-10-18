# PowerShell script to test Azure Function file upload
# Usage: .\test_upload.ps1

# Configuration
$BaseUrl = "http://localhost:7071"
$UploadUrl = "$BaseUrl/api/upload"
$HealthUrl = "$BaseUrl/api/health"
$FilesUrl = "$BaseUrl/api/files"

# Colors for output
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-StatusMessage {
    param(
        [string]$Message,
        [string]$Status = "Info"
    )
    
    switch ($Status) {
        "Success" { Write-Host "✅ $Message" -ForegroundColor $Green }
        "Error" { Write-Host "❌ $Message" -ForegroundColor $Red }
        "Warning" { Write-Host "⚠️ $Message" -ForegroundColor $Yellow }
        "Info" { Write-Host "ℹ️ $Message" -ForegroundColor $Cyan }
        default { Write-Host $Message }
    }
}

function Test-HealthCheck {
    Write-StatusMessage "Testing health check..." "Info"
    
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 5
        Write-StatusMessage "Health check passed: $($response.status)" "Success"
        return $true
    }
    catch {
        Write-StatusMessage "Health check failed: $($_.Exception.Message)" "Error"
        return $false
    }
}

function New-SampleFile {
    $tempFile = [System.IO.Path]::GetTempFileName()
    $txtFile = [System.IO.Path]::ChangeExtension($tempFile, ".txt")
    
    $content = @"
Hello from Azure Function PowerShell test!
This is a sample file for upload testing.
Timestamp: $(Get-Date)
Content: Sample data for testing file upload functionality.
PowerShell Version: $($PSVersionTable.PSVersion)
Computer: $($env:COMPUTERNAME)
User: $($env:USERNAME)
"@
    
    $content | Out-File -FilePath $txtFile -Encoding UTF8
    Write-StatusMessage "Created sample file: $txtFile" "Info"
    return $txtFile
}

function Invoke-FileUpload {
    param([string]$FilePath)
    
    $fileName = Split-Path $FilePath -Leaf
    Write-StatusMessage "Uploading file: $fileName" "Info"
    
    try {
        # Read file content
        $fileBytes = [System.IO.File]::ReadAllBytes($FilePath)
        $fileContent = [System.Text.Encoding]::GetEncoding('ISO-8859-1').GetString($fileBytes)
        
        # Create multipart form data
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        
        $bodyLines = (
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
            "Content-Type: text/plain$LF",
            $fileContent,
            "--$boundary--$LF"
        ) -join $LF
        
        $headers = @{
            'Content-Type' = "multipart/form-data; boundary=$boundary"
            'X-User-ID' = 'powershell-test-user'
        }
        
        $response = Invoke-RestMethod -Uri $UploadUrl -Method Post -Body $bodyLines -Headers $headers -TimeoutSec 30
        
        Write-StatusMessage "Upload successful!" "Success"
        Write-Host "   File ID: $($response.file_id)" -ForegroundColor White
        Write-Host "   Size: $($response.file_size) bytes" -ForegroundColor White
        Write-Host "   Blob URL: $($response.blob_url)" -ForegroundColor White
        
        return $response.file_id
    }
    catch {
        Write-StatusMessage "Upload failed: $($_.Exception.Message)" "Error"
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "   Response: $responseBody" -ForegroundColor Red
        }
        return $null
    }
}

function Get-FileInformation {
    param([string]$FileId)
    
    Write-StatusMessage "Getting file info for ID: $FileId" "Info"
    
    try {
        $params = @{
            download_url = 'true'
            expiry_hours = '24'
        }
        
        $uri = "$FilesUrl/$FileId"
        $response = Invoke-RestMethod -Uri $uri -Method Get -Body $params -TimeoutSec 10
        
        Write-StatusMessage "File info retrieved!" "Success"
        Write-Host "   Filename: $($response.filename)" -ForegroundColor White
        Write-Host "   Original: $($response.original_filename)" -ForegroundColor White
        Write-Host "   Upload time: $($response.upload_timestamp)" -ForegroundColor White
        
        if ($response.download_url) {
            Write-Host "   Download URL available: Yes" -ForegroundColor White
        }
        
        return $true
    }
    catch {
        Write-StatusMessage "Failed to get file info: $($_.Exception.Message)" "Error"
        return $false
    }
}

# Main execution
Write-Host "🚀 PowerShell Azure Function Upload Test" -ForegroundColor Cyan
Write-Host "=" * 45 -ForegroundColor White

# Test health
if (-not (Test-HealthCheck)) {
    Write-StatusMessage "Health check failed - make sure the function is running" "Error"
    Write-Host "   Run: func start" -ForegroundColor Yellow
    exit 1
}

# Create and upload sample file
$sampleFile = New-SampleFile

try {
    # Upload file
    $fileId = Invoke-FileUpload -FilePath $sampleFile
    
    if ($fileId) {
        # Get file info
        $infoSuccess = Get-FileInformation -FileId $fileId
        
        if ($infoSuccess) {
            Write-StatusMessage "Test completed successfully!" "Success"
        } else {
            Write-StatusMessage "Test partially failed during file info retrieval" "Warning"
        }
    } else {
        Write-StatusMessage "Test failed during upload" "Error"
        exit 1
    }
}
finally {
    # Clean up
    if (Test-Path $sampleFile) {
        Remove-Item $sampleFile -Force
        Write-StatusMessage "Cleaned up sample file" "Info"
    }
}

Write-Host "`n🎉 PowerShell test completed!" -ForegroundColor Green