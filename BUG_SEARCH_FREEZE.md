# Bug: aba Buscar congela após primeira pesquisa/seleção

> **Status: corrigido** na Sprint 4.5. Ver `PLAN.md` seção "Sprint 4.5 — Estabilizar busca" e plugin de referência em `legacy/Import-LIB-KiCad-Plugin/plugins/component_search.py`. `search_tab.py` foi refatorado no padrão do plugin (contador de request-id + checagem no callback, sem `trace_add`, sem watchdog, sem sessão HTTP compartilhada, timeout 15 s). Complementos: botão **Cancelar** enquanto há busca em voo, dedup de fetch de imagem por URL + cache de bytes. Testes 60/60. Fazer o teste manual descrito em "Testes manuais recomendados" para validar em UI real.

## Resumo

A aba **Buscar** funciona na primeira pesquisa e na primeira seleção de componente, mas depois de selecionar outros componentes, carregar imagem/preview, baixar um componente ou tentar uma nova pesquisa, a UI entra em um estado inconsistente.

Sintomas observados:

- O botão/cabeçalho pode ficar em estado de **"Buscando..."**.
- Uma segunda pesquisa pode não renderizar novos resultados.
- Selecionar outro componente nem sempre atualiza imagem/detalhes.
- Imagem só carrega de forma confiável no primeiro componente selecionado.
- Algumas ações antigas parecem continuar interferindo após nova busca.
- Mesmo após mudanças com tokens/watchdog/reset, o problema persiste.

O usuário pediu a regra desejada:

> Após uma pesquisa, quando eu digito uma nova pesquisa, pode interromper todos os processos e "reiniciar o motor de busca".

## Ambiente observado

- Projeto: `EasyJLC`
- Diretório: `/home/idea/EasyJLC`
- GUI: CustomTkinter
- API busca JLCPCB:
  `https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList`
- Engine preview/download: `easyeda2kicad`
- Venv do easyeda2kicad:
  `/home/idea/.local/share/EasyJLC/easyeda2kicad-venv/bin/python`
- Pasta de saída usada nos testes:
  `/home/idea/Documents/KiCad`

## Arquivos relevantes

- `easyjlc/ui/search_tab.py`
- `easyjlc/ui/download_tab.py`
- `easyjlc/ui/preview_panel.py`
- `easyjlc/ui/preview_canvas.py`
- `easyjlc/ui/footprint_canvas.py`
- `easyjlc/core/jlc_api.py`
- `easyjlc/core/kicad_parse.py`
- `easyjlc/core/artifacts.py`
- `easyjlc/ui/bindings.py`

## Comportamento esperado

1. Usuário pesquisa `esp32`.
2. A lista de resultados aparece.
3. Selecionar um item deve atualizar detalhes imediatamente.
4. Carregar imagem deve ser explícito ou, se automático, não pode bloquear a UI.
5. Pré-visualizar deve ser explícito e não interferir em outras seleções.
6. Se o usuário digitar uma nova busca, todo estado antigo da aba Buscar deve ser descartado.
7. Uma nova busca deve sempre poder começar limpa.
8. Requests/threads antigas podem terminar em background, mas não podem atualizar a UI.

## Comportamento real reportado

O usuário relata:

> Apesar disso só consigo visualizar a imagem do primeiro componente que eu seleciono. Os outros não carregam imagem e uma segunda pesquisa de componentes não funciona.

E depois:

> Fica em buscando...

Mesmo após tentativas de:

- tokens para busca;
- tokens para imagem;
- tokens para preview;
- watchdog;
- reset da sessão HTTP;
- reset ao editar campo;
- carregamento explícito de imagem;
- remoção da seleção automática do primeiro item.

## Logs fornecidos

### Caso 1: busca e download funcionando, mas depois a busca textual falha com 403

