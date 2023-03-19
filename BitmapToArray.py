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
mainLayout = [
    [sg.Text('This program will generate an array to use in BitmapData.py')],
    [sg.Text(' ')],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Text('Select a bitmap'), sg.InputText(), sg.FileBrowse(file_types=(('Text Files', '*.bmp'),))],
    [sg.Text('It must be 1 bit or 24 bit color. This program does not support anything else.')],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Text('Is this a 24 bit or 1 bit color bitmap?'),
     sg.Radio('24 bit', 'radio1', default=True), sg.Radio('1 bit', 'radio1')],
    [sg.Text('This program will not auto-detect the 1 or 24 bit so it won\'t work if you don\'t select correctly.')],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Text('Name or describe your image.'), sg.InputText('Hello world')],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Text('Pick an image number starting at 0. Integer only.'), sg.InputText(0)],
    [sg.Text('---------------------------------------------------------------------------------------------------')],
    [sg.Button('Copy Array To Clipboard'), sg.Button('Cancel')]]

dataEntered = False
window = sg.Window('Window Title', mainLayout)
while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
        break
    if event == 'Copy Array To Clipboard':
        dataEntered = True
        print('You entered ', values[0], values[1], values[2], values[3], values[3])
        filename = values[0]
        if values[1]:
            bitDepth = 24
        else:
            bitDepth = 1
        imageName = str(values[3])
        imageNumber = str(values[4])
        window.close()

if dataEntered:
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
        codeStr = codeStr + '    # 24 bit Bitmap\n'
        codeStr = codeStr + '    # ' + imageName + '\n'
        codeStr = codeStr + '    # This array is stored as [width],[height],[R_list],[G_list],[B_list]' + '\n'
        codeStr = codeStr + '    if BitmapNumber == ' + imageNumber + ':\n'
        codeStr = codeStr + '        return [' + widthString + ',' + heightString + ',' + rString + ',' + gString + ',' + bString + ']'

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
        codeStr = codeStr + '    # 1 bit Bitmap\n'
        codeStr = codeStr + '    # ' + imageName + '\n'
        codeStr = codeStr + '    # This array is stored as [width],[height],[pixel_list]' + '\n'
        codeStr = codeStr + '    if BitmapNumber == ' + imageNumber + ':\n'
        codeStr = codeStr + '        return [' + widthString + ',' + heightString + ',' + oneBitImageString + ']'

    pyperclip.copy(codeStr)

    copiedSuccessLayout = [
        [sg.Text('If nothing has gone wrong, the bitmap array has been copied to your clipboard.')],
        [sg.Text('Try pasting it somewhere to confirm.')],
        [sg.Button('Exit')]]
    window = sg.Window('Window Title', copiedSuccessLayout)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Exit':  # if user closes window or clicks cancel
            break

print(codeStr)

# if not os.path.isfile('Output.txt'):
#     f = open('Output.txt', 'x')
# f = open('Output.txt', 'w')
# f.write('')
# f = open('Output.txt', 'a')
# f.write(codeStr)
# f.close()
