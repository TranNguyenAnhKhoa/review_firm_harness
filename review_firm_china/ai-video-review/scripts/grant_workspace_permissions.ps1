param (
    [string]$TargetDir = "d:\workplace_make_firm\review_firm_china\ai-video-review"
)

Write-Host "Target: $TargetDir"

$identities = @("Everyone", "ANH-KHOA\CodexSandboxUsers", "BUILTIN\Users", "ANH-KHOA\khoatna")

try {
    $acl = Get-Acl -LiteralPath $TargetDir
    foreach ($id in $identities) {
        try {
            $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                $id,
                [System.Security.AccessControl.FileSystemRights]::FullControl,
                [System.Security.AccessControl.InheritanceFlags]"ContainerInherit, ObjectInherit",
                [System.Security.AccessControl.PropagationFlags]::None,
                [System.Security.AccessControl.AccessControlType]::Allow
            )
            $acl.AddAccessRule($rule)
            Write-Host "Added rule for $id on root"
        } catch {
            Write-Warning "Could not add rule for $id : $_"
        }
    }
    Set-Acl -LiteralPath $TargetDir -AclObject $acl
    Write-Host "Successfully applied ACL to $TargetDir"
} catch {
    Write-Warning "Root Set-Acl failed: $_"
}

# Now apply to key subdirectories: input, output, data, .tmp
$subdirs = @("input", "output", "data", ".tmp", "config", "docs", "scripts", "src", "tests")
foreach ($sub in $subdirs) {
    $path = Join-Path $TargetDir $sub
    if (Test-Path -LiteralPath $path) {
        try {
            $acl = Get-Acl -LiteralPath $path
            foreach ($id in $identities) {
                try {
                    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
                        $id,
                        [System.Security.AccessControl.FileSystemRights]::FullControl,
                        [System.Security.AccessControl.InheritanceFlags]"ContainerInherit, ObjectInherit",
                        [System.Security.AccessControl.PropagationFlags]::None,
                        [System.Security.AccessControl.AccessControlType]::Allow
                    )
                    $acl.AddAccessRule($rule)
                } catch { }
            }
            Set-Acl -LiteralPath $path -AclObject $acl
            Write-Host "Successfully applied ACL to $sub"
        } catch {
            Write-Warning "Failed on $sub : $_"
        }
    }
}
