# Integração com outros sistemas

A API recebe documentos pela rede local, prepara cada página no tamanho configurado e coloca o trabalho em uma fila persistente. Um único consumidor envia as etiquetas à PD01 por uma conexão Bluetooth mantida aberta entre trabalhos.

Um sistema de produtos, laboratório, estoque ou pedidos pode gerar um PDF com texto e QR Code e enviar esse arquivo automaticamente. O sistema de origem não precisa acessar o Bluetooth: precisa alcançar o servidor HTTP no Mac.

## Endereço e configuração

No próprio Mac, use `http://localhost:8080`. Em outros computadores, use `http://IP-DO-MAC:8080`. Na configuração utilizada durante a implantação, o endereço era `http://192.168.0.122:8080`; ele pode mudar. Para uma integração estável, configure uma reserva DHCP no roteador ou um nome de rede estável.

O Mac precisa permanecer ligado, com Bluetooth ativo e acesso à PD01. Configure `.env` e reinicie o servidor para aplicar alterações:

```dotenv
PRINT_HOST=0.0.0.0
PRINT_PORT=8080
PRINT_DRY_RUN=0
PRINT_BLUETOOTH=PD01
PRINT_DPI=200
PRINT_WIDTH_PX=384
PRINT_HEIGHT_MM=20
PRINT_IMAGE_MODE=threshold
PRINT_TOKEN='SEU_TOKEN'
```

`PRINT_DRY_RUN=1` processa a fila sem imprimir. A configuração de exemplo inicia em simulação; a configuração local usada na implantação foi ativada para impressão real.

## Autenticação

Quando `PRINT_TOKEN` está preenchido, todos os endpoints `/api/` exigem este cabeçalho:

```http
Authorization: Bearer SEU_TOKEN
```

Se o token estiver vazio, a API aceita requisições sem autenticação. Não inclua o token na URL ou em código público. HTTP não cifra o arquivo nem o token: mantenha o acesso restrito à rede de confiança; para acesso externo, use uma solução com HTTPS e controle de acesso.

A API não configura CORS. Os exemplos JavaScript abaixo são para execução no servidor do sistema integrador, com Node.js. Uma página hospedada em outra origem deve enviar o documento por seu backend ou configurar uma política CORS apropriada.

## Fluxo recomendado

1. Gere uma etiqueta por página, preferencialmente em PDF com aproximadamente 48,8 × 20 mm.
2. Envie o arquivo com `POST /api/jobs`.
3. Guarde o `id` retornado junto ao produto, amostra ou pedido no sistema de origem.
4. Consulte a fila periodicamente e encontre o trabalho pelo `id`.
5. Trate `sent`, `simulated`, `failed` e `interrupted` como estados finais. Para falhas ou interrupções, confira a impressão física antes de decidir pelo reenvio.

Uma resposta HTTP 202 confirma que o documento foi preparado e registrado na fila. Ela não confirma a impressão nem que a PD01 está conectada naquele instante.

## Endpoints disponíveis

| Método | Caminho | Resultado |
| --- | --- | --- |
| POST | `/api/jobs` | Recebe documento e cria um trabalho |
| GET | `/api/jobs` | Lista os 100 trabalhos mais recentes, do mais novo ao mais antigo |
| GET | `/api/jobs/{id}/preview` | PNG da primeira página preparada |
| GET | `/api/printer` | Último estado conhecido da sessão Bluetooth |

Não existe atualmente `GET /api/jobs/{id}`. Para acompanhar um trabalho, procure seu `id` na lista. Em volume alto, ele pode sair dos 100 resultados; a ausência na lista não significa falha ou exclusão do banco.

### Enviar documento

Use `multipart/form-data`, com os campos:

| Campo | Obrigatório | Valor |
| --- | --- | --- |
| `file` | Sim | Arquivo PDF, PNG ou JPEG |
| `copies` | Não | Inteiro de 1 a 20; padrão 1 |

Não envie JSON com um caminho de arquivo: o servidor precisa receber os bytes do documento. Ao usar `FormData`, deixe o cliente gerar o `Content-Type` com o boundary multipart.

