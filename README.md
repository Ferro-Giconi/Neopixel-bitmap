# Neopixel-bitmap
A Raspberry Pi Pico program to display images on a Neopixel RGB LED array.

PicoBitmap.py:
This is written in Micropython for the Raspberry Pi Pico. It probably works on any RP4020 based microcontroller with the Micropython firmware flashed to it.

BitmapToArray.py:
This is written in normal Python 3. It is a separate program that should be run on the computer to generate an array of RGB values to paste into the PicoBitmap.py program to store bitmaps as an array. I would prefer to figure out how to do this conversion on the fly on the RPi Pico but haven't figured out how.
