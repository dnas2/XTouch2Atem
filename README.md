# XTouch2Atem
Control a Blackmagic ATEM 1M/E from a Behringer XTouch

This Python project, designed for a Raspberry Pi, allows you to control a Blackmagic ATEM 1M/E switcher from a Behringer XTouch.

A lot of features are missing and I have ideas for future development if I get around to it. This is unlikely to work reliably with an ATEM 2M/E as I've hard-coded the first M/E.

## Prerequisite

As well as the hardware, create a config.py file containing the IP address of the Atem

## Credit

Thanks to the following projects, which have been the basis of a large chunk of the code:
- https://github.com/peterdikant/xair-remote
- https://github.com/sxpert/PyATEM
