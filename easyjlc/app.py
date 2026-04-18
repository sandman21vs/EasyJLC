"""Bootstrap do EasyJLC — carrega settings/history e abre a janela principal."""

from __future__ import annotations

import logging

from easyjlc import __version__
from easyjlc import history as history_module
from easyjlc import i18n
from easyjlc import settings as settings_module
from easyjlc.config import setup_logging
from easyjlc.core import EasyEdaRunner, JlcClient
from easyjlc.ui import MainWindow

log = logging.getLogger("easyjlc.app")


def main() -> int:
    setup_logging()
    log.info("Iniciando EasyJLC %s", __version__)

    user_settings = settings_module.load()
    i18n.init(user_settings.language)
    history = history_module.load()
    runner = EasyEdaRunner()
    jlc_client = JlcClient()

    app = MainWindow(user_settings, history, runner, jlc_client=jlc_client)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
