# Neopixel-bitmap
A Raspberry Pi Pico program to display images on a Neopixel RGB LED array.

NeopixelBitmap.py:  
This will display bitmaps on a 10x16 Neopixel with support for chaining multiple Neopixels together if you want something larger. This is written in Micropython for the Raspberry Pi Pico. My assumption is that it will work on any RP4020 based microcontroller board with the Micropython firmware flashed to it.

BitmapToArray.py:  
This generates the array used to display a bitmap in NeopixelBitmap.py. Written using Python 3.