```bash
curl --fail-with-body --request POST 'http://IP-DO-MAC:8080/api/jobs' \
  --header 'Authorization: Bearer SEU_TOKEN' \
  --form 'file=@etiqueta.pdf' \
  --form 'copies=1'
```

Resposta HTTP **202**, com ID ilustrativo:

```json
{
  "id": "df3e72c025b24d699e4ad418228bde52",
  "status": "queued",
  "pages": 1,
  "copies": 1
}
```

`pages × copies` indica a quantidade de páginas/etiquetas solicitadas. Um PDF de três páginas com duas cópias produz a sequência página 1, 2, 3, seguida novamente de 1, 2, 3.

### Consultar a fila

```bash
curl --fail-with-body 'http://IP-DO-MAC:8080/api/jobs' \
  --header 'Authorization: Bearer SEU_TOKEN'
```

Resposta HTTP **200**, com exemplo ilustrativo:

```json
[
  {
    "id": "df3e72c025b24d699e4ad418228bde52",
    "name": "etiqueta.pdf",
    "status": "sent",
    "created": 1791343165.3546739,
    "pages": 1,
    "copies": 1,
    "error": ""
  }
]
```

`created` é o instante de criação em segundos Unix. `error` contém o motivo da falha/interrupção, quando disponível. Consulte a cada 1 a 3 segundos enquanto houver trabalhos pendentes; imponha um prazo de acompanhamento adequado ao tamanho da fila.

| Status do trabalho | Significado | Conduta do integrador |
| --- | --- | --- |
| `queued` | Aguardando processamento | Continuar consultando |
| `printing` | Conectando ou enviando páginas | Continuar consultando |
| `sent` | A biblioteca TiMini terminou o envio | Registrar envio concluído; não reenviar automaticamente |
| `simulated` | Processado em simulação, sem impressão | Registrar como teste |
| `failed` | Falha na conexão ou no envio | Mostrar `error`; conferir papel antes de reenviar |
| `interrupted` | Servidor reiniciou durante o processamento | Conferir papel antes de reenviar |

`sent` não é uma confirmação física independente. Uma falha pode ocorrer depois de parte do lote ter sido impressa. O servidor não repete automaticamente trabalhos com falha.

### Baixar a prévia

```bash
curl --fail-with-body 'http://IP-DO-MAC:8080/api/jobs/ID-DO-TRABALHO/preview' \
  --header 'Authorization: Bearer SEU_TOKEN' \
  --output previa.png
```

Retorna HTTP **200**, `Content-Type: image/png`. A prévia é da primeira página. Um ID inexistente retorna HTTP **404** com `{"error":"Trabalho não encontrado."}`.

### Consultar a conexão

```bash
curl --fail-with-body 'http://IP-DO-MAC:8080/api/printer' \
  --header 'Authorization: Bearer SEU_TOKEN'
```

Exemplo de resposta HTTP **200**:

```json
{"status":"connected","name":"PD01","error":""}
```

| Estado da conexão | Significado |
| --- | --- |
| `connecting` | Abrindo sessão Bluetooth |
| `connected` | Sessão aberta; reutilizada nos próximos envios |
| `disconnected` | Sem sessão; próximo trabalho tentará conectar |
| `simulated` | Simulação ativa |

Esse é o último estado conhecido. Uma queda silenciosa durante o repouso pode ser detectada apenas no próximo envio. O estado da conexão não substitui o status de cada trabalho.

## Exemplo em JavaScript / Node.js

Use Node.js 20 ou superior, com `fetch`, `FormData` e `Blob` nativos. Este código roda no backend do sistema integrador. Configure `PRINT_SERVER_URL` e, se necessário, `PRINT_SERVER_TOKEN` no ambiente desse sistema:

