param(
    [string]$AssemblyPath = 'C:\Program Files (x86)\Steam\steamapps\common\Stronghold Crusader Definitive Edition\Stronghold Crusader Definitive Edition_Data\Managed\Assembly-CSharp.dll'
)

# Reads PE metadata and method IL. Does not load/execute the inspected assembly.
$ErrorActionPreference = 'Stop'
$methodNames = @(
    'DLL_GetSaveRadar', 'DLL_UnpackRadarToARGB', 'DLL_SaveSaveGame',
    'getSaveRadar', 'unpackSavedRadar', 'SaveSaveGame',
    'GetRadarFromFile', 'GetRadarPreview', 'GetLoadSaveRadarPreview'
)
$typeNames = @('EngineInterface', 'MapFileManager')
$results = [System.Collections.Generic.List[object]]::new()
$stream = [System.IO.File]::OpenRead($AssemblyPath)
try {
    $pe = [System.Reflection.PortableExecutable.PEReader]::new($stream)
    $metadata = [System.Reflection.Metadata.PEReaderExtensions]::GetMetadataReader($pe)
    $module = $metadata.GetModuleDefinition()
    $moduleId = $metadata.GetGuid($module.Mvid).ToString()
    foreach ($typeHandle in $metadata.TypeDefinitions) {
        $type = $metadata.GetTypeDefinition($typeHandle)
        $typeName = $metadata.GetString($type.Name)
        if ($typeNames -notcontains $typeName) { continue }
        foreach ($methodHandle in $type.GetMethods()) {
            $method = $metadata.GetMethodDefinition($methodHandle)
            $methodName = $metadata.GetString($method.Name)
            if ($methodNames -notcontains $methodName) { continue }
            $entityHandle = [System.Reflection.Metadata.EntityHandle]$methodHandle
            $token = [System.Reflection.Metadata.Ecma335.MetadataTokens]::GetToken($entityHandle)
            $record = [ordered]@{
                Method = "$typeName.$methodName"
                Token = ('0x{0:X8}' -f $token)
                IlRva = ('0x{0:X8}' -f $method.RelativeVirtualAddress)
            }
            if ($method.RelativeVirtualAddress -gt 0) {
                $body = [System.Reflection.Metadata.PEReaderExtensions]::GetMethodBody($pe, $method.RelativeVirtualAddress)
                $record.IlHex = [System.BitConverter]::ToString($body.GetILBytes())
            } else {
                $import = $method.GetImport()
                if (-not $import.Name.IsNil) {
                    $record.Import = $metadata.GetString($import.Name)
                    $record.Library = $metadata.GetString($metadata.GetModuleReference($import.Module).Name)
                }
            }
            $results.Add($record)
        }
    }
} finally {
    if ($null -ne $pe) { $pe.Dispose() }
    $stream.Dispose()
}

[ordered]@{
    AssemblyPath = (Get-Item -LiteralPath $AssemblyPath).FullName
    Length = (Get-Item -LiteralPath $AssemblyPath).Length
    Sha256 = (Get-FileHash -LiteralPath $AssemblyPath -Algorithm SHA256).Hash
    ModuleVersionId = $moduleId
    Methods = $results
} | ConvertTo-Json -Depth 5
