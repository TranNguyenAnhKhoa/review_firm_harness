$dir = "data\test_perm_recreate"
New-Item -ItemType Directory -Path $dir -Force | Out-Null
$acl = (Get-Item $dir).GetAccessControl("Access")
$sidEveryone = New-Object System.Security.Principal.SecurityIdentifier("S-1-1-0")
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $sidEveryone,
    [System.Security.AccessControl.FileSystemRights]::FullControl,
    [System.Security.AccessControl.InheritanceFlags]"ContainerInherit, ObjectInherit",
    [System.Security.AccessControl.PropagationFlags]::None,
    [System.Security.AccessControl.AccessControlType]::Allow
)
$acl.AddAccessRule($rule)
try {
    (Get-Item $dir).SetAccessControl($acl)
    Write-Host "SET_ACL_SUCCESS"
} catch {
    Write-Host "SET_ACL_FAILED: $_"
}
Remove-Item $dir
