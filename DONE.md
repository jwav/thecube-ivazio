# DONE.md

# General / Unsorted

- [x] check that the cubeboxes boot with the rfid reader attached
- [x] autostart on cubemaster
- [x] autostart on cubeboxes
- [x] make the rpis start automatically their respective servers (cubemaster and cubeboxes)
- [x] auto display on hdmi on cubemaster
- [x] limit custom names length

- [x] implement commands :
    - [x] `reset` : reset cubebox
    - [x] `reboot` : shutdown cubebox
    - [x] `button` : simulate button press

# CubeMessages

- [x] add a `CubeMsgConfig` class to share config updates among all nodes
  - [x] implement the `CubeMsgConfig` class in cubemaster, cubebox, cubefrontdesk. cubefrontdesk should be the only one sending it

# CubeGame

- [x] implement the new time calculation method
- [x] implement the new score calculation method
- [x] add team creation timestamp for unique identification

# CubeConfig
- [x] handle encryption
- [x] implement routine saving and config changes among all nodes

# CubeBoxes

- [x] make the cubeboxes status messages more frequent and more orderly
- [x] simulate press button
- [x] simulate rfid read

# CubeMaster

- [x] create scoresheets
- [x] display scoreboard on hdmi screen
- [x] test with real hardware
- [x] improve display, have room for 12 teams max
- [x] rgb_test command doesnt work
- [x] fix the highscores page background : we can't see the background image
- [x] make it so the cubemaster cannot be hacked from the x11 session
- [x] the sound on cubemaster doesnt work
- [x] handle teams being out of time
- [x] flicker on the highscores page's icons, but not the text
- [x] no sound on cubemaster if launched as a service, but as a script it works

# CubeRGBMatrix

# CubeFrontdesk

# GUI

- [x] !! remove icons. use emojis in the text directly. more portable and easy
- [x] !! CHECK THAT THE GUI RUNS FINE ON WINDOWS
- [x] bugs in current team search : too many teams displayed, maybe due to rgb_test
- [x] implement add and remove trophy in gui
- [x] do not display in gui the teams code names that are already occupied

# Hardware

- [x] !! problème du relais qui grésille, acheter relais simple avec adaptateur rail imprimé
- [x] imprimer adaptateurs et installer un max de rgbmatrices
- [x] câbler armoire complète
    - [x] vérifier comment alimenter l'armoire en 230V
- [x] CAD wireless button case and mechanism
    - [x] valider une conception avec impression coté Cédric
- [x] new cad case for rfid reader