```text
[busca] pesquisando "C82899" página 1
[busca] 1 resultados, exibindo 1 na página 1
[busca] selecionado C82899 | ESP32-WROOM-32-N4 | pacote=SMD,25.5x18mm | estoque=13784 | imagem=sim
[imagem C82899] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583054178722070528
[imagem C82899] exibindo JPEG 96x96
[preview C82899] solicitado na aba Buscar
[preview C82899] Símbolo carregado: ESP32-WROOM-32 (39 pinos, 1 retângulos, 1 círculos, 0 polylines)
[preview C82899] Footprint carregado: easyeda2kicad:WIFIM-SMD_ESP32-WROOM-32-N4 (26 linhas, 39 pads)
[busca] enviar C82899 para Download direto
[download] trigger externo para C82899, output=(campo atual)
[download] LCSC ID alterado para C82899; limpando preview
[download] iniciar C82899, output=/home/idea/Documents/KiCad
$ /home/idea/.local/share/EasyJLC/easyeda2kicad-venv/bin/python -m easyeda2kicad --full --overwrite --lcsc_id=C82899 --output /home/idea/Documents/KiCad
[INFO] Created Kicad symbol for ID : C82899
       Symbol name : ESP32-WROOM-32
       Library path : /home/idea/Documents/KiCad/easyeda2kicad.kicad_sym
[INFO] Created Kicad footprint for ID: C82899
       Footprint name: WIFIM-SMD_ESP32-WROOM-32-N4
       Footprint path: /home/idea/Documents/KiCad/easyeda2kicad.pretty/WIFIM-SMD_ESP32-WROOM-32-N4.kicad_mod
[INFO] Created 3D model for ID: C82899
       3D model name: WIFIM-SMD_ESP32-WROOM-32-N4
       3D model path (wrl): /home/idea/Documents/KiCad/easyeda2kicad.3dshapes/WIFIM-SMD_ESP32-WROOM-32-N4.wrl
       3D model path (step): /home/idea/Documents/KiCad/easyeda2kicad.3dshapes/WIFIM-SMD_ESP32-WROOM-32-N4.step
-- easyeda2kicad.py v1.0.1 --
[download] finalizado C82899: success=True, output=/home/idea/Documents/KiCad, message=-
[preview] busca pós-download filtrada por C82899: symbol=/home/idea/Documents/KiCad/easyeda2kicad.kicad_sym footprint=/home/idea/Documents/KiCad/easyeda2kicad.pretty/WIFIM-SMD_ESP32-WROOM-32-N4.kicad_mod
[preview] Símbolo carregado: ESP32-WROOM-32 (39 pinos, 1 retângulos, 1 círculos, 0 polylines)
[preview] Footprint carregado: easyeda2kicad:WIFIM-SMD_ESP32-WROOM-32-N4 (26 linhas, 39 pads)
[busca] pesquisando "C129733" página 1
[busca] HTTP 403 da JLCPCB.
```

### Caso 2: múltiplas seleções e nova busca fica presa

```text
[busca] pesquisando "esp32" página 1 token=1
[busca] 617 resultados, exibindo 20 na página 1
[busca] selecionado C82899 | ESP32-WROOM-32-N4 | pacote=SMD,25.5x18mm | estoque=13784 | imagem=sim
[imagem C82899] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583054178722070528
[imagem C82899] exibindo JPEG 96x96
[busca] pesquisando "C129733" página 1 token=2
[busca] 1 resultados, exibindo 1 na página 1
[busca] selecionado C129733 | ESP32-D0WDQ6 | pacote=QFN-48-EP(6x6) | estoque=609 | imagem=sim
[imagem C129733] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583005160020299776
[imagem C129733] exibindo JPEG 96x96
[busca] pesquisando "C129733" página 1 token=3
[busca] pesquisando "esp32" página 1 token=4
```

### Caso 3: busca duplicada em andamento

