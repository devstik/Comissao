"""
Sistema de atualização automática
Verifica versões no GitHub Releases e baixa atualizações
"""
import requests
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from constants import APP_VERSION, GITHUB_REPO


def get_latest_version() -> Optional[Tuple[str, str, str]]:
    """
    Verifica a versão mais recente no GitHub Releases
    
    Returns:
        Tuple (versão, url_download, notas) ou None se erro
    """
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(api_url, timeout=5)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        version = data.get("tag_name", "").replace("v", "")
        notes = data.get("body", "Sem descrição")
        
        # Procura pelo arquivo .exe nos assets
        assets = data.get("assets", [])
        download_url = None
        
        for asset in assets:
            if asset.get("name", "").endswith(".exe"):
                download_url = asset.get("browser_download_url")
                break
        
        if not download_url:
            return None
        
        return (version, download_url, notes)
    
    except Exception as e:
        print(f"Erro ao verificar atualização: {e}")
        return None


def compare_versions(v1: str, v2: str) -> int:
    """
    Compara duas versões
    
    Returns:
        -1 se v1 < v2
         0 se v1 == v2
         1 se v1 > v2
    """
    try:
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]
        
        # Preenche com zeros se necessário
        while len(parts1) < len(parts2):
            parts1.append(0)
        while len(parts2) < len(parts1):
            parts2.append(0)
        
        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        
        return 0
    except:
        return 0


def has_update() -> Optional[Tuple[str, str, str]]:
    """
    Verifica se há atualização disponível
    
    Returns:
        Tuple (versão, url, notas) se houver atualização, None caso contrário
    """
    latest = get_latest_version()
    
    if not latest:
        return None
    
    version, url, notes = latest
    
    if compare_versions(APP_VERSION, version) < 0:
        return (version, url, notes)
    
    return None


def download_update(url: str, progress_callback=None) -> Optional[str]:
    """
    Baixa a atualização
    
    Args:
        url: URL do arquivo para download
        progress_callback: Função callback(bytes_downloaded, total_bytes)
    
    Returns:
        Caminho do arquivo baixado ou None se erro
    """
    try:
        response = requests.get(url, stream=True, timeout=30)
        
        if response.status_code != 200:
            return None
        
        total_size = int(response.headers.get('content-length', 0))
        
        # Salva na pasta temp
        temp_dir = Path(os.getenv('TEMP', '/tmp'))
        filename = url.split('/')[-1]
        filepath = temp_dir / filename
        
        downloaded = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)
        
        return str(filepath)
    
    except Exception as e:
        print(f"Erro ao baixar atualização: {e}")
        return None


def install_update(update_file: str) -> bool:
    """
    Instala a atualização (substitui o executável atual)
    
    Args:
        update_file: Caminho do novo executável
    
    Returns:
        True se sucesso, False se erro
    """
    try:
        current_exe = sys.executable
        
        # Se está rodando como script Python, não pode atualizar
        if not current_exe.endswith('.exe'):
            print("Atualização automática disponível apenas para executável")
            return False
        
        # Cria script batch para substituir o executável
        batch_script = Path(os.getenv('TEMP')) / 'update_comissys.bat'
        
        batch_content = f"""@echo off
echo Atualizando Comissys...
timeout /t 2 /nobreak > nul
taskkill /F /IM "{Path(current_exe).name}" > nul 2>&1
timeout /t 1 /nobreak > nul
copy /Y "{update_file}" "{current_exe}"
del "{update_file}"
start "" "{current_exe}"
del "%~f0"
"""
        
        with open(batch_script, 'w') as f:
            f.write(batch_content)
        
        # Executa o batch e fecha o aplicativo
        subprocess.Popen(['cmd', '/c', str(batch_script)], 
                        creationflags=subprocess.CREATE_NO_WINDOW)
        
        return True
    
    except Exception as e:
        print(f"Erro ao instalar atualização: {e}")
        return False


def check_and_notify():
    """
    Função auxiliar para verificar atualizações de forma assíncrona
    Retorna informações se houver atualização disponível
    """
    return has_update()
