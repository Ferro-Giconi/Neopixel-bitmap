# Waveshare 160 Neopixel Board Basic
# Tony Goodhew 19th April 2022 for thepihut.com
import array
import utime
from machine import Pin
import rp2
import random
import math
import micropython
import _thread

# in variable names: w = width on the x axis and h = height on the y axis

# define how many Neopixels you have, width and height
# when connecting multiple Neopixels, arrange them in order from left to right, then top to bottom.
global screens_w
screens_w = 1
global screens_h
screens_h = 2
# if there is a gap between Neopixels, define the gap size in number of LEDs.
# this will take gaps into account when displaying images or text for a more normal look.
# gap_w = gap width in number of pixels between horizontally places Neopixels
# gap_h = gap height in number of pixels between vertically stacked Neopixels
# Integer only. Decimals will probably break it.
global gap_w
gap_w = 0
global gap_h
gap_h = 0

# I couldn't figure out how to check if the second thread is locked correctly so instead I'm using a global variable
global threadLocked
threadLocked = False

# Configure the number of WS2812 LEDs.
PIN_NUM = 6
brightness = 0.1
# set total number of LEDs. Each neopixel has 160 LEDs, 10H 16W.
screen_total_width = screens_w * 16 + (screens_w * gap_w - gap_w)
screen_total_height = screens_h * 10 + (screens_h * gap_h - gap_h)
NUM_LEDS = screen_total_width * screen_total_height

#calculates which X and Y cordinates will not be used if there are gaps defined
global missing_x
missing_x = []
for i in range(16,screen_total_width+1,1):
    ii = i
    while ii > 16:
        ii = ii - 16 - gap_w
    if ii <= 0:
        missing_x.append(i)

global missing_y
missing_y = []
for i in range(10,screen_total_height+1,1):
    ii = i
    while ii > 10:
        ii = ii - 10 - gap_h
    if ii <= 0:
        missing_y.append(i)

# Boilerplate Neopixel driver for RP2040
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()

# Create the StateMachine with the ws2812 program, outputting on pin
# You can also increase the frequency to improve performance by 1-2ms
sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(PIN_NUM))

# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)

# Display a pattern on the LEDs via an array of LED RGB values.
ar = array.array("I", [0 for _ in range(NUM_LEDS)])

####################### Functions ##############################

def pixels_show():
    dimmer_ar = array.array("I", [0 for _ in range(NUM_LEDS)])
    for i,c in enumerate(ar):
        r = int(((c >> 8) & 0xFF) * brightness)
        g = int(((c >> 16) & 0xFF) * brightness)
        b = int((c & 0xFF) * brightness)
        dimmer_ar[i] = (g<<16) + (r<<8) + b
    sm.put(dimmer_ar, 8)

def pixels_set(i, colour):
    ar[i] = (colour[1]<<16) + (colour[0]<<8) + colour[2]
    
def xy_set(x, y, colour):
    # +1 to x and y allows me to do pixel math in this function starting at 1 when the input x and y start at 0.
    # it's just easier for me to figure out the math that way.
    x = x + 1
    y = y + 1
    valid_pixel = True
    # Check if the pixel you want to set is outside the size of the
    # screen to avoid wasting CPU cycles on pixels that you can't see
    if (x <= 0) or (y <= 0) or (x > screen_total_width) or (y > screen_total_height):
        valid_pixel = False
    # If you configured a gap between neopixels, check if the pixel is on a gap
    if valid_pixel:
        for i in missing_x:
            if x == i:
                valid_pixel = False
        for i in missing_y:
            if y == i:
                valid_pixel = False
    # if you have a valid pixel, figure out which Neopixel to use
    if valid_pixel:
        screen_x = 1
        screen_y = 1
        xx = x
        yy = y
        while xx > 16:
            screen_x = screen_x + 1
            xx = xx - 16 - gap_w
        while yy > 10:
            screen_y = screen_y + 1
            yy = yy - 10 - gap_h
        screen_number = screen_x + ((screen_y - 1) * screens_w)
        
        #calculate which pixel to set on which Neopixel
        pos = ((screen_number - 1) * 160) + (xx - 1) + (yy - 1) * 16
        pixels_set(pos, colour)

