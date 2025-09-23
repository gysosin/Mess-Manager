@echo off
echo Setting up Windows Task Scheduler for File Organizer...

:: Create the scheduled task
schtasks /create /tn "FileOrganizerDaily" /tr "python \"C:\projects\personal\file-organizer\file_organizer.py\"" /sc daily /st 09:00 /f

if %errorlevel% equ 0 (
    echo.
    echo ✓ Task scheduled successfully!
    echo   - Task Name: FileOrganizerDaily
    echo   - Schedule: Daily at 9:00 AM
    echo   - Script: C:\projects\personal\file-organizer\file_organizer.py
    echo.
    echo You can modify the schedule using Windows Task Scheduler GUI
    echo or run 'schtasks /change /tn "FileOrganizerDaily" /st HH:MM' to change time
) else (
    echo.
    echo ✗ Failed to create scheduled task
    echo Please run this script as Administrator
)

pause