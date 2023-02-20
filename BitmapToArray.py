import string
import numpy
from PIL import Image
from numpy import asarray
import os.path
import PySimpleGUI as sg
import pyperclip
import sys

# variables that control settings
# Should black pixels be treated as transparency?
# If they are not treated as transparent, they will be converted to the value 4 which is
# not high enough to turn on a pixel on a Neopixel.
# If black is treated as transparent,
blackAsTransparent = False
# This is the filename, duh!
filename = 'rpi.bmp'
# Set which image number this is. Values can range form 0 to anything. Integer only.
imageNumber = str(0)
numpy.set_printoptions(threshold=sys.maxsize)
# display a window
sg.theme('DarkAmber')
layout = [
    [sg.Text('This program will generate an array to use in NeopixelBitmap.py')],
    [sg.Text('It currently will not tell you if it worked. You have to try pasting.')],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Text('Select a bitmap'), sg.InputText(), sg.FileBrowse(file_types=(('Text Files', '*.bmp'),))],
    [sg.Text('It must be 1 bit or 24 bit color. This program does not support anything else.')],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Text('Is this a 24 bit or 1 bit color bitmap?'),
     sg.Radio('24 bit', 'radio1', default=True), sg.Radio('1 bit', 'radio1')],
    [sg.Text('This program will not auto-detect the 1 or 24 bit so it won\'t work if you don\'t select correctly.')],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Text('Pick an image number starting at 0. Integer only.'), sg.InputText(0)],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Button('Copy Array To Clipboard'), sg.Button('Cancel')]]

window = sg.Window('Window Title', layout)
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
        break
    print('You entered ', values[0], values[1], values[2], values[3])
    filename = values[0]
    if values[1]:
        bitDepth = 24
    else:
        bitDepth = 1
    imageNumber = str(values[3])
    window.close()

# Load the bitmap then put all the RGB values into an array.
imageFile = Image.open(filename)
# set values to an array
imageArray = asarray(imageFile, dtype=int)
codeStr = ''
# print(imageArray)
if bitDepth == 24:
    # Store all the R, G, and B value into a comma separated string which will be treated
    # as an array by the output code.
    rString = '['
    gString = '['
    bString = '['
    for i in range(len(imageArray)):
        for j in range(len(imageArray[i])):
            for k in range(len(imageArray[i][j])):
                nextValue = numpy.array2string(imageArray[i][j][k])
                # an RGB value of 0,0,0 will be treated as a transparent pixel in the NeoPixel code
                # so if blackAsTransparent is false, set zeros to 1. The Neopixel displays nothing
                # when the value is 1.
                if (nextValue == 0) and (blackAsTransparent is False):
                    nextValue = 1
                if k == 0:
                    rString = rString + nextValue + ','
                if k == 1:
                    gString = gString + nextValue + ','
                if k == 2:
                    bString = bString + nextValue + ','
    # there is an extra comma at the end of the strings, so remove them
    # also add the ending bracket at the end
    widthString = "[" + str(imageFile.size[0]) + "]"
    heightString = "[" + str(imageFile.size[1]) + "]"
    rString = rString[:-1] + ']'
    gString = gString[:-1] + ']'
    bString = bString[:-1] + ']'

    # generate the array to be pasted into the code
    codeStr = codeStr + '# Array for bitmap ' + imageNumber + '\n'
    codeStr = codeStr + '# This array is stored as [width],[height],[R_list],[G_list],[B_list]' + '\n'
    codeStr = codeStr + 'bitmap[' + imageNumber + '] = '
    codeStr = codeStr + '[' + widthString + ',' + heightString + ',' + rString + ',' + gString + ',' + bString + ']'

if bitDepth == 1:
    widthString = "[" + str(imageFile.size[0]) + "]"
    heightString = "[" + str(imageFile.size[1]) + "]"
    oneBitImageString = numpy.array2string(imageArray)
    print(oneBitImageString)
    oneBitImageString = oneBitImageString.replace(" ", ",")
    oneBitImageString = oneBitImageString.replace(",,", ",")
    oneBitImageString = oneBitImageString.replace("\n", "")
    oneBitImageString = oneBitImageString.replace("[", "")
    oneBitImageString = '[' + oneBitImageString.replace("]", "") + ']'
    codeStr = codeStr + '# Array for bitmap ' + imageNumber + '\n'
    codeStr = codeStr + '# This array is stored as [width],[height],[pixel_list]' + '\n'
    codeStr = codeStr + 'bitmap[' + imageNumber + '] = '
    codeStr = codeStr + '[' + widthString + ',' + heightString + ',' + oneBitImageString + ']'


pyperclip.copy(codeStr)

print(codeStr)

# if not os.path.isfile('Output.txt'):
#     f = open('Output.txt', 'x')
# f = open('Output.txt', 'w')
# f.write('')
# f = open('Output.txt', 'a')
# f.write(codeStr)
# f.close()