def pixels_fill(colour):
    _thread.start_new_thread(pixels_fill_thread2,((colour),))
    for i in range(math.ceil(len(ar)/2)):
        pixels_set(i, colour)
    # wait for the second thread to finish before continuing
    while threadLocked:
        utime.sleep_ms(1)

def pixels_fill_thread2(colour):
    global threadLocked
    threadLocked = True
    for i in range(math.ceil(len(ar)/2),len(ar)):
        pixels_set(i, colour)
    threadLocked = False
    _thread.exit()

def clear():
    colour = (0,0,0)
    pixels_fill(colour)
    
def rect(x,y,w,h,r,g,b):
    # Hollow square at (x,y), w pixels wide coloured (r,g,b)
    _thread.start_new_thread(rect_threads,(x,y,w,h,r,g,b,1))
    rect_threads(x,y,w,h,r,g,b,0)
    while threadLocked:
        utime.sleep_ms(1)

def rect_threads(x,y,w,h,r,g,b,threadNum):
    if threadNum:
        global threadLocked
        threadLocked = True
        cc = (r,g,b)
        for i in range(x,x+w):
            xy_set(i,y,cc)       # Top
            xy_set(i,y+h-1,cc)   # Bottom
    else:
        cc = (r,g,b)
        for i in range(y+1,y+h):
            xy_set(x,i,cc)       # Left
            xy_set(x+w-1,i,cc)   # Right
    if threadNum:
        threadLocked = False

def vert(x,y,l,r,g,b):
    # Vertical line at (x,y) of length l coloured (r,g,b)
    cc = (r,g,b)
    for i in range(l):
        xy_set(x,i,cc)

def horiz(x,y,l,r,g,b):
    # Horizontal line from (x,y) of length l coloured (r,g,b)
    cc = (r,g,b)
    for i in range(l):
        xy_set(i,y,cc)

def bitmap_set_fast(x,y,w,h,r,g,b):
    # bitmap_set(x_coordinate, y_coordinate, bmp_width, bmp_height, bmp_red, bmp_green, bmp_blue)
    # set the pixels for a bitmap. Treats 
    # start at pixel zero
    PxNum = 0
    for i in range(h):
        for j in range(w):
            rr = r[PxNum]
            gg = g[PxNum]
            bb = b[PxNum]
            # use the heavily modified xy_set to set each pixel
            xy_set(j+x,i+y,(rr,gg,bb))
            PxNum = PxNum + 1

def bitmap_set24(x,y,w,h,r,g,b,ga=1,br=1,tr=False):
    # bitmap_set(x_coord, y_coord, bmp_width, bmp_height, bmp_r, bmp_g, bmp_b, gama, brightness, transparency)
    # use for placing a 24 bit bitmap somewhere on screen.
    # start a thread to process the upper half of the pixels
    _thread.start_new_thread(bitmap_set24_threads,(x,y,w,h,r,g,b,ga,br,tr,1))
    # start a the function to run at the same time as the thread to process the lower half of the pixels
    bitmap_set24_threads(x,y,w,h,r,g,b,ga,br,tr,0)
    # wait for the thread to finish if it isn't done yet
    while threadLocked:
        utime.sleep_ms(1)