```text
[busca] pesquisando "C129733" página 1 token=1
[busca] 1 resultados, exibindo 1 na página 1
[busca] selecionado C129733 | ESP32-D0WDQ6 | pacote=QFN-48-EP(6x6) | estoque=609 | imagem=sim
[imagem C129733] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583005160020299776
[imagem C129733] exibindo JPEG 96x96
[preview C129733] solicitado na aba Buscar
[preview C129733] Símbolo carregado: ESP32-D0WDQ6 (49 pinos, 1 retângulos, 1 círculos, 0 polylines)
[preview C129733] Footprint carregado: easyeda2kicad:QFN-48_L6.0-W6.0-P0.40-BL-EP3.8 (12 linhas, 53 pads)
[busca] pesquisando "C129733" página 1 token=2
[busca] 1 resultados, exibindo 1 na página 1
[busca] selecionado C129733 | ESP32-D0WDQ6 | pacote=QFN-48-EP(6x6) | estoque=609 | imagem=sim
[imagem C129733] exibindo imagem em cache
[preview C129733] solicitado na aba Buscar
[preview C129733] Símbolo carregado: ESP32-D0WDQ6 (49 pinos, 1 retângulos, 1 círculos, 0 polylines)
[preview C129733] Footprint carregado: easyeda2kicad:QFN-48_L6.0-W6.0-P0.40-BL-EP3.8 (12 linhas, 53 pads)
[busca] pesquisando "esp32" página 1 token=3
[busca] ignorando busca duplicada em andamento "esp32" página 1
[busca] ignorando busca duplicada em andamento "esp32" página 1
```

### Caso 4: seleção de vários componentes, download, depois busca parece congelar

```text
[busca] pesquisando "esp32" página 1 token=1
[busca] 617 resultados, exibindo 20 na página 1
[busca] selecionado C82899 | ESP32-WROOM-32-N4 | pacote=SMD,25.5x18mm | estoque=13784 | imagem=sim
[imagem C82899] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583054178722070528
[imagem C82899] exibindo JPEG 96x96
[busca] selecionado C129733 | ESP32-D0WDQ6 | pacote=QFN-48-EP(6x6) | estoque=609 | imagem=sim
[imagem C129733] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583005160020299776
[imagem C129733] exibindo JPEG 96x96
[busca] selecionado C193707 | ESP32-PICO-D4 | pacote=QFN-48-EP(7x7) | estoque=5116 | imagem=sim
[imagem C193707] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583007355604361216
[busca] selecionado C328062 | ESP32-WROOM-32U-N4 | pacote=SMD,19.2x18mm | estoque=5003 | imagem=sim
[imagem C328062] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583054269343391744
[busca] enviar C328062 para Download direto
[download] trigger externo para C328062, output=(campo atual)
[download] LCSC ID alterado para C328062; limpando preview
[download] iniciar C328062, output=/home/idea/Documents/KiCad
...
[download] finalizado C328062: success=True, output=/home/idea/Documents/KiCad, message=-
[preview] busca pós-download filtrada por C328062: symbol=/home/idea/Documents/KiCad/easyeda2kicad.kicad_sym footprint=/home/idea/Documents/KiCad/easyeda2kicad.pretty/WIFIM-SMD_38P-L19.2-W18.0-P1.27.kicad_mod
[preview] Símbolo carregado: ESP32-WROOM-32U (39 pinos, 1 retângulos, 1 círculos, 3 polylines)
[preview] Footprint carregado: easyeda2kicad:WIFIM-SMD_38P-L19.2-W18.0-P1.27 (8 linhas, 39 pads)
[busca] pesquisando "C129733" página 1 token=2
```

Depois disso, a UI aparentemente fica presa em **Buscando...**.

### Caso 5: após reset, ainda fica em Buscando

