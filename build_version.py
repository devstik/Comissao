"""
Script para gerar nova versão automaticamente
Incrementa a versão, atualiza constants.py e gera o executável
"""
import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    """Lê a versão atual do constants.py"""
    constants_file = Path(__file__).parent / "constants.py"
    
    with open(constants_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    match = re.search(r'APP_VERSION\s*=\s*["\'](\d+\.\d+\.\d+)["\']', content)
    
    if match:
        return match.group(1)
    
    return "1.0.0"


def parse_version(version_str):
    """Converte string de versão em tupla (major, minor, patch)"""
    parts = version_str.split('.')
    return tuple(int(p) for p in parts)


def increment_version(version_str, part='patch'):
    """
    Incrementa a versão
    
    Args:
        version_str: Versão atual (ex: "1.0.3")
        part: Parte a incrementar ('major', 'minor', 'patch')
    
    Returns:
        Nova versão como string
    """
    major, minor, patch = parse_version(version_str)
    
    if part == 'major':
        major += 1
        minor = 0
        patch = 0
    elif part == 'minor':
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
    
    return f"{major}.{minor}.{patch}"


def update_constants(new_version):
    """Atualiza a versão no constants.py"""
    constants_file = Path(__file__).parent / "constants.py"
    
    with open(constants_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(
        r'APP_VERSION\s*=\s*["\'](\d+\.\d+\.\d+)["\']',
        f'APP_VERSION = "{new_version}"',
        content
    )
    
    with open(constants_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✓ constants.py atualizado para versão {new_version}")


def build_executable():
    """Gera o executável usando PyInstaller"""
    print("\n🔨 Gerando executável...")
    print("-" * 50)
    
    result = subprocess.run([
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name', 'Comissys',
        '--icon=icons/app.ico',
        'main.py'
    ], capture_output=False)
    
    if result.returncode == 0:
        print("-" * 50)
        print("✓ Executável gerado com sucesso!")
        return True
    else:
        print("✗ Erro ao gerar executável")
        return False


def main():
    """Processo principal"""
    print("=" * 50)
    print("  GERADOR DE NOVA VERSÃO - Comissys")
    print("=" * 50)
    print()
    
    # Obtém versão atual
    current_version = get_current_version()
    print(f"Versão atual: {current_version}")
    print()
    
    # Pergunta qual tipo de incremento
    print("Qual tipo de atualização?")
    print("  1. PATCH  - Correções de bugs (1.0.3 → 1.0.4)")
    print("  2. MINOR  - Novas funcionalidades (1.0.3 → 1.1.0)")
    print("  3. MAJOR  - Mudanças grandes (1.0.3 → 2.0.0)")
    print("  4. Cancelar")
    print()
    
    choice = input("Escolha [1-4]: ").strip()
    
    if choice == '1':
        increment_type = 'patch'
    elif choice == '2':
        increment_type = 'minor'
    elif choice == '3':
        increment_type = 'major'
    else:
        print("\nCancelado pelo usuário")
        return
    
    # Calcula nova versão
    new_version = increment_version(current_version, increment_type)
    
    print()
    print(f"Nova versão será: {new_version}")
    confirm = input("\nConfirmar e gerar executável? [S/n]: ").strip().lower()
    
    if confirm and confirm != 's':
        print("\nCancelado pelo usuário")
        return
    
    print()
    print("=" * 50)
    
    # Atualiza constants.py
    update_constants(new_version)
    
    # Gera executável
    if build_executable():
        print()
        print("=" * 50)
        print("  ✓ PROCESSO CONCLUÍDO COM SUCESSO!")
        print("=" * 50)
        print()
        print(f"Versão: {new_version}")
        print(f"Executável: dist\\Comissys.exe")
        print()
        print("Próximos passos:")
        print(f"  1. Teste o executável")
        print(f"  2. Commit: git add . && git commit -m \"v{new_version}\"")
        print(f"  3. Crie Release no GitHub com tag: v{new_version}")
        print(f"  4. Anexe o arquivo dist\\Comissys.exe ao Release")
        print()
    else:
        # Reverte a versão se falhou
        update_constants(current_version)
        print("\n✗ Processo falhou. Versão revertida.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelado pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Erro: {e}")
        sys.exit(1)