def bitmap_set24_threads(x,y,w,h,r,g,b,ga,br,tr,threadNum):
    # do not call this function directly. This is used by bitmap_set24 to run my innefficient code on
    # two cores at once to improve performance
    if threadNum:
        global threadLocked
        threadLocked = True
        PxNum = w*math.ceil(h/2)
        range1 = math.ceil(h/2)
        range2 = h
    else:
        PxNum = 0
        range1 = 0
        range2 = math.ceil(h/2)
    for i in range(range1,range2,1):
        for j in range(w):
            # If transparency is enabled and r, g, and b are all 0
            if tr and (r[PxNum]+g[PxNum]+b[PxNum] > 0):
                # compress the data range from 0-255 to 0-246 to compensate for the 0-9 pixels all being black
                rr = r[PxNum]*246/255
                gg = g[PxNum]*246/255
                bb = b[PxNum]*246/255
                # adjust the brightness
                rr = rr*br
                gg = gg*br
                bb = bb*br
                # This is a crude gama adjustment formula which can help make bitmaps look more normal instead of washed out
                rr = math.pow(rr,ga) * 255 / math.pow(255,ga)
                gg = math.pow(gg,ga) * 255 / math.pow(255,ga)
                bb = math.pow(bb,ga) * 255 / math.pow(255,ga)
                #undo the compression
                rr = math.ceil(rr+9)
                gg = math.ceil(gg+9)
                bb = math.ceil(bb+9) 
                # use the heavily modified xy_set to set each pixel
                xy_set(j+x,i+y,(rr,gg,bb))
            PxNum = PxNum + 1
    if threadNum == 1:
        threadLocked = False
        _thread.exit()

def bitmap_set1(x,y,p,r,g,b):
    # bitmap_set(x_coord, y_coord, pixel_data,color)
    # Sets a 1 bit bitmap using a defined color
    PxNum = 0
    for i in range(len(p)):
        for j in range(len(p[i])):
            # use the heavily modified xy_set to set each pixel
            xy_set(j+x,i+y,(p[i][j]*r,p[i][j]*g,p[i][j]*b))
            PxNum = PxNum + 1

def button_handler():
    asdf = "nothing here yet"

def targetFT(ms=-1):
    # define a target frame time in MS to improve frame time consistency.
    # use 'frameTime = targetFT() at the begining of your frame code
    # use targetFT(frameTime)
    utime.sleep_ms(10)
    asdf = "nothing here yet"

def adjust_gama_list(color,ga):
    # this is a crude way to adjust the gama so that images don't display blown out on the screen
    for i in range(len(color)):
        color[i] = math.trunc(math.pow(color[i],ga) * 255 / math.pow(255,ga))
    return(color)

def adjust_gama(color,ga):
    # this is a crude way to adjust the gama so that images don't display blown out on the screen
    color = math.trunc(math.pow(color,ga) * 255 / math.pow(255,ga))
    return(color)


# define the quantity of bitmaps that will be defined starting at 0
qtyOfBitmaps = 1
bmpW = [[],[]]
bmpH = [[],[]]
bmpR = [[],[]]
bmpG = [[],[]]
bmpB = [[],[]]

# ======================= BITMAP DATA ======================= 


# define bitmap width and height of image number 0
bmpW[0] = 16
bmpH[0] = 20
# define the bitmap as an array of RGB values from 0 to 255 of image number 0
bmpR[0] = [0,0,0,0,0,0,108,0,0,0,0,0,0,0,0,0,0,47,47,47,47,108,169,108,108,108,47,54,47,0,0,0,0,47,222,54,54,47,169,
           169,169,169,108,71,54,0,0,0,0,47,222,54,54,47,169,169,169,169,108,71,54,0,0,0,0,47,222,222,47,54,169,169,
           169,108,108,71,54,0,0,0,0,47,222,222,54,71,71,169,169,169,169,108,54,0,0,0,0,47,54,222,54,71,71,71,108,108,
           108,54,54,0,0,0,0,0,47,47,71,71,54,47,47,71,71,47,0,0,0,0,0,0,47,47,71,71,54,47,47,71,71,47,0,0,0,0,0,0,0,
           54,71,71,47,255,148,71,71,148,0,0,0,0,0,0,108,54,71,71,47,255,148,71,71,148,101,148,101,0,0,108,138,169,253,
           71,54,255,148,71,71,148,54,101,101,0,0,0,108,138,169,253,71,71,71,71,71,71,47,72,0,0,0,0,108,138,169,253,71,
           71,71,71,71,71,47,72,0,0,0,0,0,108,108,54,71,71,71,71,54,47,72,0,0,0,0,0,0,0,138,138,253,71,71,138,138,0,0,
           0,0,0,0,0,0,138,222,169,169,253,71,71,138,138,0,0,0,0,0,0,0,138,169,138,47,169,253,71,71,138,138,0,0,0,0,0,
           0,138,169,138,47,169,253,71,71,138,138,0,0,0,0,0,138,169,222,47,138,222,253,71,54,169,138,0,0,0]
