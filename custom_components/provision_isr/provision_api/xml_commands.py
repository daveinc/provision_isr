"""Provision ISR XML command definitions.

Each entry defines:
    • method: HTTP verb used to send the command
    • endpoint: relative URL (may include '{channel_id}')
    • dict_repr: full XML dict returned by the corresponding GET call
    • toggle_fields: list of nested keys inside the <motion> element that we intend to flip
    • (optional) post_fields: overrides for POST that set a value unconditionally
"""

from __future__ import annotations

from typing import Dict, List, Union

# ----------------------------------------------------------------------
# Helper types
# ----------------------------------------------------------------------
DictLike = Dict[str, Union[str, Dict[str, Union[str, Dict]], List[Union[str, Dict]]]]

# ----------------------------------------------------------------------
# Example entry for motion detection (copy the exact dict you get from GetMotionConfig)
# ----------------------------------------------------------------------
commands: Dict[str, Dict[str, Union[str, List[str], DictLike]]] = {
    "GetMotionConfig": {
        "method": "GET",
        "endpoint": "/GetMotionConfig",
        "dict_repr": {   # <== paste the dict from your GetMotionConfig response here
            "@version": "1.7",
            "@xmlns": "http://www.ipc.com/ver10",
            "motion": {
                "switch": {"#text": "false"},
                "sensitivity": {"#text": "4", "@type": "int32", "@min": "0", "@max": "8"},
                "alarmHoldTime": {"#text": "20", "@type": "uint32"},
                "area": {
                    "@type": "list",
                    "@count": "9",
                    "itemType": {"@type": "string", "@minLen": "16", "@maxLen": "16"},
                    "item": [
                        {"#text": "<![CDATA[1111111111111111]]>"},
                        {"#text": "<![CDATA[1111111111111111]]>"},
                        {"#text": "<![CDATA[1111111111111111]]>"},
                        {"#text": "<![CDATA[1111111111111111]]>"},
                        {"#text": "<![CDATA[1111111111111111]]>"},
                        {"#text": "<![CDATA[1111111111111111]]>"},
                        {"#text": "<![CDATA[1111111111111111]]>"},
                        {"#text": "<![CDATA[1111111111111111]]>"},
                        {"#text": "<![CDATA[1111111111111111]]>"},
                    ],
                },
                "sensitivities": {
                    "@type": "list",
                    "@count": "9",
                    "itemType": {"@type": "string", "@minLen": "16", "@maxLen": "16"},
                    "item": [
                        {"#text": "<![CDATA[6666666666666666]]>"},
                        {"#text": "<![CDATA[6666666666666666]]>"},
                        {"#text": "<![CDATA[6666666666666666]]>"},
                        {"#text": "<![CDATA[6666666666666666]]>"},
                        {"#text": "<![CDATA[6666666666666666]]>"},
                        {"#text": "<![CDATA[6666666666666666]]>"},
                        {"#text": "<![CDATA[6666666666666666]]>"},
                        {"#text": "<![CDATA[6666666666666666]]>"},
                        {"#text": "<![CDATA[6666666666666666]]>"},
                    ],
                },
                "triggerAlarmOut": {"@type": "list", "@count": "0", "itemType": {"@type": "boolean"}},
                "mail": {
                    "@type": "list",
                    "@count": "0",
                    "switch": {"#text": "false"},
                    "subject": {"#text": "<![CDATA[]]>", "@type": "string", "@maxLen": "63"},
                    "content": {"#text": "<![CDATA[]]>", "@type": "string", "@maxLen": "255"},
                },
                "ftp": {
                    "@type": "list",
                    "@count": "0",
                    "switch": {"#text": "false"},
                },
                "sendPush": {
                    "@type": "list",
                    "@count": "0",
                    "pushSwitch": {"#text": "false"},
                    "recordSwitch": {"#text": "false"},
                    "recordStreamIndex": {"#text": "0", "@type": "uint8"},
                    "sendPicSwitch": {"#text": "false"},
                    "recordTime": {"#text": "0", "@type": "uint32"},
                    "pushContent": {"#text": "<![CDATA[]]>", "@type": "string", "@maxLen": "127"},
                },
                "audioSwitch": {"#text": "false"},
            },
        },
        "toggle_fields": ["switch"],
    },

    # ------------------------------------------------------------------
    # Example: a second feature – toggle the audio switch.
    # Add a new entry exactly like this whenever you need another toggle.
    # ------------------------------------------------------------------
    "ToggleAudio": {
        "method": "POST",
        "endpoint": "/SetMotionConfig",
        "dict_repr": {   # same dict as GetMotionConfig – we mimic the device’s schema
            "@version": "1.7",
            "@xmlns": "http://www.ipc.com/ver10",
            "motion": {
                "switch": {"#text": "false"},
                "sensitivity": {"#text": "4", "@type": "int32", "@min": "0", "@max": "8"},
                "alarmHoldTime": {"#text": "20", "@type": "uint32"},
                "area": {
                    "@type": "list",
                    "@count": "9",
                    "itemType": {"@type": "string", "@minLen": "16", "@maxLen": "16"},
                    "item": [{"#text": "<![CDATA[1111111111111111]]>"}]*9,
                },
                "sensitivities": {
                    "@type": "list",
                    "@count": "9",
                    "itemType": {"@type": "string", "@minLen": "16", "@maxLen": "16"},
                    "item": [{"#text": "<![CDATA[6666666666666666]]>"}]*9,
                },
                "triggerAlarmOut": {"@type": "list", "@count": "0", "itemType": {"@type": "boolean"}},
                "mail": {
                    "@type": "list",
                    "@count": "0",
                    "switch": {"#text": "false"},
                    "subject": {"#text": "<![CDATA[]]>", "@type": "string", "@maxLen": "63"},
                    "content": {"#text": "<![CDATA[]]>", "@type": "string", "@maxLen": "255"},
                },
                "ftp": {"@type": "list", "@count": "0", "switch": {"#text": "false"}},
                "sendPush": {
                    "@type": "list",
                    "@count": "0",
                    "pushSwitch": {"#text": "false"},
                    "recordSwitch": {"#text": "false"},
                    "recordStreamIndex": {"#text": "0", "@type": "uint8"},
                    "sendPicSwitch": {"#text": "false"},
                    "recordTime": {"#text": "0", "@type": "uint32"},
                    "pushContent": {"#text": "<![CDATA[]]>", "@type": "string", "@maxLen": "127"},
                },
                "audioSwitch": {"#text": "false"},
            },
        },
        "toggle_fields": ["audioSwitch"],
    },

    # ------------------------------------------------------------------
    # Add more entries here as you add new features.
    # ------------------------------------------------------------------
}