```javascript
import { readFile } from 'node:fs/promises';

const baseUrl = (process.env.PRINT_SERVER_URL || 'http://localhost:8080').replace(/\/$/, '');
const token = process.env.PRINT_SERVER_TOKEN;
const headers = token ? { Authorization: `Bearer ${token}` } : {};

export async function enviarEtiqueta(caminhoPdf) {
  const form = new FormData();
  form.append('file', new Blob([await readFile(caminhoPdf)], {
    type: 'application/pdf'
  }), 'etiqueta.pdf');
  form.append('copies', '1');

  const response = await fetch(`${baseUrl}/api/jobs`, {
    method: 'POST', headers, body: form,
    signal: AbortSignal.timeout(30_000)
  });
  if (response.status !== 202) {
    throw new Error(`Falha HTTP ${response.status}: ${await response.text()}`);
  }
  return response.json(); // Guarde o id no sistema de origem.
}

export async function consultarTrabalho(id) {
  const response = await fetch(`${baseUrl}/api/jobs`, {
    headers, signal: AbortSignal.timeout(10_000)
  });
  if (!response.ok) throw new Error(`Consulta falhou: HTTP ${response.status}`);
  const trabalhos = await response.json();
  return trabalhos.find(trabalho => trabalho.id === id) ?? null;
}
```

`null` indica apenas que o ID não está nos 100 resultados retornados. Um timeout do POST deixa o resultado incerto: o servidor pode ter recebido o arquivo. Não repita o envio automaticamente.

## Exemplo em Python

Instale `requests` no ambiente do sistema integrador (`pip install requests`):

```python
import os
import requests

base_url = os.environ.get('PRINT_SERVER_URL', 'http://localhost:8080').rstrip('/')
token = os.environ.get('PRINT_SERVER_TOKEN')
headers = {'Authorization': f'Bearer {token}'} if token else {}

with open('etiqueta.pdf', 'rb') as arquivo:
    resposta = requests.post(
        f'{base_url}/api/jobs',
        headers=headers,
        files={'file': ('etiqueta.pdf', arquivo, 'application/pdf')},
        data={'copies': '1'},
        timeout=(5, 30),
    )
resposta.raise_for_status()
trabalho = resposta.json()
print('Guarde este ID:', trabalho['id'])

consulta = requests.get(f'{base_url}/api/jobs', headers=headers, timeout=(5, 10))
consulta.raise_for_status()
atual = next((item for item in consulta.json() if item['id'] == trabalho['id']), None)
print(atual)
```

A consulta acima é única: se o trabalho ainda estiver pendente, o integrador deve consultar novamente. Não configure repetição automática do POST após timeout ou falha de conexão.

## Limites e erros

| HTTP | Situação |
| --- | --- |
| 202 | Documento preparado e registrado na fila |
| 400 | Campo `file` ausente, cópias inválidas, documento inválido, PDF protegido ou limite de páginas excedido |
| 401 | Token ausente/incorreto quando a autenticação está habilitada |
| 404 | Prévia solicitada para um ID inexistente |
| 413 | Requisição multipart maior que 10 MiB |
| 500 | Falha interna, por exemplo ao gravar arquivos ou banco |

As respostas de validação usam `{"error":"mensagem"}`. Falhas HTTP 500 não têm formato JSON garantido. Uma falha Bluetooth após o HTTP 202 aparece no trabalho como `failed`; não altera retroativamente a resposta do POST.

O limite de 10 MiB é da requisição inteira, incluindo os campos multipart. PDFs aceitam de 1 a 30 páginas, sem senha. Cópias: 1 a 20. Documentos são ajustados à área de 384 × 157 pixels, mantendo proporção e margens. Uma página A4 será reduzida inteira; prefira gerar o PDF no tamanho da etiqueta. Não há suporte a DOCX, ZPL, ESC/POS bruto ou texto via JSON neste endpoint.

Os trabalhos e imagens ficam em `data/`; não há exclusão automática. A API não oferece cancelamento, reenvio ou exclusão. Mantenha apenas uma instância do servidor por impressora.

## Evitar duplicações

A versão atual **não implementa idempotência**: cada POST aceito cria um novo trabalho. Enviar `Idempotency-Key` não impede duplicação, pois esse cabeçalho ainda não é processado.

O sistema integrador deve guardar o ID retornado e impedir cliques ou eventos repetidos para o mesmo pedido. Se houver timeout antes de receber o ID, registre o envio como resultado incerto e confira a fila/papel antes de reenviar. Nome do arquivo e horário podem ajudar na conferência manual, mas não são identificadores confiáveis para deduplicação automática.

Para uma integração futura com maior volume, estão propostos: consulta direta por ID, chave de idempotência, paginação do histórico e webhook de mudança de status. Esses recursos ainda não estão disponíveis.
