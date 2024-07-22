# TODOs.md

# General / Unsorted

- [ ] !! list the rest of the TODOs
- [ ] !! make full scale simulations that can be run on localhost or on the local network (aka for realsies)
- [x] auto display on hdmi on cubemaster
- [x] limit custom names length


# CubeWebApp

- [ ] !! simple web api that can get send commands and get statuses to handle the inevitable post-installation bugs
- [ ] handle commands :
    - [x] reset cubebox, cubemaster
    - [x] reboot cubebox, cubemaster
    - [ ] press button
    - [ ] stop and resume time for a team or everyone

# CubeGui

- [x] !! remove icons. use emojis in the text directly. more portable and easy
- [x] !! CHECK THAT THE GUI RUNS FINE ON WINDOWS
- [ ] "heure dernier message" doesnt update
- [ ] bugs in current team search : too many teams displayed, maybe due to rgb_test
- [ ] implement add and remove trophy in gui
- [ ] do not display in gui the teams code names that are already occupied

# CubeBoxes

- [ ] write an SD card cloner script

# CubeMaster

- [x] test with real hardware
- [x] !! improve display, have room for 12 teams max
    - [x] problème grésillement relais
- [ ] rgb_test command doesnt work
- [ ] !! implement a way to stop and resume time for a team
- [x] fix the highscores page background : we can't see the background image
- [x] make it so the cubemaster cannot be hacked from the x11 session
- [ ] the sound on cubemaster doesnt work


# CubeRGBMatrix


# CubeFrontdesk


# Hardware

- [x] !! problème du relais qui grésille, acheter relais simple avec adaptateur rail imprimé
- [ ] imprimer adaptateurs et installer un max de rgbmatrices
- [ ] câbler armoire complète
    - [ ] vérifier comment alimenter l'armoire en 230V
- [ ] créer 12 rails de cubeboxes
- [ ] CAD wireless button case and mechanism
    - [ ] valider une conception avec impression coté Cédric
- [ ] test cubemaster gpio hat with rgb matrix
- [ ] new cad case for rfid reader