bmpG[0] = [0,0,0,0,0,0,32,0,0,0,0,0,0,0,0,0,0,11,11,11,11,32,68,32,32,32,11,20,11,0,0,0,0,11,255,20,20,11,68,68,68,68,
           32,34,20,0,0,0,0,11,255,20,20,11,68,68,68,68,32,34,20,0,0,0,0,11,255,255,11,20,68,68,68,32,32,34,20,0,0,0,0,
           11,255,255,20,34,34,68,68,68,68,32,20,0,0,0,0,11,20,255,20,34,34,34,32,32,32,20,20,0,0,0,0,0,11,11,34,34,20,
           11,11,34,34,11,0,0,0,0,0,0,11,11,34,34,20,11,11,34,34,11,0,0,0,0,0,0,0,20,34,34,11,255,224,34,34,224,0,0,0,0,
           0,0,32,20,34,34,11,255,224,34,34,224,166,224,166,0,0,32,54,68,165,34,20,255,224,34,34,224,20,166,166,0,0,0,
           32,54,68,165,34,34,34,34,34,34,11,123,0,0,0,0,32,54,68,165,34,34,34,34,34,34,11,123,0,0,0,0,0,32,32,20,34,34,
           34,34,20,11,123,0,0,0,0,0,0,0,54,54,165,34,34,54,54,0,0,0,0,0,0,0,0,54,255,68,68,165,34,34,54,54,0,0,0,0,0,
           0,0,54,68,54,11,68,165,34,34,54,54,0,0,0,0,0,0,54,68,54,11,68,165,34,34,54,54,0,0,0,0,0,54,68,255,11,54,255,
           165,34,20,68,54,0,0,0]
bmpB[0] = [0,0,0,0,0,0,56,0,0,0,0,0,0,0,0,0,0,61,61,61,61,56,100,56,56,56,61,67,61,0,0,0,0,61,248,67,67,61,100,100,100,
           100,56,85,67,0,0,0,0,61,248,67,67,61,100,100,100,100,56,85,67,0,0,0,0,61,248,248,61,67,100,100,100,56,56,85,67,
           0,0,0,0,61,248,248,67,85,85,100,100,100,100,56,67,0,0,0,0,61,67,248,67,85,85,85,56,56,56,67,67,0,0,0,0,0,61,61,85,
           85,67,61,61,85,85,61,0,0,0,0,0,0,61,61,85,85,67,61,61,85,85,61,0,0,0,0,0,0,0,67,85,85,61,255,218,85,85,218,0,0,0,0,
           0,0,56,67,85,85,61,255,218,85,85,218,161,218,161,0,0,56,80,100,157,85,67,255,218,85,85,218,67,161,161,0,0,0,56,
           80,100,157,85,85,85,85,85,85,61,119,0,0,0,0,56,80,100,157,85,85,85,85,85,85,61,119,0,0,0,0,0,56,56,67,85,85,85,
           85,67,61,119,0,0,0,0,0,0,0,80,80,157,85,85,80,80,0,0,0,0,0,0,0,0,80,248,100,100,157,85,85,80,80,0,0,0,0,0,0,0,80,
           100,80,61,100,157,85,85,80,80,0,0,0,0,0,0,80,100,80,61,100,157,85,85,80,80,0,0,0,0,0,80,100,248,61,80,248,157,85,
           67,100,80,0,0,0]

