# DONE.md

# General / Unsorted

- [x] check that the cubeboxes boot with the rfid reader attached
- [x] autostart on cubemaster
- [x] autostart on cubeboxes

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

# CubeMaster

- [x] create scoresheets
- [x] display scoreboard on hdmi screen

# CubeRGBMatrix

- [x] use a localhost server instead of a shared file
  - [x] test with real hardware
- [x] add an option to display the team name additionally to the remaining time
  - [x] test with real hardware

# GUI

- [x] new tab for game config :
  - [x] SCREW THAT JUST IMPLEMENT FILE DECRYPTION/ENCRYPTION WERE NOT DOING A WHOLE GUI FOR THAT
- [x] "sound the alarm" checkbox
- [x] shorter dates: dd/mm/yyyy

# Hardware

- [x] CAD a new case for the RFID reader
  - [x] choose solution (off the shelf of custom made) and print what must be printed
- [x] find cheap Rpi GPIO hats
  - bought.
- [x] find a solution for in-box setup of components (like an MDF board)
  - we're going with a DIN rail
- [x] interface new RFID readers
  - [x] RFID detection and reading
