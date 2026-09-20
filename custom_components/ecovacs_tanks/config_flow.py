"""Einrichtungsdialog fuer die Ecovacs-Profilerweiterung.

Die Erweiterung hat nichts zu konfigurieren - sie ergaenzt fest hinterlegte
Geraeteprofile. Der Dialog besteht deshalb aus einer einzigen Bestaetigung.

Zweck ist nicht Konfigurierbarkeit, sondern Erreichbarkeit: Vorher liess sich
die Erweiterung nur ueber einen Eintrag in configuration.yaml scharf schalten.
Auf einer HAOS-Anlage ohne Terminal-, Datei-Editor- oder SSH-Add-on kommt man
an diese Datei gar nicht heran - die Erweiterung war dort per HACS zwar
installierbar, aber nicht aktivierbar. Mit dem Dialog geht beides ueber die
Oberflaeche und ueber die API.

`single_config_entry` im Manifest verhindert einen zweiten Eintrag; HA bricht
dann von sich aus mit `single_instance_allowed` ab.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from . import DOMAIN

TITEL = "Ecovacs: Tank- und Beutelstaende"


class EcovacsTanksConfigFlow(ConfigFlow, domain=DOMAIN):
    """Fuehrt durch die Einrichtung - eine Bestaetigung, sonst nichts."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Von Hand ueber die Oberflaeche oder die API."""
        if user_input is not None:
            return self.async_create_entry(title=TITEL, data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Uebernahme aus `ecovacs_tanks:` in der configuration.yaml.

        Bestandsanlagen sollen durch die Umstellung nicht stehen bleiben:
        Beim ersten Start nach dem Update legt der YAML-Schluessel den Eintrag
        selbsttaetig an, ohne dass jemand etwas anfassen muss.
        """
        return self.async_create_entry(title=TITEL, data={})
