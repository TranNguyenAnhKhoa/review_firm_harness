$targetPaths = @(
    "d:\workplace_make_firm\review_firm_china\ai-video-review",
    "d:\workplace_make_firm\review_firm_china\ai-video-review\input",
    "d:\workplace_make_firm\review_firm_china\ai-video-review\input\scripts",
    "d:\workplace_make_firm\review_firm_china\ai-video-review\data",
    "d:\workplace_make_firm\review_firm_china\ai-video-review\data\timeline",
    "d:\workplace_make_firm\review_firm_china\ai-video-review\data\handoff",
    "d:\workplace_make_firm\review_firm_china\ai-video-review\.tmp"
)

# Well-known SIDs:
# Everyone: S-1-1-0
# BUILTIN\Users: S-1-5-32-545
$sidEveryone = New-Object System.Security.Principal.SecurityIdentifier("S-1-1-0")
$sidUsers = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-32-545")

# CodexSandboxUsers SID
$codexAccount = New-Object System.Security.Principal.NTAccount("ANH-KHOA\CodexSandboxUsers")
try {
    $sidCodex = $codexAccount.Translate([System.Security.Principal.SecurityIdentifier])
} catch {
    $sidCodex = $null
}

# Current user SID
$currentUserSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User

$sidsToGrant = @($sidEveryone, $sidUsers, $currentUserSid)
if ($sidCodex) {
    $sidsToGrant += $sidCodex
}

foreach ($p in $targetPaths) {
    if (-not (Test-Path -LiteralPath $p)) {
        New-Item -ItemType Directory -Path $p -Force | Out-Null
    }
    Write-Host "Processing: $p"
    try {
        $dirInfo = New-Object System.IO.DirectoryInfo($p)
        $acl = $dirInfo.GetAccessControl([System.Security.AccessControl.AccessControlSections]::Access)
        
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
        
        # Save directly via DirectoryInfo
        $dirInfo.SetAccessControl($acl)
        Write-Host "  -> SUCCESS on $p"
    } catch {
        Write-Warning "  -> ERROR on $p : $_"
    }
}
