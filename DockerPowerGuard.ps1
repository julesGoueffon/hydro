# Script : DockerPowerGuard.ps1
# Ce script empêche la mise en veille tant que le processus Docker est actif.

while($true) {
    # Vérifie si le processus backend de Docker est en cours d'exécution
    $dockerProcess = Get-Process -Name "com.docker.backend" -ErrorAction SilentlyContinue

    if ($dockerProcess) {
        # Empêche la mise en veille système tant que le processus est détecté
        powercfg /requestsoverride PROCESS "com.docker.backend.exe" DISPLAY SYSTEM
        Write-Host "Docker est actif, mise en veille bloquée." -ForegroundColor Green
    } else {
        # Autorise Windows à gérer la veille normalement
        powercfg /requestsoverride PROCESS "com.docker.backend.exe"
        Write-Host "Docker est inactif, veille autorisée." -ForegroundColor Yellow
    }

    # Pause de 60 secondes pour ne pas surcharger le CPU
    Start-Sleep -Seconds 60
}