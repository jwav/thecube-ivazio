# CubeMessages

- [ ] add a `CubeMsgConfig` class to share config updates among all nodes

# CubeGame

- [ ] implement the new time calculation method
- [ ] add team creation timestamp for unique identification

# CubeConfig
- [ ] handle encryption
- [ ] implement routine saving and config changes among all nodes

# CubeBoxes
 
- [ ] make the cubeboxes status messages more frequent and more orderly
- [ ] for the CubeBoxWithPrompt, add commands

# CubeMaster

- [ ] create scoresheets
- [ ] display scoreboard on hdmi screen
- [ ] for the CubeMasterWithPrompt, add commands

# CubeFrontdesk

- [ ] for the CubeFrontdeskWithPrompt, add commands


# CubeRGBMatrix

- [x] use a localhost server instead of a shared file
  - [ ] test with real hardware
- [x] add an option to display the team name additionally to the remaining time
  - [ ] test with real hardware

# GUI

- [ ] new tab for game config :
  - [ ] trophies
  - [ ] game times
  - [ ] cubeboxes score formulae
  - [ ] password system for config edition
- [ ] "sound the alarm" checkbox
- [ ] shorter dates: dd/mm/yyyy


# Hardware

- [ ] CAD a new case for the RFID reader
  - [ ] choose solution (off the shelf of custom made) and print what must be printed
- [ ] CAD rail adapter for button receiver
- [ ] CAD wireless button case and mechanisme
- [x] find cheap Rpi GPIO hats
  - bought.
- [x] find a solution for in-box setup of components (like an MDF board)
  - we're going with a DIN rail
- [x] interface new RFID readers
  - [x] RFID detection and reading
  - [ ] neopixel control
