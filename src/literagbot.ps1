#Get-Content "./literagbot.config" | foreach-object -begin {$settings=@{}} -process { $k = [regex]::split($_,'='); if(($k[0].CompareTo("") -ne 0) -and ($k[0].StartsWith("[") -ne $True)) { $settings.Add($k[0], $k[1]) } }

$init = (Get-Content "./literagbot.config") | Select-String "INIT = True"

if ( $null -ne $init )
{
    Write-Output "INIT set to true"
    $python = & python -V 2>&1
    if ($python -lt 3)
    {
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.5/python-3.11.5.exe" -OutFile "c:/temp/python-3.11.5.exe"
        c:/temp/python-3.11.5.exe /quiet InstallAllUsers=0 InstallLauncherAllUsers=0 PrependPath=1 Include_test=0
        Remove-Item "c:/temp/python-3.11.5.exe" -Force
    }

    Write-Output "Installing pip..."
    python3 -m ensurepip --upgrade

    Write-Output "Installing virtualenv..."
    pip install virtualenv
    python -m virtualenv literagbot_env

    Write-Output "Activating virtualenv..."
    ./literagbot_env/Scripts/activate.ps1

    Write-Output "Installing dependencies..."
    pip install -r "./requirements.txt"

    Write-Output "Installing Vector Store..."
    .\literagbot_env\Scripts\python.exe "./scripts/literagbot_init.py"

    (Get-Content "./literagbot.config") | ForEach-Object {$_ -Replace 'INIT = True', 'INIT = False'} | Set-Content "./literagbot.config"
    
}
else {
    Write-Output "INIT set to false"
}

Write-Output "Initializing LiteRagBot..."
./literagbot_env/Scripts/activate.ps1
.\literagbot_env\Scripts\python.exe -m streamlit run "./scripts/literagbot_streamlit.py"