bmpW[1] = 16
bmpH[1] = 20
bmpR[1] = [0,0,0,0,0,0,108,0,0,0,0,0,0,0,0,0,0,47,47,47,47,108,169,108,108,108,47,54,47,0,0,0,0,47,222,54,54,47,169,169,169,169,
           108,71,54,0,0,0,0,47,222,54,54,47,169,169,169,169,108,71,54,0,0,0,0,47,222,222,47,54,169,169,169,108,108,71,54,0,0,0,0,
           47,222,222,54,71,71,169,169,169,169,108,54,0,0,0,0,47,54,222,54,71,71,71,108,108,108,54,54,0,0,0,0,0,47,47,71,71,54,47,
           47,71,71,47,0,0,0,0,0,0,47,47,71,71,54,47,47,71,71,47,0,0,0,0,0,0,0,54,71,71,47,255,148,71,71,148,0,0,0,0,0,0,108,54,71,
           71,47,255,148,71,71,148,101,148,101,0,0,108,138,169,253,71,54,255,148,71,71,148,54,101,101,0,0,0,108,138,169,253,71,71,71,
           71,71,71,47,72,0,0,0,0,108,138,169,253,71,71,71,71,71,71,47,72,0,0,0,0,0,108,108,54,71,71,71,71,54,47,72,0,0,0,0,0,0,0,
           138,138,253,71,71,138,138,0,0,0,0,0,0,0,0,138,222,169,169,253,71,71,138,138,0,0,0,0,0,0,0,138,169,138,47,169,253,71,71,
           138,138,0,0,0,0,0,0,138,169,138,47,169,253,71,71,138,138,0,0,0,0,0,138,169,222,47,138,222,253,71,54,169,138,0,0,0]
bmpG[1] = [0,0,0,0,0,0,32,0,0,0,0,0,0,0,0,0,0,11,11,11,11,32,68,32,32,32,11,20,11,0,0,0,0,11,255,20,20,11,68,68,68,68,32,34,20,
           0,0,0,0,11,255,20,20,11,68,68,68,68,32,34,20,0,0,0,0,11,255,255,11,20,68,68,68,32,32,34,20,0,0,0,0,11,255,255,20,34,34,
           68,68,68,68,32,20,0,0,0,0,11,20,255,20,34,34,34,32,32,32,20,20,0,0,0,0,0,11,11,34,34,20,11,11,34,34,11,0,0,0,0,0,0,11,
           11,34,34,20,11,11,34,34,11,0,0,0,0,0,0,0,20,34,34,11,255,224,34,34,224,0,0,0,0,0,0,32,20,34,34,11,255,224,34,34,224,166,
           224,166,0,0,32,54,68,165,34,20,255,224,34,34,224,20,166,166,0,0,0,32,54,68,165,34,34,34,34,34,34,11,123,0,0,0,0,32,54,68,
           165,34,34,34,34,34,34,11,123,0,0,0,0,0,32,32,20,34,34,34,34,20,11,123,0,0,0,0,0,0,0,54,54,165,34,34,54,54,0,0,0,0,0,0,0,0,
           54,255,68,68,165,34,34,54,54,0,0,0,0,0,0,0,54,68,54,11,68,165,34,34,54,54,0,0,0,0,0,0,54,68,54,11,68,165,34,34,54,54,0,0,
           0,0,0,54,68,255,11,54,255,165,34,20,68,54,0,0,0]
