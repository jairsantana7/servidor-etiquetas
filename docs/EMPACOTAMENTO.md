# Aplicativos para macOS, Windows e Linux

Os pacotes incluem o interpretador Python, o servidor HTTP, a interface no navegador e a biblioteca TiMini. Quem instala um pacote não precisa instalar Python. A aplicação abre a interface no navegador e mantém o servidor rodando enquanto seu processo estiver aberto.

## Plataformas

| Plataforma | Arquitetura | Distribuição |
| --- | --- | --- |
| macOS | Apple Silicon / arm64 | `.app` dentro de `.dmg` ou `.zip` |
| macOS | Intel / x86_64 | `.app` dentro de `.dmg` ou `.zip` |
| Windows | x86_64 | `.zip` com `.exe` e dependências |
| Linux | x86_64 | `.tar.gz` com executável e dependências |

Windows e Linux usam pacotes portáteis: extraia a pasta inteira e mantenha o executável junto de `_internal`. Não são instaladores MSI/DEB. A versão Linux é compilada em Ubuntu 22.04; compatibilidade com outras distribuições depende das bibliotecas do sistema. Windows ARM e Linux ARM não fazem parte da matriz inicial.

Os builds macOS não são notarizados nem assinados com uma identidade Apple Developer. Não foi incluído um certificado de assinatura Windows. Para distribuição com assinatura reconhecida pelo sistema, é necessário configurar os certificados correspondentes.

## Instalar e iniciar

- **macOS:** abra o DMG, arraste `ServidorEtiquetas.app` para Aplicativos e abra o aplicativo. Permita Bluetooth e acesso à rede local quando solicitado.
- **Windows:** extraia o ZIP e abra `ServidorEtiquetas.exe`. A janela do console permanece aberta; fechá-la encerra o servidor. Permita conexões de entrada no firewall conforme sua rede.
- **Linux:** extraia o arquivo, execute `chmod +x ServidorEtiquetas/ServidorEtiquetas` se necessário e execute `./ServidorEtiquetas/ServidorEtiquetas`. É necessário Bluetooth/BlueZ ativo e acesso ao serviço D-Bus do sistema.

Abra `http://localhost:8080`. Outros sistemas na rede podem acessar `http://IP-DO-COMPUTADOR:8080`. Leia o [guia da API](API.md).

**A primeira execução inicia em simulação.** Ligue a impressora, informe a configuração e só então ative impressão real.

## Configuração e fila persistentes

O pacote cria `settings.env`, `jobs.sqlite3` e `server.log` na pasta de dados do usuário, fora do executável:

| Sistema | Pasta padrão |
| --- | --- |
| macOS | `~/Library/Application Support/ServidorEtiquetas/` |
| Windows | `%LOCALAPPDATA%\ServidorEtiquetas\` |
| Linux | `~/.local/share/ServidorEtiquetas/` ou diretório indicado por `XDG_DATA_HOME` |

As imagens ficam em subpastas identificadas pelo ID do trabalho. Atualizar o aplicativo não apaga essa pasta. Feche o aplicativo, edite `settings.env` e abra novamente para aplicar alterações. Para uma PD01:

```dotenv
PRINT_BLUETOOTH=PD01
PRINT_DRY_RUN=0
PRINT_IMAGE_MODE=threshold
PRINT_DPI=200
PRINT_WIDTH_PX=384
PRINT_HEIGHT_MM=20
PRINT_TOKEN='SEU_TOKEN'
PRINT_BLUETOOTH_ADDRESS=
```

Em um computador novo, deixe `PRINT_BLUETOOTH_ADDRESS` vazio: o servidor descobre a impressora e mantém a conexão. O UUID BLE de um Mac não deve ser copiado para outro computador. `PRINT_MODEL` pode ficar vazio para a descoberta automática; com um endereço BLE configurado diretamente, o modelo padrão é `pd01_v5g`.

A configuração usa sintaxe `.env`, sem executar comandos de shell. Variáveis de ambiente do processo têm prioridade sobre o arquivo; opções de linha de comando têm prioridade sobre ambas. O endereço de rede e as credenciais deste projeto não são incluídos nos pacotes.

## Linha de comando

No Windows use `ServidorEtiquetas.exe`; no Linux use `./ServidorEtiquetas`; no macOS o executável fica dentro do aplicativo:

```sh
/Applications/ServidorEtiquetas.app/Contents/MacOS/ServidorEtiquetas --help
```

Opções disponíveis:

```text
--config CAMINHO      Usar arquivo .env específico
--data-dir CAMINHO    Usar outra pasta persistente
--host ENDERECO       Endereço de escuta HTTP
--port NUMERO         Porta HTTP
--no-browser          Não abrir navegador automaticamente
--simulate            Forçar simulação
--check               Conferir interface e catálogo sem conectar/imprimir
```

Exemplo para teste sem impressora:

```sh
./ServidorEtiquetas --simulate --port 8081 --no-browser
```

Uma segunda instância na mesma porta falha antes de abrir a sessão Bluetooth. Use apenas uma instância por impressora. Não há serviço de inicialização automática instalado: o aplicativo deve continuar aberto.

## Gerar pacotes pelo código-fonte

Com GNU Make e Python instalados, execute na raiz do projeto:

```sh
make start          # Instala dependências e inicia o servidor
make build          # Pacote nativo para o sistema atual
make build-macos    # Somente no macOS
make build-windows  # Somente no Windows
make build-linux    # Somente no Linux
make test
```

O Makefile cria e reutiliza `.venv`; preserva a configuração existente. `make install` prepara apenas as dependências da aplicação; `make build` instala também PyInstaller. Os alvos específicos verificam o sistema e recusam compilação cruzada. O padrão de Python é `python3.12` em macOS/Linux e `python` no Windows; substitua com `PYTHON=python3` ou o caminho do interpretador. No Linux, prefira `make build-linux PYTHON=python3` com o Python da distribuição.

No Windows, é necessário instalar GNU Make; se o comando for `mingw32-make`, use esse nome. Para gerar o pacote Windows, execute com Python nativo do Windows. WSL gera pacote Linux. As instruções diretas abaixo continuam disponíveis sem Make.

Use Python 3.12 no macOS/Windows. No Linux, prefira o Python da distribuição com suporte a sockets RFCOMM (Python 3.10 ou superior). Cada pacote deve ser gerado no sistema e arquitetura correspondentes; PyInstaller não faz compilação cruzada.

Crie um ambiente virtual e execute nele:

```sh
python -m venv .build-venv
# macOS/Linux:
.build-venv/bin/python packaging/build.py --install
# Windows:
.build-venv\Scripts\python.exe packaging\build.py --install
```

`packaging/build.py` obtém o TiMini no commit fixado `9bfc1b582c4d6492c74725f459a5843f8e8f66f8`, instala dependências quando solicitado e gera os arquivos em `dist/`. Se já existir outra versão em `vendor/TiMini-Print`, o build interrompe e informa a divergência em vez de substituir seu checkout.

Para testar os recursos de um pacote, execute seu binário com `--check --simulate --data-dir CAMINHO-TEMPORARIO`. Isso verifica imports, recursos da interface e catálogo do PD01, sem acessar Bluetooth ou gastar papel.

## GitHub Actions

O workflow `.github/workflows/packages.yml` gera quatro builds: macOS ARM64, macOS Intel, Windows x86_64 e Linux x86_64. Ele executa testes e a verificação dos recursos empacotados em cada sistema, depois disponibiliza os arquivos como artifacts.

Execute em **Actions → Pacotes macOS Windows Linux → Run workflow**, ou envie uma tag `v*`. O workflow não publica automaticamente uma release nem envia mensagens. As dependências nativas e o Bluetooth exigem teste físico em cada plataforma; o CI não tem uma PD01 conectada.

## Dependências e avisos

O pacote inclui os avisos e a licença do TiMini em `licenses/TiMini-Print` dentro dos recursos, além dos metadados das dependências. As licenças dos componentes continuam aplicáveis; este empacotamento não muda as licenças de bibliotecas como PyMuPDF. O código original do TiMini está disponível no repositório referenciado acima.

## Validação

A conexão e a impressão física com PD01 foram confirmadas no servidor pelo código-fonte no macOS. O pacote deve ser verificado separadamente com `--check`, teste da API em simulação e teste físico de Bluetooth. Um build bem-sucedido não garante a impressão em todos os adaptadores e sistemas.