```text
[busca] pesquisando "esp32" página 1 token=1
[busca] 617 resultados, exibindo 20 na página 1
[busca] selecionado C82899 | ESP32-WROOM-32-N4 | pacote=SMD,25.5x18mm | estoque=13784 | imagem=sim
[imagem C82899] solicitação explícita
[imagem C82899] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583054178722070528
[imagem C82899] exibindo JPEG 96x96
[preview C82899] solicitado na aba Buscar token=2
[preview C82899] Símbolo carregado: ESP32-WROOM-32 (39 pinos, 1 retângulos, 1 círculos, 0 polylines)
[preview C82899] Footprint carregado: easyeda2kicad:WIFIM-SMD_ESP32-WROOM-32-N4 (26 linhas, 39 pads)
[busca] selecionado C193707 | ESP32-PICO-D4 | pacote=QFN-48-EP(7x7) | estoque=5116 | imagem=sim
[imagem C193707] solicitação explícita
[imagem C193707] carregando https://jlcpcb.com/api/file/downloadByFileSystemAccessId/8583007355604361216
[preview C193707] solicitado na aba Buscar token=3
[preview C193707] Símbolo carregado: ESP32-PICO-D4 (49 pinos, 1 retângulos, 1 círculos, 0 polylines)
[preview C193707] Footprint carregado: easyeda2kicad:LGA-48_L7.0-W7.0-P0.50-BL-EP5.4 (12 linhas, 58 pads)
[busca] interrompendo processos: campo de busca alterado
[busca] pesquisando "C129733" página 1 token=3
```

Depois disso, a UI fica visualmente em **Buscando...**.

## Mudanças já tentadas

### 1. Parser/preview

- Implementado parser KiCad S-expression.
- Corrigido suporte a footprint antigo `(module ...)`, pois o `easyeda2kicad` gera `.kicad_mod` nesse formato.
- Corrigida seleção de símbolo por propriedade:
  `(property "LCSC Part" "Cxxxxx")`
- Corrigido problema onde biblioteca `easyeda2kicad.kicad_sym` continha vários símbolos e o preview pegava sempre o primeiro (`RP2040`).

### 2. Preview na busca

- Adicionado botão **Pré-visualizar**.
- Preview baixa para cache:
  `~/.cache/EasyJLC/previews/<LCSC_ID>/`
- Preview não deveria rodar automaticamente.
- Foi adicionado token para ignorar preview antigo.

### 3. Imagem JLC

- Adicionada imagem JLC no detalhe.
- Inicialmente carregava automaticamente na seleção.
- Depois foi alterado para carregamento explícito via botão **Carregar imagem**.
- Adicionado cache em memória para imagem.
- Ainda assim o usuário reporta que só a primeira imagem carrega de forma confiável.

### 4. Busca

- Adicionados tokens de busca para ignorar resultados antigos.
- Adicionado watchdog de busca.
- Reduzido timeout da API JLC.
- Adicionado fallback para LCSC ID exato em caso de `HTTP 403`.
- Adicionado fallback por cache expirado e previews locais.
- Tentado reset ao alterar campo de busca.

### 5. Reset de busca

Foi implementada uma rotina de reset tentando:

- incrementar tokens;
- limpar seleção;
- limpar resultados;
- limpar fila de mensagens;
- cancelar watchdog;
- reiniciar sessão HTTP;
- resetar painel de detalhe.

Mesmo assim o problema persiste.

## Hipóteses principais

### Hipótese A: deadlock/lentidão no thread de busca + sessão HTTP compartilhada

`JlcClient` usa uma única `requests.Session`. Mesmo com `reset_session()`, threads antigas podem continuar usando a sessão antiga ou interagir com estado compartilhado.

Sugestão:

- Não compartilhar `requests.Session` entre buscas.
- Em `JlcClient.search()`, criar uma sessão/request isolada por chamada, ou usar `requests.post(...)` direto.
- Alternativamente, proteger `session` com lock e nunca resetar a sessão enquanto thread antiga pode estar usando.

### Hipótese B: reset ao `trace_add("write")` dispara durante alterações internas

`query_var.trace_add("write", self._on_query_changed)` pode disparar em momentos inesperados, inclusive durante manipulações programáticas ou logo antes da busca.

Possível efeito:

