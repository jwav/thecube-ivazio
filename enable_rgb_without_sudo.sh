# add this setting to enable the rgb led without sudo
# explanation by chatgpt :
# setcap 'cap_sys_nice=eip': Uses the setcap tool to set capabilities on the specified file.
#cap_sys_nice: This is the capability being set, which allows the process to change the priority and scheduling of other processes.
#eip: This flag specifies that the capability is enabled for effective, inheritable, and permitted sets.
MY_PYTHON_PATH='/home/ivazio/.pyenv/versions/3.9.19/bin/python3.9'
sudo setcap 'cap_dac_override,cap_sys_nice=eip' $MY_PYTHON_PATH

# to remove this setting:
#sudo setcap -r $MY_PYTHON_PATH
