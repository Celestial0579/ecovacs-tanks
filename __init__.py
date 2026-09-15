"""Ergaenzt Ecovacs-Modellprofile um Staubbeutel- und Wassertankstaende.

Hintergrund
-----------
`deebot-client` haelt je Geraeteklasse ein Profil, das aufzaehlt, welche
Verschleiss- und Verbrauchskomponenten das Geraet meldet. Das Profil des
DEEBOT T30 OMNI (Klasse `z4lvk7`) zaehlt nur Buerste, Filter und Seitenbuerste
auf - die Datei traegt sogar die Ueberschrift "Deebot T20 Omni Capabilities",
bedient also ein Nachfolgemodell mit dem Profil des Vorgaengers.

Home Assistant selbst unterstuetzt Staubbeutel, Schmutzwasser- und
Frischwassertank laengst (`SUPPORTED_LIFESPANS` in der Ecovacs-Integration).
Es bekommt sie nur nicht angeboten.

Wie der Eingriff funktioniert
-----------------------------
`deebot_client.hardware.get_static_device_info()` fragt ZUERST einen
Zwischenspeicher und importiert das Profilmodul nur, wenn dort nichts steht:

    if device := _DEVICES.get(class_):
        return device

Diese Integration legt dort vorab ein erweitertes Profil ab. Die Bibliothek
greift dann nie auf die Originaldatei zu - es wird also keine mitgelieferte
Datei veraendert, und der Eingriff ueberlebt jedes Update von Home Assistant.

Gemessener Befund (15.09.2026, T30 OMNI)
---------------------------------------
Einzeln durchprobiert, je ein Neustart:

    DUST_BAG     -> FUNKTIONIERT, lieferte 26,13 %
    SEWAGE_BOX   -> Geraet antwortet {'ret': 'fail', 'errno': 500}
    WATER_SINK   -> Geraet antwortet {'ret': 'fail', 'errno': 500}

WICHTIGE FALLE: `getLifeSpan` fragt ALLE Komponenten in EINEM Aufruf ab. Ist
auch nur eine nicht unterstuetzte dabei, weist das Geraet die GESAMTE Anfrage
zurueck - dann stehen auch Buerste, Filter und Seitenbuerste auf `unknown`.
Eine nicht unterstuetzte Komponente kostet also nicht nur sich selbst, sondern
die funktionierenden gleich mit.

Fuellstaende der Wassertanks gibt es an diesem Geraet folglich nicht. Voll- und
Leer-Zustaende meldet es ausschliesslich als Fehlercode auf
`sensor.<name>_fehler`: 301/322 Frischwasser leer, 302/305/318/323 Schmutzwasser
voll, 311/312 Staubbeutel, 110/114 Staubbehaelter im Roboter.

Grenzen
-------
`_DEVICES` ist ein privater Name. Wird er in einer kuenftigen Fassung von
deebot-client umbenannt oder umgebaut, greift der Eingriff nicht mehr. Dieser
Fall wird erkannt und ins Protokoll geschrieben - er darf NICHT still
fehlschlagen, sonst fehlen die Sensoren wieder und niemand merkt es.

Die gelieferten Werte sind Schaetzungen aus der Nutzung (Prozent Restlaufzeit),
keine gemessenen Fuellstaende. Ein echter Pegel existiert in der Hardware nicht;
Voll-/Leer-Zustaende meldet das Geraet nur als Fehlercode (301/302/312/...).
"""

from __future__ import annotations

import dataclasses
import importlib
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecovacs_tanks"

# Geraeteklasse -> zusaetzlich anzumeldende Komponenten.
#
# NUR eintragen, was das Geraet nachweislich beantwortet. Siehe die Falle im
# Modulkopf: eine einzige nicht unterstuetzte Komponente legt die Abfrage
# ALLER Komponenten lahm.
#
# Die Namen muessen in deebot_client.events.LifeSpan existieren UND in
# homeassistant.components.ecovacs.const.SUPPORTED_LIFESPANS stehen,
# sonst baut HA keinen Sensor daraus.
ERWEITERUNGEN: dict[str, tuple[str, ...]] = {
    # T30 OMNI: SEWAGE_BOX und WATER_SINK am 15.09.2026 geprueft -> errno 500
    "z4lvk7": ("DUST_BAG",),
}

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({}, extra=vol.ALLOW_EXTRA)}, extra=vol.ALLOW_EXTRA)


def _erweitere(klasse: str, komponenten: tuple[str, ...]) -> tuple[bool, str]:
    """Profil der Geraeteklasse erweitern und in den Zwischenspeicher legen.

    Rueckgabe: (erfolgreich, Meldung). Laeuft im Executor, nicht in der Schleife -
    importlib.import_module blockiert.
    """
    from deebot_client import hardware
    from deebot_client.commands.json.life_span import GetLifeSpan
    from deebot_client.events import LifeSpan

    speicher: dict[str, Any] | None = getattr(hardware, "_DEVICES", None)
    if speicher is None or not isinstance(speicher, dict):
        return False, (
            "deebot_client.hardware._DEVICES nicht gefunden - die Bibliothek hat sich "
            "geaendert. Die Tank- und Beutelsensoren bleiben aus."
        )

    schon_aufgeloest = klasse in speicher

    modul = importlib.import_module(f"deebot_client.hardware.{klasse}")
    info = modul.get_device_info()
    caps = info.capabilities

    vorhanden = tuple(caps.life_span.types)
    neu = []
    for name in komponenten:
        wert = getattr(LifeSpan, name, None)
        if wert is None:
            _LOGGER.warning("LifeSpan.%s kennt deebot-client nicht - uebersprungen", name)
            continue
        if wert not in vorhanden:
            neu.append(wert)

    if not neu:
        return True, f"{klasse}: nichts zu ergaenzen, Profil ist bereits vollstaendig"

    alle = vorhanden + tuple(neu)
    life_span = dataclasses.replace(
        caps.life_span, types=alle, get=[GetLifeSpan(list(alle))]
    )
    speicher[klasse] = dataclasses.replace(
        info, capabilities=dataclasses.replace(caps, life_span=life_span)
    )

    namen = ", ".join(x.name for x in neu)
    hinweis = (
        " (Profil war bereits aufgeloest - Ecovacs-Eintrag wird neu geladen)"
        if schon_aufgeloest
        else ""
    )
    return True, f"{klasse}: ergaenzt um {namen}{hinweis}"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Profile erweitern, bevor die Ecovacs-Integration sie abruft."""
    neu_geladen = False

    for klasse, komponenten in ERWEITERUNGEN.items():
        try:
            ok, meldung = await hass.async_add_executor_job(
                _erweitere, klasse, komponenten
            )
        except Exception:  # noqa: BLE001 - darf HA nicht mitreissen
            _LOGGER.exception(
                "Profil %s liess sich nicht erweitern - Tank- und Beutelsensoren bleiben aus",
                klasse,
            )
            continue

        if ok:
            _LOGGER.info("%s", meldung)
            if "neu geladen" in meldung:
                neu_geladen = True
        else:
            _LOGGER.warning("%s", meldung)

    # War die Ecovacs-Integration schneller, hat sie das alte Profil bereits
    # benutzt. Dann hilft nur ein Neuladen ihres Eintrags.
    if neu_geladen:
        for eintrag in hass.config_entries.async_entries("ecovacs"):
            if eintrag.state is ConfigEntryState.LOADED:
                _LOGGER.info("Lade Ecovacs-Eintrag %s neu", eintrag.title)
                hass.async_create_task(
                    hass.config_entries.async_reload(eintrag.entry_id)
                )

    return True
