# EasyJLC

App gráfico multiplataforma para baixar símbolos e footprints KiCad a partir do LCSC/EasyEDA, com busca, preview, preço e estoque JLCPCB.

Sucessor dos scripts `jlc_downloader.py` / `.bat` (preservados em [`legacy/`](legacy/)). Plano de ação completo em [`PLAN.md`](PLAN.md).

## Status

Sprint 1 (fundação) — em andamento. MVP não pronto para uso ainda.

## Requisitos

- Python 3.10+ (testado em 3.13)
- Linux ou Windows (macOS via fonte; build oficial é follow-up)

## Rodando em modo desenvolvimento

### Linux / macOS

```bash
./scripts/run_dev.sh
```

### Windows

```bat
scripts\run_dev.bat
```

Os scripts criam (se necessário) um venv local em `.venv/`, instalam as dependências de `requirements.txt` e iniciam `python -m easyjlc`.

## Instalação via pip (opcional)

```bash
python -m pip install -e .[dev]
easyjlc
```

## Testes

```bash
python -m pytest
```

## Estrutura

```
easyjlc/        # pacote principal (GUI CustomTkinter + core)
legacy/         # scripts originais do SandKrux (referência)
packaging/      # specs PyInstaller, ícones, .desktop
scripts/        # launchers de dev
tests/          # pytest
```

## Licença

MIT.
