from com_importer.main import main


def test_main_returns_zero() -> None:
    assert main() == 0
