# Other learning systems

The game's zip is a standard **SCORM 1.2** package, so it should work in any learning system that
plays SCORM 1.2. The helper saves in `cmi.suspend_data`, and Scored Games send a 0-100 grade in
`cmi.core.score.raw`. Upload the zip wherever the system adds a SCORM package.

| System | Open source | SCORM 1.2 | Notes |
|---|---|---|---|
| **Chamilo** | yes | yes | Learning paths: **Import AICC, SCORM and Chamilo**. |
| **ILIAS** | yes | yes | **Add new item > Learning module SCORM/AICC**. |
| **Open edX** | yes | with the SCORM XBlock | Ask your Open edX administrator to install the XBlock. |
| **Sakai** | yes | with its SCORM player tool | |
| **Blackboard Learn** | no | yes | Content area: **Build content > Content package (SCORM)**. |
| **D2L Brightspace** | no | yes | **Upload/Create > SCORM/xAPI**. |
| **Canvas** (Instructure's cloud) | no | through Instructure's SCORM app | |
| **Canvas** (self-hosted) | yes | no | Planned: LTI 1.3, see [../LTI.md](../LTI.md). |

Menu names change between versions, so look for "SCORM" or "content package" in yours.

## Things to check in a new system

Use `edugame preview` first, then in the system:

1. Open the game, make some progress, and close it. Open it again: it should carry on.
2. For a Scored Game, finish a round and check the grade in the gradebook.
3. If saves are lost, look for a setting that starts a new attempt every time.

Some systems open SCORM packages in a new window or in frames; the helper looks for the SCORM
connection in parent frames and in the window that opened the game, so both work.

If you try a system that isn't listed, please open an issue saying how it went.
