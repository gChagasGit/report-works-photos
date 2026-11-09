"""Teste de fumaça: o pacote é importável."""

import report_works


def test_package_is_importable() -> None:
    assert report_works.__doc__
