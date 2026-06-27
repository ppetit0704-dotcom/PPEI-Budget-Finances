"""
@author  : Philippe PETIT
@version : 1.0.4
@description : Lanceur PPEI-Emploi
"""
import streamlit.web.cli as stcli
from threading import Timer
import os, sys, webbrowser
import multiprocessing
import psutil
import threading


def open_browser():
    """Ouvre le navigateur après un court délai pour laisser le serveur démarrer."""
    webbrowser.open("http://localhost:8501")


def kill_port(port: int):
    """Tue proprement tout process écoutant sur le port donné."""
    killed = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.net_connections(kind='inet'):
                if conn.laddr.port == port:
                    proc.kill()
                    killed.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if killed:
        print(f"⛔ Process tués sur le port {port} : PID {killed}")
    else:
        print(f"✅ Port {port} libre.")


def get_resource_path(relative_path):
    """Chemin absolu vers la ressource — compatible PyInstaller et dev local."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    # Indispensable sur Windows pour éviter l'ouverture en cascade de fenêtres
    multiprocessing.freeze_support()

    app_path = get_resource_path("app.py")
    print(f"DEBUG: Recherche de app.py ici -> {app_path}")

    if not os.path.exists(app_path):
        print(f"Erreur : Impossible de trouver {app_path}")
        sys.exit(1)

    # Nettoyage du port avant lancement
    print("🔍 Vérification du port 8501...")
    kill_port(8501)

    print("🚀 Initialisation du Dashboard PPEI-Budget-Finances...")
    print("Veuillez patienter, le navigateur va s'ouvrir automatiquement.")

    # Ouverture du navigateur après délai
    Timer(8, open_browser).start()

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.port=8501",
        "--server.headless=true",
        "--global.developmentMode=false",
        "--server.runOnSave=false",
        "--server.fileWatcherType=none",
    ]
    sys.exit(stcli.main())