- usuário digita;
- `_interrupt_search_engine()` limpa tudo;
- `_start_search()` roda;
- algum trace adicional roda e invalida token novo;
- resultado chega e é ignorado;
- UI fica em estado visual inconsistente.

Sugestão:

- Remover reset automático por `trace_add`.
- Em vez disso, resetar somente dentro de `_start_search()` quando a query nova é diferente da query atual.
- Ou usar debounce com `after()` no trace, não reset imediato.

### Hipótese C: `_drain_message_queue()` descarta mensagens novas demais

Ao editar o campo, `_interrupt_search_engine()` drena a fila inteira. Se uma busca nova foi iniciada quase ao mesmo tempo, a fila pode receber o resultado novo e ele pode ser drenado por engano.

Sugestão:

- Nunca drenar fila global.
- Deixar todos os handlers verificarem token e ignorarem só mensagens antigas.
- Se precisar drenar, drenar apenas mensagens com token menor que o token atual, não a fila inteira.

### Hipótese D: estado visual `Buscando...` não está centralizado

Há múltiplos caminhos alterando:

- `_search_running`
- `_pending_search`
- `_watchdog_job`
- botão Buscar
- `results_header`
- `page_label`

Sugestão:

- Criar um estado explícito:
  `IDLE`, `SEARCHING`, `SHOWING_RESULTS`, `ERROR`
- Só uma função deve aplicar estado visual:
  `_set_search_state(state, message=None)`

### Hipótese E: handlers antigos ainda atualizam UI parcialmente

Mesmo com tokens, alguns caminhos podem ainda atualizar:

- logs;
- detail panel;
- preview panel;
- image panel;

Sugestão:

- Criar um `generation_id` único para a aba inteira.
- Toda ação assíncrona recebe `generation_id`.
- Qualquer mudança de query incrementa generation.
- Todos os callbacks, inclusive log/preview/image/search, verificam generation antes de tocar UI.

## Sugestão de correção estrutural

### 1. Remover `trace_add` como reset imediato

Trocar:

```python
self.query_var.trace_add("write", self._on_query_changed)
```

Por:

- desabilitar paginação quando campo muda;
- não resetar motor ali.

Reset deve acontecer no começo de `_start_search()`.

### 2. Implementar `SearchController` simples

Estado sugerido em `SearchTab`:

```python
self._generation = 0
self._search_state = "idle"
self._active_query = ""
self._active_page = 1
```

Ao iniciar busca:

```python
self._generation += 1
generation = self._generation
self._set_state("searching", query)
self._clear_results()
self.detail.reset()
threading.Thread(
    target=self._worker_search,
    args=(generation, query, page),
    daemon=True,
).start()
```

No callback:

```python
if generation != self._generation:
    return
```

### 3. Não drenar fila global

Remover:

```python
self._drain_message_queue()
```

Mensagens antigas devem ser descartadas por generation/token, não removidas às cegas.

### 4. Não resetar sessão HTTP enquanto thread antiga existe

Remover `reset_session()` do caminho de edição do campo.

Se quiser reiniciar sessão, fazer isso apenas para a próxima busca dentro do worker novo, sem tocar a sessão antiga:

```python
client = JlcClient(cache=self.client.cache, timeout=self.client.timeout)
result = client.search(...)
```

Ou alterar `JlcClient.search()` para não usar sessão compartilhada.

### 5. Isolar imagem de seleção

Manter imagem explícita por botão.

Quando clicar **Carregar imagem**:

```python
generation = self._generation
selected_lcsc = self._selected.lcsc_id
```

No retorno:

```python
if generation != self._generation:
    return
if not self._selected or self._selected.lcsc_id != selected_lcsc:
    return
```

### 6. Isolar preview

Mesma regra da imagem.

Preview antigo não deve bloquear novo preview:

- sem `if preview_worker.is_alive(): return`
- sempre cria novo worker;
- callback antigo é ignorado por generation.

### 7. Nunca iniciar download/preview/imagem em busca automaticamente

Busca deve fazer só:

- chamar API;
- renderizar lista.