bmpB[1] = [0,0,0,0,0,0,56,0,0,0,0,0,0,0,0,0,0,61,61,61,61,56,100,56,56,56,61,67,61,0,0,0,0,61,248,67,67,61,100,100,100,100,56,
           85,67,0,0,0,0,61,248,67,67,61,100,100,100,100,56,85,67,0,0,0,0,61,248,248,61,67,100,100,100,56,56,85,67,0,0,0,0,61,248,
           248,67,85,85,100,100,100,100,56,67,0,0,0,0,61,67,248,67,85,85,85,56,56,56,67,67,0,0,0,0,0,61,61,85,85,67,61,61,85,85,61,
           0,0,0,0,0,0,61,61,85,85,67,61,61,85,85,61,0,0,0,0,0,0,0,67,85,85,61,255,218,85,85,218,0,0,0,0,0,0,56,67,85,85,61,255,
           218,85,85,218,161,218,161,0,0,56,80,100,157,85,67,255,218,85,85,218,67,161,161,0,0,0,56,80,100,157,85,85,85,85,85,85,
           61,119,0,0,0,0,56,80,100,157,85,85,85,85,85,85,61,119,0,0,0,0,0,56,56,67,85,85,85,85,67,61,119,0,0,0,0,0,0,0,80,80,157,
           85,85,80,80,0,0,0,0,0,0,0,0,80,248,100,100,157,85,85,80,80,0,0,0,0,0,0,0,80,100,80,61,100,157,85,85,80,80,0,0,0,0,0,0,80,
           100,80,61,100,157,85,85,80,80,0,0,0,0,0,80,100,248,61,80,248,157,85,67,100,80,0,0,0]

# this 
bmp1 = [
    [1,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,1,0,1,1,0,0,0,0,1],
    [1,0,1,0,1,0,0,0,1,0,0,1,1],
    [1,0,1,0,1,0,1,1,1,0,1,0,1],
    [1,0,1,1,1,0,1,1,1,0,1,1,1]]


# ================  Replace everyting before this line  ================
# ================ with the output from the RGB program ================

# Due to memory constaints and crappy code, loading multiple "large" bitmaps is problematic.
# For some reason, just loading a bitmap doesn't use much ram, but modifying it uses a lot.
# Because of this, adjuustments to images should be used sparingly except as needed to improve
# frame times during render.
# bmpR[0] = adjust_gama_list(bmpR[0],1.8)
# bmpG[0] = adjust_gama_list(bmpG[0],1.8)
# bmpB[0] = adjust_gama_list(bmpB[0],1.8)


micropython.mem_info()
TimeCounter = utime.ticks_ms()
print("Loading took " + str(utime.ticks_ms()-TimeCounter) + "ms")

# ========= Your code to control what is displayed goes here ========


# define which bitmap to use
bmpToUse = 0
TimeCounter = utime.ticks_ms()
for i in range(17,-17,-1):
    # this example scrolls the bitmap from right to left
    # bitmap_set defines which bitmap to use.
    # normally clear() would be needed, but with a solid color background it isn't needed so it is commented out
    # clear()
    # draw a colorful background
    rect(0,0,16,20,10,0,0)
    rect(1,1,14,18,0,10,0)
    rect(2,2,12,16,0,0,10)
    rect(3,3,10,14,10,0,10)
    rect(4,4,8,12,10,10,0)
    rect(5,5,6,10,10,0,0)
    rect(6,6,4,8,0,10,0)
    rect(7,7,2,6,0,0,10)
    # draw the bitmap over the background with black pixels treated as transparent
    bitmap_set24(i,0,bmpW[bmpToUse],bmpH[bmpToUse],bmpR[bmpToUse],bmpG[bmpToUse],bmpB[bmpToUse],1.8,1,True)
    # draw a few random pixels over the bitmap
    for i in range(12):
        xy_set(math.ceil(screen_total_width*random.random()),math.ceil(screen_total_height*random.random()),(200,200,200))
    # display the result
    pixels_show()
print("Animation took " + str(utime.ticks_ms()-TimeCounter) + "ms")
utime.sleep_ms(100)


for i in range(17,-17,-1):
    clear()
    bitmap_set1(i,2,bmp1,40,40,40)
    pixels_show()


clear()
pixels_show()