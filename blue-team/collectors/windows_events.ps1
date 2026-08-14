[CmdletBinding()]
param(
    [ValidateRange(1, 1440)]
    [int]$SinceMinutes = 15
)

$ErrorActionPreference = 'Stop'
$startTime = (Get-Date).AddMinutes(-$SinceMinutes)

function ConvertTo-SafeIdentifier {
    param([AllowNull()][string]$Value, [string]$Fallback = 'unknown')
    if ([string]::IsNullOrWhiteSpace($Value)) { return $Fallback }
    $safe = $Value -replace '[^A-Za-z0-9._:-]', '_'
    if ($safe.Length -gt 128) { $safe = $safe.Substring(0, 128) }
    if ($safe -notmatch '^[A-Za-z0-9]') { $safe = "x$safe" }
    return $safe
}

function Get-EventData {
    param([System.Diagnostics.Eventing.Reader.EventRecord]$Event)
    $data = @{}
    [xml]$xml = $Event.ToXml()
    foreach ($node in $xml.Event.EventData.Data) {
        $name = [string]$node.Name
        if ($name) { $data[$name] = [string]$node.'#text' }
    }
    return $data
}

$queries = @(
    @{ LogName = 'Security'; Id = @(1102, 4625, 4698, 4728, 4732, 4756) },
    @{ LogName = 'System'; Id = @(7045) },
    @{ LogName = 'Microsoft-Windows-Windows Defender/Operational'; Id = @(5001, 5007, 5010) }
)

foreach ($query in $queries) {
    try {
        $events = Get-WinEvent -FilterHashtable @{
            LogName = $query.LogName
            Id = $query.Id
            StartTime = $startTime
        } -ErrorAction Stop
    }
    catch [System.UnauthorizedAccessException] {
        Write-Warning "Access denied reading $($query.LogName); run from an approved elevated collection session."
        continue
    }
    catch [System.Exception] {
        Write-Warning "Unable to read $($query.LogName): $($_.Exception.Message)"
        continue
    }

    foreach ($record in $events) {
        $fields = Get-EventData -Event $record
        $eventType = 'windows_event'
        $source = if ($query.LogName -eq 'System') { 'windows-system' } elseif ($query.LogName -eq 'Security') { 'windows-security' } else { 'edr' }
        $attributes = [ordered]@{
            provider = [string]$record.ProviderName
            windows_event_id = [int]$record.Id
            channel = [string]$record.LogName
        }
        $user = $null

        switch ([int]$record.Id) {
            1102 { $eventType = 'audit_log_cleared' }
            4625 {
                $eventType = 'authentication_failed'
                $user = ConvertTo-SafeIdentifier -Value $fields['TargetUserName'] -Fallback 'unknown-user'
                if ($fields['IpAddress']) { $attributes['ip'] = $fields['IpAddress'] }
                if ($fields['LogonType']) { $attributes['logon_type'] = $fields['LogonType'] }
            }
            4698 {
                $eventType = 'scheduled_task_created'
                $attributes['hidden'] = $false
                if ($fields['TaskName']) { $attributes['task_name'] = $fields['TaskName'] }
            }
            { $_ -in @(4728, 4732, 4756) } {
                $eventType = 'group_membership_added'
                $group = [string]$fields['TargetUserName']
                $privilegedGroups = @('Administrators', 'Domain Admins', 'Enterprise Admins', 'Schema Admins')
                $attributes['group'] = $group
                $attributes['privileged'] = $group -in $privilegedGroups
                $user = ConvertTo-SafeIdentifier -Value $fields['MemberName'] -Fallback 'unknown-member'
            }
            7045 {
                $eventType = 'service_installed'
                $imagePath = [string]$fields['ImagePath']
                $attributes['service_name'] = [string]$fields['ServiceName']
                $attributes['image_path'] = $imagePath
                $attributes['user_writable_path'] = $imagePath -match '(?i)\\Users\\|\\ProgramData\\|\\Temp\\'
            }
            5001 {
                $eventType = 'security_control_changed'
                $attributes['control'] = 'defender_real_time_protection'
                $attributes['state'] = 'disabled'
            }
            5007 {
                $eventType = 'security_control_configuration'
                $attributes['control'] = 'defender_configuration'
            }
            5010 {
                $eventType = 'security_control_changed'
                $attributes['control'] = 'defender_scanning'
                $attributes['state'] = 'disabled'
            }
        }

        $channel = ConvertTo-SafeIdentifier -Value ([string]$record.LogName)
        $hostName = ConvertTo-SafeIdentifier -Value ([string]$record.MachineName) -Fallback 'unknown-host'
        $event = [ordered]@{
            event_id = "win-$channel-$($record.RecordId)"
            timestamp = $record.TimeCreated.ToUniversalTime().ToString('o')
            source = $source
            event_type = $eventType
            host = $hostName
            user = $user
            severity = 0
            attributes = $attributes
        }
        $event | ConvertTo-Json -Compress -Depth 6
    }
}
