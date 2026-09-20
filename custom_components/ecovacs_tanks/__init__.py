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
Jede Komponente einzeln durchprobiert, je ein Neustart:

    DUST_BAG           -> FUNKTIONIERT   Staubbeutel            26,13 %
    ROUND_MOP          -> FUNKTIONIERT   Wischpads              82,07 %
    UNIT_CARE          -> FUNKTIONIERT   "Andere Komponente"    60,44 %
    CLEANING_SOLUTION  -> errno 500      ECOVACS Reinigungsloesung
    SEWAGE_BOX         -> errno 500      Schmutzwasserbehaelter
    WATER_SINK         -> errno 500      Frischwasserbehaelter

Die drei funktionierenden decken sich mit der Herstellerapp unter "Wartung".
Bezeichnend: Fuer Staubbeutel und Reinigungsloesung zeigt die App als einzige
KEINE Reststunden an - trotzdem antwortet das Geraet auf dustBag, auf
cleaningSolution jedoch nicht. Aus der App laesst sich also nicht ableiten,
was die API hergibt; es hilft nur Ausprobieren.

WICHTIGE FALLE: `getLifeSpan` fragt ALLE Komponenten in EINEM Aufruf ab. Ist
auch nur eine nicht unterstuetzte dabei, weist das Geraet die GESAMTE Anfrage
zurueck - dann stehen auch Buerste, Filter und Seitenbuerste auf `unknown`.
Eine falsch eingetragene Komponente kostet also nicht nur sich selbst, sondern
die funktionierenden gleich mit. Deshalb hier NUR eintragen, was nachweislich
antwortet, und jede Ergaenzung EINZELN pruefen.

Stationsfaehigkeit (15.09.2026 ergaenzt)
----------------------------------------
Das Profil hatte gar keine `station`-Faehigkeit, deshalb fehlten in HA die drei
Tasten der Herstellerapp. Ergaenzt wurden EMPTY_DUSTBIN, DRY_MOP und CLEAN_BASE
(mehr baut HA nicht, siehe SUPPORTED_STATION_ACTIONS), dazu die
Entleerungshaeufigkeit und der Stationszustand. Beide antworteten sofort:
`smart` bzw. `idle`.

Anders als bei den Verbrauchsteilen ist das ungefaehrlich: Stationsaktionen,
getAutoEmpty und getStationState sind EIGENE Kommandos. Eine nicht
unterstuetzte Aktion laesst nur sich selbst scheitern und reisst nichts mit.

Die Auswahlwerte der Entleerung stehen zurueckhaltend auf AUTO und SMART wie im
Vergleichsmodell. Ob das Geraet auch die Minutenwerte (10/15/25) annimmt, ist
UNGEPRUEFT - das liesse sich nur durch Setzen herausfinden, was das Verhalten
des Geraets aendert.

Fuellstaende der Wassertanks gibt es nicht. Die Herstellerapp zeigt fuer Frisch-
und Schmutzwasser nur zwei Tropfensymbole (voll/leer) - dafuer kennt
deebot-client ueberhaupt kein Ereignis. Voll- und Leer-Zustaende meldet das
Geraet nur als Fehlercode auf `sensor.<name>_fehler`: 301/322 Frischwasser leer,
302/305/318/323 Schmutzwasser voll, 311/312 Staubbeutel, 110/114 Staubbehaelter
im Roboter.

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

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecovacs_tanks"

# Geraeteklasse -> zusaetzlich anzumeldende Verschleiss-/Verbrauchskomponenten.
#
# NUR eintragen, was das Geraet nachweislich beantwortet. Siehe die Falle im
# Modulkopf: eine einzige nicht unterstuetzte Komponente legt die Abfrage
# ALLER Komponenten lahm.
#
# Die Namen muessen in deebot_client.events.LifeSpan existieren UND in
# homeassistant.components.ecovacs.const.SUPPORTED_LIFESPANS stehen,
# sonst baut HA keinen Sensor daraus.
ERWEITERUNGEN: dict[str, tuple[str, ...]] = {
    # T30 OMNI: CLEANING_SOLUTION, SEWAGE_BOX, WATER_SINK am 15.09.2026
    # geprueft -> Geraet antwortet errno 500
    "z4lvk7": ("DUST_BAG", "ROUND_MOP", "UNIT_CARE"),
}

# Geraeteklasse -> Stationsaktionen, die als Taste erscheinen sollen.
#
# Anders als bei den Verschleissteilen ist das ungefaehrlich: Stationsaktionen
# sind eigene Kommandos. Eine nicht unterstuetzte Aktion laesst nur sich selbst
# scheitern und reisst nichts mit.
#
# HA baut Tasten nur fuer CLEAN_BASE, DRY_MOP und EMPTY_DUSTBIN
# (SUPPORTED_STATION_ACTIONS). WASH_MOP kennt die Bibliothek zwar, HA nicht.
STATIONSAKTIONEN: dict[str, tuple[str, ...]] = {
    "z4lvk7": ("EMPTY_DUSTBIN", "DRY_MOP", "CLEAN_BASE"),
}