Seleção deve fazer só:

- renderizar metadados disponíveis.

Botões explícitos:

- Carregar imagem
- Pré-visualizar
- Baixar

## Possível patch conceitual

### Novo padrão para iniciar busca

```python
def _start_search(self, page=1):
    query = self.query_var.get().strip()
    if not query:
        return

    self._generation += 1
    generation = self._generation
    self._active_query = query
    self._active_page = page

    self._set_state("searching", f'Buscando "{query}"...')
    self._clear_results()
    self.detail.reset("Selecione um resultado.")

    threading.Thread(
        target=self._worker_search,
        args=(generation, query, page),
        daemon=True,
    ).start()
```

### Worker

```python
def _worker_search(self, generation, query, page):
    try:
        result = self.client.search(query, page=page, page_size=PAGE_SIZE)
        self._msg_queue.put(("search_ok", generation, query, page, result))
    except Exception as exc:
        self._msg_queue.put(("search_err", generation, query, page, str(exc)))
```

### Poll

```python
def _handle_search_ok(self, generation, query, page, result):
    if generation != self._generation:
        return
    self._set_state("results")
    self._render_results(query, page, result)
```

## Testes manuais recomendados

### Teste 1

1. Buscar `esp32`.
2. Clicar em 5 componentes diferentes.
3. Não clicar em imagem/preview.
4. Confirmar que detalhe muda instantaneamente.
5. Confirmar que log não mostra requests de imagem.

### Teste 2

1. Buscar `esp32`.
2. Clicar componente 1.
3. Clicar **Carregar imagem**.
4. Antes da imagem terminar, clicar componente 2.
5. Confirmar que imagem do componente 1 não aparece no componente 2.

### Teste 3

1. Buscar `esp32`.
2. Antes de terminar, trocar campo para `C129733`.
3. Buscar.
4. Confirmar que resultado antigo de `esp32` não aparece.
5. Confirmar que botão não fica em **Buscando...**.

### Teste 4

1. Buscar `esp32`.
2. Clicar **Pré-visualizar** em um item.
3. Antes de terminar, selecionar outro item.
4. Clicar **Pré-visualizar**.
5. Confirmar que preview antigo não sobrescreve o novo.

### Teste 5

1. Buscar `C129733`.
2. Buscar `esp32`.
3. Buscar `C82899`.
4. Repetir várias vezes.
5. Confirmar que cada busca limpa estado anterior e renderiza corretamente.

## Commits relacionados já feitos

Os commits abaixo contêm tentativas e partes corretas, mas o bug final persiste:

- `df5829f` — Preview parts from search results
- `c2c160b` — Show JLC images and refresh previews
- `aba00f6` — Improve preview diagnostics and artifact matching
- `1fed182` — Select symbols by LCSC id in previews
- `ffc10ef` — Fallback exact LCSC searches when JLC blocks
- `dd298df` — Fix entry paste and search fallbacks
- `300a121` — Allow overlapping searches without blocking UI
- `0410047` — Guard search pagination while loading
- `acaadf4` — Make search selection explicit
- `1422f27` — Add search watchdog fallback
- `73ade42` — Make search image loading explicit
- `5cef4fa` — Ignore duplicate result selections
- `9910ea1` — Reset search engine on query edits
- `6c1f5d0` — Reset search button on interruption

## Estado dos testes automatizados

Até o último ponto:

```bash
.venv/bin/python -m pytest
```

Resultado:

```text
60 passed
```

Os testes automatizados passam, mas não cobrem adequadamente concorrência/event loop do CustomTkinter.

## Observação final

O bug parece estar menos em parsing/preview/download e mais no controle assíncrono da aba Buscar. A solução mais promissora é simplificar drasticamente o estado:

- uma geração global;
- nenhuma drenagem global de fila;
- nenhuma sessão HTTP compartilhada mutável entre threads;
- reset apenas em `_start_search`, não em `trace_add`;
- todo callback assíncrono verifica geração antes de tocar UI.
