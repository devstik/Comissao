# Sistema de Atualização Automática

## Como funciona

O sistema verifica automaticamente se há novas versões disponíveis no GitHub Releases ao iniciar. Se houver, exibe um dialog permitindo que o usuário baixe e instale a atualização com um clique.

## Como publicar uma nova versão

### 1. Gerar nova versão automaticamente

Execute o script que faz tudo automaticamente:

```bash
# Opção 1: Usando o .bat
build_exe.bat

# Opção 2: Diretamente com Python
python build_version.py
```

O script irá:
- ✅ Mostrar a versão atual
- ✅ Perguntar qual tipo de atualização (PATCH/MINOR/MAJOR)
- ✅ Incrementar automaticamente a versão em `constants.py`
- ✅ Gerar o executável
- ✅ Mostrar os próximos passos

**Tipos de atualização:**
- **PATCH** (1.0.3 → 1.0.4): Correções de bugs
- **MINOR** (1.0.3 → 1.1.0): Novas funcionalidades
- **MAJOR** (1.0.3 → 2.0.0): Mudanças grandes/incompatíveis

O executável será gerado em `dist/Comissys.exe`

### 2. Criar Release no GitHub

1. Acesse: https://github.com/devstik/Comissao/releases/new

2. Preencha:
   - **Tag version**: `v1.0.3` (usar o mesmo número da versão no código)
   - **Release title**: `Versão 1.0.3 - Nome descritivo`
   - **Description**: Liste as mudanças dessa versão:
     ```markdown
     ## Novidades
     - ✨ Nova funcionalidade X
     - 🐛 Corrigido bug Y
     - 🎨 Melhorias na interface Z
     
     ## Correções
     - Corrigido problema com...
     ```

3. **Anexar o executável**:
   - Clique em "Attach binaries"
   - Selecione o arquivo `dist/Comissys.exe`

4. Marque como "Latest release" (versão mais recente)

5. Clique em **"Publish release"**

### 3. Teste a atualização

Quando os usuários iniciarem o sistema, após 2 segundos será verificado se há atualização disponível. Se houver:
- Um dialog será exibido com as notas da versão
- O usuário pode escolher "Baixar e Instalar" ou "Agora Não"
- Se aceitar, o download será feito com barra de progresso
- Após o download, o sistema será atualizado e reiniciado automaticamente

## Estrutura de Versionamento

Use versionamento semântico: `MAJOR.MINOR.PATCH`

- **MAJOR**: Mudanças incompatíveis
- **MINOR**: Novas funcionalidades (compatível)
- **PATCH**: Correções de bugs

Exemplos:
- `1.0.0` → `1.0.1` (correção)
- `1.0.1` → `1.1.0` (nova funcionalidade)
- `1.1.0` → `2.0.0` (mudança grande/incompatível)

## Arquivos do Sistema de Atualização

- `constants.py` - Define a versão atual e repositório
- `utils/updater.py` - Lógica de verificação e download
- `ui/update_dialog.py` - Interface do dialog de atualização
- `main.py` - Integração com o sistema principal

## Fluxo de Atualização

```
1. Sistema inicia
2. Após 2s, verifica GitHub Releases
3. Se versão > versão atual:
   a. Exibe dialog com notas
   b. Usuário aceita atualizar
   c. Download com progresso
   d. Cria script batch para substituir exe
   e. Fecha aplicativo
   f. Script substitui exe
   g. Script reinicia aplicativo
   h. Script se auto-deleta
```

## Vantagens

✅ Usuários sempre têm a versão mais recente  
✅ Não precisa ir fisicamente instalar  
✅ Processo automático e seguro  
✅ Controle total sobre quando atualizar  
✅ Histórico de versões no GitHub  
