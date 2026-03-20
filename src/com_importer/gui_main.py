"""GUI entry point."""

import sys


def main() -> int:
    from PyQt6.QtWidgets import QApplication

    from .gui.main_window import ComImporterWindow

    app = QApplication(sys.argv)
    app.setApplicationName("City of Mist Foundry Importer")
    window = ComImporterWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
