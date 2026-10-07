# Servidor de impressão PD01 — 48,8 × 20 mm

Servidor local em Python que recebe PDF, PNG e JPEG pelo navegador ou API HTTP e envia imagens ao TiMini por uma conexão Bluetooth persistente. O computador que executa o servidor precisa ficar ligado e perto da impressora. Outros dispositivos acessam esse computador pela rede local.

## Aplicativos para macOS, Windows e Linux

Baixe os pacotes em [Releases](https://github.com/jairsantana7/servidor-etiquetas/releases). Veja o [guia de instalação e empacotamento](docs/EMPACOTAMENTO.md). Os pacotes incluem Python e as dependências; a API permanece igual.

## Comandos simples com Make

Com Python e GNU Make instalados:

```sh
make start          # Prepara dependências, inicia o servidor e abre o navegador
make build          # Gera o pacote para o sistema atual em dist/
make test           # Executa os testes
make help           # Lista os comandos
```

Também existem `make build-macos`, `make build-windows` e `make build-linux`, executados no sistema correspondente. No macOS/Linux, o padrão é `python3.12`; use `make start PYTHON=python3` se necessário. No Windows, o padrão é `python`. Para Linux, use o Python da distribuição com suporte RFCOMM.

Exemplo sem imprimir: `make start ARGS="--simulate --port 8081 --no-browser"`. A configuração `.env` existente é preservada; numa instalação nova, a primeira execução cria o arquivo em simulação. Encerre com Ctrl+C.

No Windows, instale GNU Make (ou use `mingw32-make` no lugar de `make`) e execute com Python nativo do Windows. WSL gera um pacote Linux. Sem Make, continuam disponíveis os [comandos Python diretos](docs/EMPACOTAMENTO.md).

## Executar pelo código-fonte no macOS

Em uma instalação nova, obtenha também o código do TiMini e suas dependências:

```sh
mkdir -p vendor
git clone https://github.com/Dejniel/TiMini-Print vendor/TiMini-Print
```

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r vendor/TiMini-Print/requirements.txt
cp .env.example .env
./start.sh
```

Abra http://localhost:8080. Em outros dispositivos, use `http://IP-DO-MAC:8080` e permita conexões de entrada no firewall do macOS. A configuração inicial **simula** o envio, permitindo conferir a fila e a prévia sem gastar etiquetas.

Edite `.env` e reinicie o servidor para aplicar mudanças. O arquivo é carregado como configuração de shell; use aspas em valores com espaços.

## Conectar a impressora

Ligue a impressora e permita o acesso Bluetooth para o terminal/aplicativo no macOS. Descubra o nome e modelo:

```sh
./timini.sh --help
./timini.sh --scan
./timini.sh --list-models
```

Configure `PRINT_BLUETOOTH='NOME DA IMPRESSORA'` em `.env`. `PRINT_MODEL`, `PRINT_CONFIG` e `PRINT_PAPER` são opcionais e devem corresponder ao modelo e aos presets suportados pelo TiMini. Após conferir a conexão, altere `PRINT_DRY_RUN=0` e reinicie. Envie uma única etiqueta para calibrar antes de um lote.

O projeto usa o código-fonte do [TiMini-Print](https://github.com/Dejniel/TiMini-Print), incluído nos pacotes de distribuição. Não é necessário baixar separadamente o executável TiMini.

## Medidas e limitações

Cada página é ajustada e centralizada em uma imagem de 384 × 157 pixels a 200 dpi, preservando a proporção e as margens. O TiMini recebe a imagem com recorte automático desativado e intervalo extra entre páginas zero. PDFs com páginas de aproximadamente 48,8 × 20 mm oferecem o melhor resultado; uma página A4 inteira ficará muito pequena.

A largura física final, o avanço do papel e a detecção do espaço entre etiquetas dependem da cabeça de impressão, do modelo e do preset do TiMini. A imagem preparada por si só não garante a medida física. É necessário validar com a impressora; ajuste o DPI/perfil/preset conforme o hardware. O usuário confirmou a saída de uma etiqueta no teste em preto e branco; medidas e avanço ainda precisam ser conferidos no papel.

Existe um único consumidor da fila. Os trabalhos persistem em `data/`. Em caso de falha, não há repetição automática, pois parte do lote pode já ter saído. Trabalhos em andamento durante um reinício são marcados como interrompidos. Confira o papel antes de reenviar. “Enviado” indica apenas que a biblioteca TiMini terminou o envio, sem confirmação física independente.

A interface mostra os 100 trabalhos mais recentes. Os arquivos ficam em `data/` até serem removidos manualmente com o servidor parado. Limites: 10 MB, 30 páginas e 20 cópias por trabalho. Use somente uma instância do servidor por impressora.

Esta versão recebe por HTTP; não aparece como impressora nativa no diálogo “Imprimir” dos programas. Essa integração exige uma camada IPP/CUPS adicional.

## API

Veja o [guia de integração com outros sistemas](docs/API.md) para endpoints, exemplos em cURL, Node.js e Python, autenticação, estados e tratamento de falhas/duplicações.

```sh
curl -X POST http://localhost:8080/api/jobs \
  -H 'Authorization: Bearer SEU_TOKEN' \
  -F 'file=@etiqueta.pdf' -F 'copies=1'

curl http://localhost:8080/api/jobs \
  -H 'Authorization: Bearer SEU_TOKEN'
```

`GET /api/jobs/ID/preview` retorna a prévia da primeira página. Configure `PRINT_TOKEN` para exigir autenticação nos endpoints de envio, consulta e prévia. O navegador tem um campo para informar esse token. Sem token, qualquer dispositivo que alcance a porta poderá enviar e consultar documentos. Restrinja o servidor à rede de confiança; HTTP não cifra os documentos nem o token. Não exponha diretamente à internet.

## Verificação

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Testes cobrem conversão, PDF com múltiplas páginas, prévia, fila, autenticação, recuperação após reinício, reutilização da conexão Bluetooth e reconexão após falha.

## Impressora identificada: PD01 / FunPrint

O catálogo consultado identifica `PD01` normalmente como `pd01_v5g`, com perfil `v5g_small_203`, DPI efetivo 200 e preset `default_384r` (384 pontos de largura, aproximadamente 48,8 mm). Esse perfil informa `can_print_label=false` e avanço após impressão; não há garantia de alinhamento automático em etiquetas pré-cortadas de 50 × 20 mm. O nome do perfil contém “203”, mas `dev_dpi` no catálogo é 200.

A configuração usa `PRINT_BLUETOOTH=PD01`, `PRINT_DPI=200`, `PRINT_WIDTH_PX=384` e `PRINT_HEIGHT_MM=20`. A imagem de layout tem 384 × 157 pixels, correspondendo à largura nativa do perfil, sem redimensionamento horizontal. A largura útil é aproximadamente 48,8 mm; a altura rasterizada é aproximadamente 19,94 mm. O avanço adicional do protocolo não faz parte dessa altura. A saída de uma etiqueta foi confirmada pelo usuário; as medidas físicas ainda precisam ser conferidas. Alterações de dimensões se aplicam a novos trabalhos; arquivos já na fila preservam o tamanho anterior.

O PD01 deste Mac foi reconhecido como `pd01_v5g`. Com o UUID BLE conhecido, a sessão usa esse modelo diretamente; em descoberta automática, o catálogo também considera variantes do PD01. Em outro aparelho/computador, descubra o destino novamente em vez de reutilizar o UUID local.

Fontes: https://github.com/Dejniel/TiMini-Print/blob/master/timiniprint/data/printer_models.json e https://github.com/Dejniel/TiMini-Print/blob/master/timiniprint/data/printer_profiles.json

## Execução pelo código-fonte para conectar ao PD01

Como o binário local encerrou com código 137, o servidor usa diretamente a biblioteca oficial armazenada em `vendor/TiMini-Print`, com as dependências instaladas no ambiente `.venv`. O wrapper `timini.sh` permite executar o CLI para diagnóstico; `TIMINI_CLI` não é utilizado pelo consumidor atual. Para reconstruir em outro computador, clone o repositório nessa pasta e instale `.venv/bin/pip install -r vendor/TiMini-Print/requirements.txt`.

Para descobrir a impressora, ligue o Bluetooth em Ajustes do Sistema, ligue a PD01, desconecte-a do FunPrint no celular e execute:

```sh
./timini.sh --scan -v
```

Permita o acesso Bluetooth se o macOS solicitar. Após a descoberta, configure `PRINT_DRY_RUN=0` no `.env` e reinicie `./start.sh` para ativar impressão real. O servidor mantém a ligação Bluetooth aberta entre envios.

A conexão real com a PD01 foi estabelecida e encerrada corretamente pelo teste ` .venv/bin/python check_printer.py`. O `.env` local passou a usar `PRINT_DRY_RUN=0`; novos documentos enviados pela interface serão impressos. A configuração de exemplo permanece em simulação. Uma impressão física foi confirmada pelo usuário; falta conferir suas medidas.

## Diagnóstico de envio sem impressão

O servidor usa `PRINT_IMAGE_MODE=threshold` para enviar etiquetas em preto e branco, preservando texto e QR sem tons de cinza. Cada envio registra o tempo e o estado da sessão em `data/ID/timini.log`. A interface acompanha o estado do documento enviado e as respostas da API não ficam em cache. O teste direto com esse modo terminou sem erro e o usuário confirmou que a etiqueta saiu.

## Conexão persistente

O consumidor da fila usa diretamente a biblioteca em `printer_session.py`, abre a sessão ao iniciar e a reutiliza para todas as páginas, cópias e trabalhos. O CLI `timini.sh` fica disponível apenas para diagnóstico. A conexão não é fechada após cada etiqueta.

`PRINT_BLUETOOTH_ADDRESS` guarda o UUID BLE descoberto neste Mac e permite abrir a sessão sem uma busca completa. Em outro computador, deixe esse valor vazio para descobrir o destino usando `PRINT_BLUETOOTH`. Sem endereço conhecido, a descoberta ocorre na abertura inicial; a sessão guarda o dispositivo para futuras reconexões.

A interface e `GET /api/printer` mostram o último estado conhecido da sessão. Se a conexão cair silenciosamente durante o repouso, o estado pode mudar apenas no próximo envio. Em erro, a sessão é fechada; o próximo trabalho tenta reconectar. O trabalho que falhou nunca é reenviado automaticamente, pois pode ter impresso parcialmente. Mantenha a impressora ligada e não conecte o FunPrint enquanto o servidor estiver usando a PD01.
