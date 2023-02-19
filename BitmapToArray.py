
import string
import numpy
from PIL import Image
from numpy import asarray
import os.path

# variables that control settings
# Should black pixels be treated as transparency?
blackAsTransparent = False
# This is the filename, duh!
filename = 'rpi.bmp'
# Set which image number this is. Values can range form 0 to anything. Integer only.
imageNumber = 0
imageNumber = str(imageNumber)



# load the bitmap then put all the RGB values into an array
# Only tested with bitmaps. They must be 24 bit color.
imageFile = Image.open(filename)
# set values to an array
rgbArray = asarray(imageFile, dtype=int)

print(rgbArray)

# Store all the R, G, and B value into a comma separated string which will be treated
# as an array by the output code.
rString = 'bmpRR[' + imageNumber + '] = ['
gString = 'bmpGG[' + imageNumber + '] = ['
bString = 'bmpBB[' + imageNumber + '] = ['
for i in range(len(rgbArray)):
    for j in range(len(rgbArray[i])):
        for k in range(len(rgbArray[i][j])):
            nextValue = numpy.array2string(rgbArray[i][j][k])
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
rString = rString[:-1] + ']'
gString = gString[:-1] + ']'
bString = bString[:-1] + ']'

CodeStr = ''
CodeStr = CodeStr + '# define bitmap width and height of image number ' + imageNumber + '\n'
CodeStr = CodeStr + 'bmpW[' + imageNumber + '] = ' + str(imageFile.size[0]) + '\n'
CodeStr = CodeStr + 'bmpH[' + imageNumber + '] = ' + str(imageFile.size[1]) + '\n\n'
CodeStr = CodeStr + '# define the bitmap as an array of RGB values from 0 to 255 of image number ' + imageNumber + '\n'
CodeStr = CodeStr + rString + '\n' + gString + '\n' + bString + '\n'

print(CodeStr)

if not os.path.isfile('Output.txt'):
    f = open('Output.txt', 'x')
f = open('Output.txt', 'w')
f.write('')
f = open('Output.txt', 'a')
f.write(CodeStr)
f.close()
