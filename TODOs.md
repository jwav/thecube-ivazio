# CubeMessages

- [x] add a `CubeMsgConfig` class to share config updates among all nodes
  - [ ] implement the `CubeMsgConfig` class in cubemaster, cubebox, cubefrontdesk. cubefrontdesk should be the only one sending it

# CubeGame

- [ ] implement the new time calculation method
- [x] add team creation timestamp for unique identification

# CubeConfig
- [x] handle encryption
- [ ] implement routine saving and config changes among all nodes

# CubeBoxes
 
- [x] make the cubeboxes status messages more frequent and more orderly
- [ ] for the CubeBoxWithPrompt, add commands

# CubeMaster

- [ ] create scoresheets
- [ ] display scoreboard on hdmi screen
- [ ] for the CubeMasterWithPrompt, add commands

# CubeFrontdesk

- [ ] for the CubeFrontdeskWithPrompt, add commands

# CubeRGBMatrix

- [x] use a localhost server instead of a shared file
  - [x] test with real hardware
- [x] add an option to display the team name additionally to the remaining time
  - [x] test with real hardware

# GUI

- [ ] new tab for game config :
  - [ ] SCREW THAT JUST IMPLEMENT FILE DECRYPTION/ENCRYPTION WERE NOT DOING A WHOLE GUI FOR THAT
  - [ ] trophies
  - [ ] game times
  - [ ] cubeboxes score formulae
  - [ ] password system for config edition
- [ ] "sound the alarm" checkbox
- [ ] shorter dates: dd/mm/yyyy


# Hardware

- [x] CAD a new case for the RFID reader
  - [x] choose solution (off the shelf of custom made) and print what must be printed
- [ ] CAD rail adapter for button receiver
- [ ] CAD wireless button case and mechanisme
- [x] find cheap Rpi GPIO hats
  - bought.
- [x] find a solution for in-box setup of components (like an MDF board)
  - we're going with a DIN rail
- [x] interface new RFID readers
  - [x] RFID detection and reading
  - [ ] neopixel control