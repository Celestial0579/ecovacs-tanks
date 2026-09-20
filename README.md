# ecovacs-tanks

Home-Assistant-Integration, die Ecovacs-Modellprofile um Komponenten ergaenzt,
die das mitgelieferte Profil verschweigt.

Beim **DEEBOT T30 OMNI** sind das drei Verbrauchsteile — **Staubbeutel**,
**Wischpads** und **Pflegeeinheit** ("Andere Komponente" in der App) — sowie die
komplette **Basisstation**: drei Tasten, Entleerungshaeufigkeit, Stationszustand.

## Das Problem

`deebot-client` haelt je Geraeteklasse ein Profil, das aufzaehlt, welche
Verschleiss- und Verbrauchskomponenten abgefragt werden. Das Profil fuer die
Klasse `z4lvk7` (T30 OMNI) nennt nur Buerste, Filter und Seitenbuerste — die
Datei traegt sogar die Ueberschrift *"Deebot T20 Omni Capabilities"*, bedient
also ein Nachfolgemodell mit dem Profil des Vorgaengers.

Home Assistant unterstuetzt Staubbeutel-, Schmutzwasser- und Frischwasser-
sensoren laengst (`SUPPORTED_LIFESPANS`). Es bekommt sie nur nicht angeboten.

## Was gemessen wurde

Jede Komponente **einzeln** durchprobiert, je ein HA-Neustart (15.09.2026):

| Komponente | App-Bezeichnung | Ergebnis |
|---|---|---|
| `DUST_BAG` | Staubbeutel | **funktioniert** — 26,13 % |
| `ROUND_MOP` | Wischpads | **funktioniert** — 82,07 % |
| `UNIT_CARE` | Andere Komponente | **funktioniert** — 60,44 % |
| `CLEANING_SOLUTION` | ECOVACS Reinigungsloesung | `{'ret': 'fail', 'errno': 500}` |
| `SEWAGE_BOX` | Schmutzwasserbehaelter | `{'ret': 'fail', 'errno': 500}` |
| `WATER_SINK` | Frischwasserbehaelter | `{'ret': 'fail', 'errno': 500}` |

Bezeichnend: Fuer **Staubbeutel und Reinigungsloesung** zeigt die Herstellerapp
als einzige *keine* Reststunden an — trotzdem antwortet das Geraet auf
`dustBag`, auf `cleaningSolution` jedoch nicht. Aus der App laesst sich also
nicht ableiten, was die API hergibt. Es hilft nur Ausprobieren.

### Die Falle

`getLifeSpan` fragt **alle** Komponenten in **einem** Aufruf ab. Ist auch nur
eine nicht unterstuetzte dabei, weist das Geraet die **gesamte** Anfrage
zurueck — dann stehen auch Buerste, Filter und Seitenbuerste auf `unknown`.
Eine falsch eingetragene Komponente kostet also nicht nur sich selbst, sondern
die funktionierenden gleich mit.

Deshalb: **nur eintragen, was nachweislich antwortet**, und jede Ergaenzung
**einzeln** pruefen.

### Zweite Falle: Reihenfolge beim Start

Wird `ecovacs` **vor** dieser Integration eingerichtet, hat es das alte Profil
schon benutzt. Ein Neuladen direkt in `async_setup` greift dann ins Leere — der
Eintrag steht zu diesem Zeitpunkt oft noch nicht auf `LOADED`, die Schleife
findet nichts, und die Sensoren fehlen **still**. Deshalb wird das Neuladen an
`EVENT_HOMEASSISTANT_STARTED` gehaengt.

### Wassertanks

Fuellstaende gibt es nicht. Die Herstellerapp zeigt fuer Frisch- und
Schmutzwasser nur zwei Tropfensymbole (voll/leer) — dafuer kennt
`deebot-client` ueberhaupt kein Ereignis. Voll- und Leer-Zustaende meldet das
Geraet ausschliesslich als Fehlercode auf `sensor.<name>_fehler`:

| Code | Bedeutung |
|---|---|
| 301, 322 | Frischwassertank leer bzw. nicht eingesetzt |
| 302, 305, 318, 323 | Schmutzwassertank voll |
| 311, 312 | Staubbeutel wechseln bzw. voll |
| 110, 114 | Staubbehaelter im Roboter fehlt bzw. voll |
| 317 | Nachfuellen aus dem Frischwassertank gestoert |

## Basisstation

Das Profil hatte **gar keine** `station`-Faehigkeit — deshalb fehlten in HA die
drei Tasten, die die Herstellerapp unter *Angedockt* zeigt. Ergaenzt:

| | Entitaet | Stand beim Einbau |
|---|---|---|
| Staubbehaelter entleeren | `button` | — |
| Mopp trocknen | `button` | — |
| Basis reinigen | `button` | — |
| Haeufigkeit der Auto-Entleerung | `select` | `smart` |
| Zustand der Station | `sensor` | `idle` |

Anders als bei den Verbrauchsteilen ist das **ungefaehrlich**: Stationsaktionen,
`getAutoEmpty` und `getStationState` sind eigene Kommandos. Eine nicht
unterstuetzte Aktion laesst nur sich selbst scheitern und reisst nichts mit.

**Ungeprueft:** Die Auswahlwerte der Entleerung stehen auf `AUTO` und `SMART`.
Ob das Geraet auch die Minutenwerte (10/15/25) annimmt, liesse sich nur durch
Setzen herausfinden — das aendert das Verhalten des Geraets.

