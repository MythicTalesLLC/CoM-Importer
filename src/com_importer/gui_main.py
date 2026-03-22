"""GUI entry point."""

import logging
import sys
import traceback


def _install_excepthook() -> None:
    """Log unhandled Python exceptions before PyQt6's fatal abort fires.

    PyQt6 calls abort() when a Python exception escapes a Qt slot.  By
    overriding sys.excepthook we at least get a readable traceback in the
    console / log output before the process dies.
    """
    _orig = sys.excepthook

    def _hook(exc_type, exc_value, exc_tb):
        logging.getLogger(__name__).critical(
            "Unhandled exception in Qt slot:\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )
        _orig(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def main() -> int:
    from PyQt6.QtWidgets import QApplication

    from .gui.main_window import ComImporterWindow

    _install_excepthook()

    app = QApplication(sys.argv)
    app.setApplicationName("City of Mist Foundry Importer")
    window = ComImporterWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