# Auswahlwerte fuer die automatische Entleerung. Zurueckhaltend gewaehlt wie im
# Vergleichsmodell; die Minutenwerte (10/15/25) sind ungeprueft.
ENTLEERUNG_FREQUENZEN = ("AUTO", "SMART")

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({}, extra=vol.ALLOW_EXTRA)}, extra=vol.ALLOW_EXTRA)


def _station_bauen(aktionen: tuple[str, ...]):
    """CapabilityStation zusammenbauen, oder None wenn nichts davon geht."""
    from deebot_client.capabilities import (
        CapabilityEvent,
        CapabilityExecuteTypes,
        CapabilitySetTypes,
        CapabilityStation,
    )
    from deebot_client.commands import StationAction
    from deebot_client.commands.json import station_action
    from deebot_client.commands.json.auto_empty import GetAutoEmpty, SetAutoEmpty
    from deebot_client.commands.json.station_state import GetStationState
    from deebot_client.events import StationEvent, auto_empty
    from deebot_client.events.auto_empty import AutoEmptyEvent

    typen = []
    for name in aktionen:
        wert = getattr(StationAction, name, None)
        if wert is None:
            _LOGGER.warning("StationAction.%s kennt deebot-client nicht", name)
            continue
        typen.append(wert)
    if not typen:
        return None, []

    frequenzen = tuple(
        f for f in (getattr(auto_empty.Frequency, n, None) for n in ENTLEERUNG_FREQUENZEN)
        if f is not None
    )

    station = CapabilityStation(
        action=CapabilityExecuteTypes(station_action.StationAction, types=tuple(typen)),
        auto_empty=CapabilitySetTypes(
            event=AutoEmptyEvent,
            get=[GetAutoEmpty()],
            set=SetAutoEmpty,
            types=frequenzen,
        ),
        state=CapabilityEvent(StationEvent, [GetStationState()]),
    )
    return station, [t.name for t in typen]


def _erweitere(
    klasse: str,
    komponenten: tuple[str, ...],
    aktionen: tuple[str, ...],
    originale: dict[str, Any],
):
    """Profil der Geraeteklasse erweitern und in den Zwischenspeicher legen.

    Rueckgabe: (erfolgreich, Meldung). Laeuft im Executor, nicht in der
    Ereignisschleife - importlib.import_module blockiert.
    """
    from deebot_client import hardware
    from deebot_client.commands.json.life_span import GetLifeSpan
    from deebot_client.events import LifeSpan

    speicher: dict[str, Any] | None = getattr(hardware, "_DEVICES", None)
    if speicher is None or not isinstance(speicher, dict):
        return False, (
            "deebot_client.hardware._DEVICES nicht gefunden - die Bibliothek hat sich "
            "geaendert. Die zusaetzlichen Sensoren und Stationstasten bleiben aus."
        )

    schon_aufgeloest = klasse in speicher

    modul = importlib.import_module(f"deebot_client.hardware.{klasse}")
    info = modul.get_device_info()
    caps = info.capabilities
    teile = []

    # --- Verschleiss- und Verbrauchskomponenten ---
    vorhanden = tuple(caps.life_span.types)
    neu = []
    for name in komponenten:
        wert = getattr(LifeSpan, name, None)
        if wert is None:
            _LOGGER.warning("LifeSpan.%s kennt deebot-client nicht - uebersprungen", name)
            continue
        if wert not in vorhanden:
            neu.append(wert)

    if neu:
        alle = vorhanden + tuple(neu)
        caps = dataclasses.replace(
            caps,
            life_span=dataclasses.replace(
                caps.life_span, types=alle, get=[GetLifeSpan(list(alle))]
            ),
        )
        teile.append("Verbrauchsteile " + ", ".join(x.name for x in neu))

    # --- Stationsfaehigkeit ---
    if aktionen and getattr(caps, "station", None) is None:
        station, namen = _station_bauen(aktionen)
        if station is not None:
            caps = dataclasses.replace(caps, station=station)
            teile.append("Station " + ", ".join(namen) + " samt Entleerung und Zustand")

    if not teile:
        return True, f"{klasse}: nichts zu ergaenzen, Profil ist bereits vollstaendig"

    # Urzustand merken, BEVOR ueberschrieben wird. Fehlt der Schluessel noch,
    # wird None gemerkt - dann muss das Entfernen den Eintrag loeschen, nicht
    # etwas Falsches zurueckschreiben.
    originale.setdefault(klasse, speicher.get(klasse))
    speicher[klasse] = dataclasses.replace(info, capabilities=caps)
    hinweis = (
        " (Profil war bereits aufgeloest - Ecovacs-Eintrag wird neu geladen)"
        if schon_aufgeloest
        else ""
    )
    return True, f"{klasse}: ergaenzt um {'; '.join(teile)}{hinweis}"




