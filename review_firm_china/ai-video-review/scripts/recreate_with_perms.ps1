param(
    [string]$FolderPath = "d:\workplace_make_firm\review_firm_china\ai-video-review\data\handoff"
)

Write-Host "Re-creating with FullControl permissions: $FolderPath"

$sidEveryone = New-Object System.Security.Principal.SecurityIdentifier("S-1-1-0")
$sidUsers = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-32-545")
$currentUserSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User

$sidsToGrant = @($sidEveryone, $sidUsers, $currentUserSid)
$codexAccount = New-Object System.Security.Principal.NTAccount("ANH-KHOA\CodexSandboxUsers")
try {
    $sidsToGrant += $codexAccount.Translate([System.Security.Principal.SecurityIdentifier])
} catch {}

if (Test-Path -LiteralPath $FolderPath) {
    $parent = Split-Path -Parent $FolderPath
    $name = Split-Path -Leaf $FolderPath
    $tempPath = Join-Path $parent ("_tmp_old_" + $name)
    
    # Move old to temp
    Move-Item -LiteralPath $FolderPath -Destination $tempPath -Force
    
    # Create fresh folder
    New-Item -ItemType Directory -Path $FolderPath -Force | Out-Null
    
    # Apply FullControl to fresh folder
    $acl = (Get-Item -LiteralPath $FolderPath).GetAccessControl("Access")
    foreach ($sid in $sidsToGrant) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            [System.Security.AccessControl.InheritanceFlags]"ContainerInherit, ObjectInherit",
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
        $acl.AddAccessRule($rule)
    }
    (Get-Item -LiteralPath $FolderPath).SetAccessControl($acl)
    Write-Host "Set FullControl ACL on fresh $FolderPath successfully."
    
    # Copy all contents back
    Copy-Item -Path (Join-Path $tempPath "*") -Destination $FolderPath -Recurse -Force
    
    # Remove old temp
    Remove-Item -LiteralPath $tempPath -Recurse -Force
    Write-Host "Migrated all contents back into $FolderPath."
}
