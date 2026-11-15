"""Eingriff in das echte deebot-client (Fassung wie in Home Assistant, siehe requirements_test.txt)."""

from __future__ import annotations

from collections.abc import Generator
import dataclasses
from unittest.mock import patch

from deebot_client import hardware
from deebot_client.commands import StationAction
from deebot_client.events import LifeSpan
from pytest_homeassistant_custom_component.common import MockConfigEntry
import pytest

from homeassistant.core import HomeAssistant

from custom_components.ecovacs_tanks import (
    DOMAIN,
    ERWEITERUNGEN,
    STATIONSAKTIONEN,
    _erweitere,
    _wiederherstellen,
    _zuruecksetzen,
)

KLASSE = "z4lvk7"


@pytest.fixture(autouse=True)
def leerer_zwischenspeicher() -> Generator[None]:
    hardware._DEVICES.clear()
    yield
    hardware._DEVICES.clear()


def _erweitern() -> tuple[tuple, dict, dict]:
    originale: dict = {}
    erweitert: dict = {}
    ergebnis = _erweitere(KLASSE, ERWEITERUNGEN[KLASSE], STATIONSAKTIONEN[KLASSE], originale, erweitert)
    return ergebnis, originale, erweitert


def test_profil_wird_ergaenzt() -> None:
    (ok, meldung, neu_laden), originale, erweitert = _erweitern()
    assert ok and not neu_laden, meldung
    caps = hardware._DEVICES[KLASSE].capabilities
    erwartet = {LifeSpan.BRUSH, LifeSpan.FILTER, LifeSpan.SIDE_BRUSH, LifeSpan.DUST_BAG, LifeSpan.ROUND_MOP, LifeSpan.UNIT_CARE}
    assert set(caps.life_span.types) == erwartet
    # Eine einzige Abfrage mit allen Komponenten (siehe die Falle im Modulkopf).
    abfrage = caps.life_span.get[0]
    assert len(caps.life_span.get) == 1
    assert set(abfrage._args) == {t.value for t in erwartet}
    assert set(caps.station.action.types) == {StationAction.EMPTY_DUSTBIN, StationAction.DRY_MOP, StationAction.CLEAN_BASE}
    assert originale == {KLASSE: None}
    assert erweitert[KLASSE] is hardware._DEVICES[KLASSE]


def test_die_bibliothek_braucht_den_eingriff_noch() -> None:
    """Schlägt fehl, sobald deebot-client das Profil selbst vervollständigt: dann Eintrag streichen."""
    import importlib

    original = importlib.import_module(f"deebot_client.hardware.{KLASSE}").get_device_info().capabilities
    assert LifeSpan.DUST_BAG not in original.life_span.types
    assert getattr(original, "station", None) is None


def test_schon_aufgeloestes_profil_verlangt_neuladen() -> None:
    import importlib

    hardware._DEVICES[KLASSE] = importlib.import_module(f"deebot_client.hardware.{KLASSE}").get_device_info()
    vorher = hardware._DEVICES[KLASSE]
    (ok, _meldung, neu_laden), originale, _ = _erweitern()
    assert ok and neu_laden
    _zuruecksetzen(originale)
    assert hardware._DEVICES[KLASSE] is vorher


def test_zuruecksetzen_entfernt_den_eintrag() -> None:
    _ok, originale, _ = _erweitern()
    _zuruecksetzen(originale)
    assert KLASSE not in hardware._DEVICES


def test_ueberschriebenes_profil_wird_wiederhergestellt() -> None:
    _ok, _originale, erweitert = _erweitern()
    # Ecovacs schreibt nach seinem Import das Original hinein (Wettlauf beim Start).
    hardware._DEVICES[KLASSE] = dataclasses.replace(erweitert[KLASSE])
    assert _wiederherstellen(erweitert) == [KLASSE]
    assert hardware._DEVICES[KLASSE] is erweitert[KLASSE]
    assert _wiederherstellen(erweitert) == []


def test_ohne_zwischenspeicher() -> None:
    with patch.object(hardware, "_DEVICES", None):
        ok, meldung, neu_laden = _erweitere(KLASSE, ("DUST_BAG",), (), {}, {})
    assert not ok and not neu_laden and "_DEVICES" in meldung


async def test_einrichten_und_entfernen(hass: HomeAssistant) -> None:
    eintrag = MockConfigEntry(domain=DOMAIN, data={})
    eintrag.add_to_hass(hass)
    assert await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    assert LifeSpan.DUST_BAG in hardware._DEVICES[KLASSE].capabilities.life_span.types
    assert await hass.config_entries.async_remove(eintrag.entry_id)
    await hass.async_block_till_done()
    assert KLASSE not in hardware._DEVICES