def _zuruecksetzen(originale: dict[str, Any]) -> None:
    """Profile in den Urzustand bringen. Laeuft im Executor."""
    from deebot_client import hardware

    speicher: dict[str, Any] | None = getattr(hardware, "_DEVICES", None)
    if speicher is None or not isinstance(speicher, dict):
        return
    for klasse, urzustand in originale.items():
        if urzustand is None:
            speicher.pop(klasse, None)
        else:
            speicher[klasse] = urzustand


async def _ecovacs_neu_laden(hass: HomeAssistant) -> None:
    """Geladene Ecovacs-Eintraege neu laden, damit das Profil greift."""
    for eintrag in hass.config_entries.async_entries("ecovacs"):
        if eintrag.state is ConfigEntryState.LOADED:
            _LOGGER.info(
                "Lade Ecovacs-Eintrag %s neu, damit das geaenderte Profil greift",
                eintrag.title,
            )
            await hass.config_entries.async_reload(eintrag.entry_id)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML-Weg: den Eintrag einmalig aus `ecovacs_tanks:` uebernehmen.

    Der YAML-Schluessel bleibt ausdruecklich erhalten - bestehende Anlagen
    sollen durch die Umstellung auf den Einrichtungsdialog nicht stehen
    bleiben. Er richtet jetzt nur noch den Eintrag ein; die eigentliche
    Arbeit macht async_setup_entry.

    `single_config_entry` im Manifest sorgt dafuer, dass daraus kein zweiter
    Eintrag entsteht, wenn schon einer ueber die Oberflaeche angelegt wurde.
    """
    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data={}
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Profile erweitern, bevor die Ecovacs-Integration sie abruft."""
    originale: dict[str, Any] = {}
    # Neben den Urzustaenden wird auch der Abmelder des Start-Zuhoerers
    # verwahrt - siehe die dritte Falle in async_unload_entry.
    zustand: dict[str, Any] = {"originale": originale, "abmelden": None}
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = zustand
    neu_geladen = False

    klassen = set(ERWEITERUNGEN) | set(STATIONSAKTIONEN)
    for klasse in sorted(klassen):
        try:
            ok, meldung = await hass.async_add_executor_job(
                _erweitere,
                klasse,
                ERWEITERUNGEN.get(klasse, ()),
                STATIONSAKTIONEN.get(klasse, ()),
                originale,
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

    if not neu_geladen:
        return True

    # War die Ecovacs-Integration schneller, hat sie das alte Profil bereits
    # benutzt. Dann hilft nur ein Neuladen ihres Eintrags.
    #
    # FALLE (15.09.2026): Das Neuladen waehrend des Starts direkt zu versuchen
    # geht schief - der Ecovacs-Eintrag steht dann oft noch nicht auf LOADED,
    # die Schleife findet nichts und der Sensor fehlt still.
    #
    # ZWEITE FALLE (20.09.2026, mit dem Einrichtungsdialog dazugekommen): Wird
    # die Integration zur LAUFZEIT hinzugefuegt, ist der Start laengst vorbei -
    # EVENT_HOMEASSISTANT_STARTED kommt nie wieder. Wer nur auf das Ereignis
    # wartet, sieht die neuen Sensoren erst nach dem naechsten Neustart.
    # Deshalb die Fallunterscheidung.
    if hass.is_running:
        await _ecovacs_neu_laden(hass)
    else:
        async def _nachladen(_: Event) -> None:
            zustand["abmelden"] = None
            await _ecovacs_neu_laden(hass)

        zustand["abmelden"] = hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, _nachladen
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Profile zuruecksetzen und Ecovacs neu laden.

    Ohne das bliebe die Erweiterung bis zum naechsten Neustart wirksam,
    obwohl sie in der Oberflaeche schon entfernt ist - ein Zustand, der
    niemandem erklaerbar waere.
    """
    zustand = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not zustand:
        return True

    # DRITTE FALLE (20.09.2026): Wird der Eintrag entfernt, BEVOR Home Assistant
    # fertig hochgefahren ist, bleibt der Zuhoerer auf
    # EVENT_HOMEASSISTANT_STARTED sonst haengen. Er wuerde dann nach dem Start
    # die Ecovacs-Integration neu laden, obwohl diese Erweiterung schon weg ist
    # - ein Neuladen ohne erkennbaren Anlass.
    if (abmelden := zustand.get("abmelden")) is not None:
        abmelden()

    originale = zustand.get("originale") or {}
    if not originale:
        return True

    await hass.async_add_executor_job(_zuruecksetzen, originale)
    await _ecovacs_neu_laden(hass)
    return True
