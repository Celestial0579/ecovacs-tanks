# ecovacs-tanks

Home-Assistant-Integration, die Ecovacs-Modellprofile um Komponenten ergaenzt,
die das mitgelieferte Profil verschweigt.

Beim **DEEBOT T30 OMNI** ist das der **Staubbeutel der Basisstation**.

## Das Problem

`deebot-client` haelt je Geraeteklasse ein Profil, das aufzaehlt, welche
Verschleiss- und Verbrauchskomponenten abgefragt werden. Das Profil fuer die
Klasse `z4lvk7` (T30 OMNI) nennt nur Buerste, Filter und Seitenbuerste — die
Datei traegt sogar die Ueberschrift *"Deebot T20 Omni Capabilities"*, bedient
also ein Nachfolgemodell mit dem Profil des Vorgaengers.

Home Assistant unterstuetzt Staubbeutel-, Schmutzwasser- und Frischwasser-
sensoren laengst (`SUPPORTED_LIFESPANS`). Es bekommt sie nur nicht angeboten.

## Was gemessen wurde

Jede Komponente einzeln durchprobiert, je ein HA-Neustart (15.09.2026):

| Komponente | Ergebnis |
|---|---|
| `DUST_BAG` | **funktioniert**, lieferte 26,13 % |
| `SEWAGE_BOX` | Geraet antwortet `{'ret': 'fail', 'errno': 500}` |
| `WATER_SINK` | Geraet antwortet `{'ret': 'fail', 'errno': 500}` |

### Die Falle

`getLifeSpan` fragt **alle** Komponenten in **einem** Aufruf ab. Ist auch nur
eine nicht unterstuetzte dabei, weist das Geraet die **gesamte** Anfrage
zurueck — dann stehen auch Buerste, Filter und Seitenbuerste auf `unknown`.
Eine falsch eingetragene Komponente kostet also nicht nur sich selbst, sondern
die funktionierenden gleich mit.

Deshalb: **nur eintragen, was nachweislich antwortet**, und jede Ergaenzung
einzeln pruefen.

### Wassertanks

Fuellstaende der Wassertanks gibt es an diesem Geraet nicht. Voll- und
Leer-Zustaende meldet es ausschliesslich als Fehlercode auf
`sensor.<name>_fehler`:

| Code | Bedeutung |
|---|---|
| 301, 322 | Frischwassertank leer bzw. nicht eingesetzt |
| 302, 305, 318, 323 | Schmutzwassertank voll |
| 311, 312 | Staubbeutel wechseln bzw. voll |
| 110, 114 | Staubbehaelter im Roboter fehlt bzw. voll |
| 317 | Nachfuellen aus dem Frischwassertank gestoert |

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

1. Ordner nach `config/custom_components/ecovacs_tanks/` kopieren
2. In `configuration.yaml` ergaenzen:

```yaml
ecovacs_tanks:
```

3. Home Assistant neu starten

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
