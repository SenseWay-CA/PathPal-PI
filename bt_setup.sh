#!/bin/bash

#Stop the Bluetooth service temporarily
sudo systemctl stop bluetooth

#Turn the Bluetooth chip OFF and back ON (hard reset)
sudo hciconfig hci0 down
sudo hciconfig hci0 up

#Restart the Bluetooth service
sudo systemctl start bluetooth

#Force "Page and Inquiry Scan" mode (This makes it advertisable)
sudo hciconfig hci0 piscan

#Check if it worked
#hciconfig -a