## Was NICHT geht

| | warum |
|---|---|
| Fuellstand der Wassertanks | kein Ereignis in `deebot-client`; die App zeigt nur zwei Tropfensymbole |
| KI-Modus (`AI`-Knopf der App) | **kein einziges** KI-Kommando in der Bibliothek — App-/Cloud-Funktion |
| Reinigungsgeschwindigkeit | `getEfficiency` gibt es, aber **Home Assistant** baut daraus keine Entitaet |

Bei den letzten beiden liegt die Luecke nicht im Modellprofil, sondern eine
Schicht hoeher. Eine Profilergaenzung liefe ins Leere.

## Wie es funktioniert

`deebot_client.hardware.get_static_device_info()` fragt **zuerst** einen
Zwischenspeicher und importiert das Profilmodul nur, wenn dort nichts steht:

```python
if device := _DEVICES.get(class_):
    return device
```

Diese Integration legt dort vorab ein erweitertes Profil ab. Die Bibliothek
greift dann nie auf die Originaldatei zu — es wird **keine mitgelieferte Datei
veraendert**, und der Eingriff ueberlebt jedes Update von Home Assistant.

## Einrichtung

Seit Fassung 1.1.0 laeuft die Einrichtung ueber die Oberflaeche — **ohne**
Eingriff in `configuration.yaml`.

### Ueber HACS (empfohlen)

1. In HACS unter *Eigene Repositorien* die Adresse dieses Repositoriums
   eintragen, Art: **Integration**
2. Herunterladen, Home Assistant neu starten
3. *Einstellungen → Geraete & Dienste → Integration hinzufuegen* →
   **Ecovacs: Tank- und Beutelstaende** → bestaetigen

Es gibt nichts einzustellen. Der Dialog besteht aus einer Bestaetigung; die
Erweiterung ergaenzt fest hinterlegte Profile.

### Von Hand

1. `custom_components/ecovacs_tanks/` nach `config/custom_components/`
   kopieren, Home Assistant neu starten
2. Integration wie oben hinzufuegen

### Warum ueberhaupt ein Dialog

Bis 1.0.0 liess sich die Erweiterung **nur** ueber `ecovacs_tanks:` in der
`configuration.yaml` scharf schalten. Auf einer HAOS-Anlage ohne Terminal-,
Datei-Editor- oder SSH-Add-on kommt man an diese Datei jedoch gar nicht heran:
Die Erweiterung war dort per HACS installierbar, aber **nicht aktivierbar**.
Genau dieser Fall trat am 20.09.2026 an einem zweiten Standort auf.

### Bestandsanlagen

Der YAML-Schluessel bleibt erhalten und funktioniert weiter. Beim ersten Start
nach dem Update legt er den Eintrag selbsttaetig an — es ist **nichts zu tun**,
und die Zeile darf stehen bleiben. `single_config_entry` verhindert, dass
daraus ein zweiter Eintrag entsteht.

### Zeitpunkt des Neuladens

Beim Hochfahren haengt sich die Integration an `EVENT_HOMEASSISTANT_STARTED`
und laedt den Ecovacs-Eintrag erst dann neu — zu frueh laesst die Sensoren als
*nicht verfuegbar* stehen.

Wird sie dagegen **zur Laufzeit** hinzugefuegt, ist dieses Ereignis laengst
vorbei und kaeme nie wieder. Dann wird sofort neu geladen. Ohne diese
Unterscheidung erschienen die neuen Sensoren erst nach dem naechsten Neustart.

### Entfernen

Beim Entfernen des Eintrags werden die Profile in den Urzustand gebracht und
der Ecovacs-Eintrag neu geladen. Die Zusatzsensoren verschwinden also sofort
und nicht erst beim naechsten Neustart.

**Steht `ecovacs_tanks:` noch in der `configuration.yaml`, kommt der Eintrag
beim naechsten Start von selbst wieder.** Das ist bei YAML-konfigurierten
Integrationen so vorgesehen und kein Fehler — wer die Erweiterung dauerhaft
loswerden will, muss die Zeile mit entfernen. Anlagen, die ueber die
Oberflaeche eingerichtet wurden, haben diese Zeile ohnehin nicht.

Kommt man an die Datei nicht heran — genau der Fall, fuer den es den Dialog
gibt —, hilft **Deaktivieren statt Loeschen**: `single_config_entry` zaehlt
auch deaktivierte Eintraege mit, der Import-Flow bricht deshalb ab und die
Erweiterung bleibt aus. Nachgeprueft gegen Home Assistant 2026.9.3.

## Grenzen

`_DEVICES` ist ein privater Name. Wird er in einer kuenftigen Fassung von
deebot-client umbenannt oder umgebaut, greift der Eingriff nicht mehr. Dieser
Fall wird erkannt und ins Protokoll geschrieben — er scheitert **nicht still**.

Der Wert ist eine Schaetzung aus der Nutzung (Prozent Restlaufzeit), kein
gemessener Fuellstand.

## Andere Modelle

`ERWEITERUNGEN` in `__init__.py` ergaenzen. Die Geraeteklasse steht in Home
Assistant unter *Geraet → Geraeteinfo* als Modell-ID, oder per API im
Geraeteregister als `model_id`.
