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
screens_w = 2
global screens_h
screens_h = 1
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
        xy_set(i+x,y,cc)

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

def bitmap_set24(x,y,ia,ga=1,br=1,tr=False):
    # bitmap_set(x_coord, y_coord, image_array, gama, brightness, transparency)
    # use for placing a 24 bit bitmap somewhere on screen.
    # start a thread to process the lower half of the pixels

    _thread.start_new_thread(bitmap_set24_threads,(x,y,ia,ga,br,tr,1))
    # start a the function to run at the same time as the thread to process the upper half of the pixels
    bitmap_set24_threads(x,y,ia,ga,br,tr,0)
    # wait for the thread to finish if it isn't done yet
    while threadLocked:
        utime.sleep_ms(1)

def bitmap_set24_threads(x,y,ia,ga,br,tr,threadNum):
    # do not call this function directly. This is used by bitmap_set24 to run my innefficient code on
    # two cores at once to improve performance
    w = ia[0][0]
    h = ia[1][0]
    r = ia[2]
    g = ia[3]
    b = ia[4]
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
            # if transparency is disabled, or if it is enabled and the r,g,b isn't 0,0,0, draw the pixel.
            if tr and (r[PxNum]+g[PxNum]+b[PxNum] > 0) or (not tr):
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

def bitmap_set1(x,y,ia,r,g,b,tr=False):
    # bitmap_set(x_coord, y_coord, image_array,color,transparency)
    # Sets a 1 bit bitmap using a defined color
    # start a thread to process the lower half of the pixels

    _thread.start_new_thread(bitmap_set1_threads,(x,y,ia,r,g,b,tr,1))
    # start a the function to run at the same time as the thread to process the upper half of the pixels
    bitmap_set1_threads(x,y,ia,r,g,b,tr,0)
    # wait for the thread to finish if it isn't done yet
    while threadLocked:
        utime.sleep_ms(1)

            
def bitmap_set1_threads(x,y,ia,r,g,b,tr,threadNum):
    # bitmap_set(x_coord, y_coord, image_array,color,transparency)
    # Sets a 1 bit bitmap using a defined color
    w = ia[0][0]
    h = ia[1][0]
    p = ia[2]
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
            if tr and p[PxNum] or not tr and j < 33:
                xy_set(j+x,i+y,(p[PxNum]*r,p[PxNum]*g,p[PxNum]*b))
            PxNum = PxNum + 1
    if threadNum:
        threadLocked = False

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
qtyOfBitmaps = 4
bitmap = [[],[],[],[],[]]

# ======================= BITMAP DATA ======================= 

# test image of jayde's head
# Array for bitmap 0
# This array is stored as [width],[height],[R_list],[G_list],[B_list]
bitmap[0] = [[16],[20],[0,0,0,0,3,70,70,70,70,70,70,70,70,70,70,70,0,0,0,3,70,70,70,70,70,70,70,70,70,70,3,70,0,0,3,70,70,70,70,70,70,70,70,70,70,3,70,70,0,3,70,70,70,70,70,70,70,70,70,70,70,3,70,3,0,3,70,70,70,70,70,70,70,70,70,70,147,3,70,3,3,70,70,70,70,70,70,70,70,70,70,3,147,3,70,3,0,3,70,70,70,70,70,70,70,70,3,3,3,0,3,0,0,3,147,70,3,70,70,70,70,70,3,0,0,0,0,0,3,147,147,147,3,147,70,70,70,70,3,0,0,0,0,0,3,147,147,3,147,147,147,147,70,70,3,0,0,0,0,0,3,147,147,3,147,147,147,147,147,147,3,0,0,0,0,0,3,147,147,3,147,147,147,147,147,147,3,0,0,0,0,0,0,3,147,147,3,147,147,147,147,3,0,0,0,0,0,0,0,3,147,147,3,147,147,147,147,3,0,0,0,0,0,0,3,147,147,147,3,147,147,147,147,3,0,0,0,0,0,0,3,147,147,147,3,147,147,147,147,3,0,0,0,0,0,0,3,147,147,3,147,147,147,147,147,3,0,0,0,0,0,0,0,3,3,0,3,3,147,3,3,0,0,0,0,0,0,0,0,0,0,0,0,3,147,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,0,0],[0,0,0,0,3,34,34,34,34,34,34,34,34,34,34,34,0,0,0,3,34,34,34,34,34,34,34,34,34,34,3,34,0,0,3,34,34,34,34,34,34,34,34,34,34,3,34,34,0,3,34,34,34,34,34,34,34,34,34,34,34,3,34,3,0,3,34,34,34,34,34,34,34,34,34,34,225,3,34,3,3,34,34,34,34,34,34,34,34,34,34,3,225,3,34,3,0,3,34,34,34,34,34,34,34,34,3,3,3,0,3,0,0,3,225,34,3,34,34,34,34,34,3,0,0,0,0,0,3,225,225,225,3,225,34,34,34,34,3,0,0,0,0,0,3,225,225,3,225,225,225,225,34,34,3,0,0,0,0,0,3,225,225,3,225,225,225,225,225,225,3,0,0,0,0,0,3,225,225,3,225,225,225,225,225,225,3,0,0,0,0,0,0,3,225,225,3,225,225,225,225,3,0,0,0,0,0,0,0,3,225,225,3,225,225,225,225,3,0,0,0,0,0,0,3,225,225,225,3,225,225,225,225,3,0,0,0,0,0,0,3,225,225,225,3,225,225,225,225,3,0,0,0,0,0,0,3,225,225,3,225,225,225,225,225,3,0,0,0,0,0,0,0,3,3,0,3,3,225,3,3,0,0,0,0,0,0,0,0,0,0,0,0,3,225,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,0,0],[0,0,0,0,3,85,85,85,85,85,85,85,85,85,85,85,0,0,0,3,85,85,85,85,85,85,85,85,85,85,3,85,0,0,3,85,85,85,85,85,85,85,85,85,85,3,85,85,0,3,85,85,85,85,85,85,85,85,85,85,85,3,85,3,0,3,85,85,85,85,85,85,85,85,85,85,216,3,85,3,3,85,85,85,85,85,85,85,85,85,85,3,216,3,85,3,0,3,85,85,85,85,85,85,85,85,3,3,3,0,3,0,0,3,216,85,3,85,85,85,85,85,3,0,0,0,0,0,3,216,216,216,3,216,85,85,85,85,3,0,0,0,0,0,3,216,216,3,216,216,216,216,85,85,3,0,0,0,0,0,3,216,216,3,216,216,216,216,216,216,3,0,0,0,0,0,3,216,216,3,216,216,216,216,216,216,3,0,0,0,0,0,0,3,216,216,3,216,216,216,216,3,0,0,0,0,0,0,0,3,216,216,3,216,216,216,216,3,0,0,0,0,0,0,3,216,216,216,3,216,216,216,216,3,0,0,0,0,0,0,3,216,216,216,3,216,216,216,216,3,0,0,0,0,0,0,3,216,216,3,216,216,216,216,216,3,0,0,0,0,0,0,0,3,3,0,3,3,216,3,3,0,0,0,0,0,0,0,0,0,0,0,0,3,216,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,0,0]]

# test image of jayde's hoof
# Array for bitmap 1
# This array is stored as [width],[height],[R_list],[G_list],[B_list]
bitmap[1] = [[16],[20],[187,176,154,94,41,9,0,0,1,12,25,44,66,89,117,136,193,180,151,91,43,13,3,3,7,20,30,46,65,85,107,125,203,187,143,87,46,19,9,8,18,32,39,50,64,77,85,99,204,183,132,82,49,25,13,11,23,40,44,49,58,65,60,70,195,168,118,76,51,31,17,12,26,46,46,44,47,47,34,38,182,152,106,71,52,34,21,20,34,48,46,39,36,29,7,0,167,140,102,69,51,33,27,32,43,47,44,35,27,14,0,0,165,142,110,79,56,36,34,41,49,47,41,31,18,2,0,0,177,157,127,98,65,41,42,48,50,46,38,27,9,0,0,0,183,168,147,119,77,50,47,48,46,41,33,22,4,0,0,0,183,175,166,140,90,61,48,41,37,31,27,16,4,0,0,0,178,174,173,153,102,73,50,34,26,22,22,12,5,0,0,0,170,167,169,159,113,84,54,30,19,18,19,12,4,0,0,0,168,164,168,161,119,89,56,29,17,21,20,14,4,0,0,0,171,166,171,160,121,89,57,32,23,28,25,17,4,0,0,0,173,166,169,153,114,84,56,35,31,37,32,22,8,2,2,4,172,164,162,139,98,73,51,36,39,45,39,28,15,7,7,11,172,163,153,122,81,60,43,32,40,50,46,34,23,16,16,21,175,163,144,104,66,48,33,24,35,51,51,40,31,24,24,30,176,163,140,93,57,41,27,18,32,52,54,43,34,28,28,33],[0,0,5,16,13,13,28,40,45,50,49,54,69,90,104,104,0,1,7,17,14,14,29,41,49,58,59,69,92,115,126,135,0,3,11,18,17,16,30,43,58,71,78,94,125,150,160,177,6,12,20,22,20,19,32,50,72,94,112,138,164,179,194,209,16,23,29,28,23,23,37,60,90,120,149,183,201,203,226,233,25,33,35,31,25,26,45,76,112,150,189,214,224,224,241,241,34,43,40,33,27,29,57,95,135,181,227,236,236,242,242,236,45,55,54,45,36,41,75,115,158,207,246,247,244,246,237,227,58,68,71,61,49,57,95,136,180,229,251,249,250,239,226,216,74,82,85,76,64,78,119,159,202,243,251,248,247,230,216,207,91,96,97,91,79,101,145,184,223,249,246,245,236,222,208,200,103,108,106,103,96,125,168,209,238,248,240,237,225,213,202,195,114,120,115,116,113,147,189,232,246,240,231,227,217,206,198,194,140,143,137,133,131,162,202,240,244,228,220,216,209,199,195,194,174,172,165,154,149,173,208,235,233,214,208,205,202,192,191,194,206,199,189,172,165,182,210,227,219,199,195,194,193,187,189,192,233,223,208,187,180,190,210,220,204,185,182,183,183,183,188,189,248,239,224,201,192,200,217,222,200,176,169,172,174,179,187,187,253,249,237,212,203,211,228,233,207,174,159,161,165,175,186,186,255,254,243,218,208,217,234,238,211,173,154,156,161,172,185,186],[152,154,156,133,143,158,168,172,179,179,171,161,151,133,104,79,165,165,160,141,150,164,173,177,182,181,176,170,162,139,101,74,186,183,167,155,165,175,183,188,188,185,186,186,179,149,94,63,201,193,174,172,184,192,200,207,204,198,201,204,190,146,84,50,208,194,180,191,205,211,220,231,227,216,219,220,192,129,68,37,211,195,191,209,223,230,237,246,243,234,234,221,180,110,58,36,210,196,205,225,239,246,249,252,251,248,244,205,152,94,59,48,208,196,207,227,244,254,255,255,255,254,238,185,130,91,72,64,205,194,196,216,238,254,255,255,255,252,216,162,123,101,89,80,189,182,184,201,227,248,253,255,255,245,194,146,123,114,108,98,158,158,171,186,211,235,250,255,253,232,179,141,128,127,125,117,129,134,154,171,194,221,243,253,248,217,169,141,129,131,136,134,108,115,131,158,177,204,232,249,236,200,164,142,126,127,140,149,94,102,114,145,161,186,216,234,219,184,159,140,122,121,140,158,88,97,109,132,145,167,194,207,195,170,153,135,115,113,137,163,78,87,101,118,127,145,167,177,169,155,146,129,111,111,137,163,58,70,87,104,106,120,136,144,142,139,136,124,108,115,140,161,43,54,72,89,87,96,106,112,116,122,124,115,106,120,146,161,40,43,58,72,74,78,82,86,95,105,110,105,104,127,153,162,39,38,49,61,67,69,67,70,82,95,101,99,103,130,157,164]]

# 1 bit bitmap
# "load..." text
# Array for bitmap 2
# This array is stored as [width],[height],[pixel_list]
bitmap[2] = [[19],[5],[1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,0,1,1,1,0,1,1,0,0,0,0,1,0,0,0,0,0,0,1,0,1,0,1,0,0,0,1,0,0,1,1,0,0,0,0,0,0,1,0,1,0,1,0,1,1,1,0,1,0,1,0,0,0,0,0,0,1,0,1,1,1,0,1,1,1,0,1,1,1,0,1,0,1,0,1]]

# 1 bit bitmap
# jayde the goo deer text
# Array for bitmap 3
# This array is stored as [width],[height],[pixel_list]
bitmap[3] = [[81],[6],[1,1,1,0,1,1,0,0,1,1,0,1,0,1,0,0,0,1,1,0,0,0,0,1,1,1,1,0,0,0,1,0,1,1,0,1,0,0,0,0,1,1,1,1,1,0,0,1,1,1,0,0,1,1,1,0,0,1,1,1,1,1,0,0,0,1,1,0,0,0,0,1,0,0,0,0,1,0,0,0,1,1,1,1,0,1,0,1,1,0,1,0,1,0,1,0,1,1,0,1,0,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1,1,1,1,0,1,1,0,1,0,1,1,1,1,0,1,1,1,1,0,1,1,0,1,1,1,0,1,0,1,1,0,1,0,1,0,1,0,1,1,0,1,0,0,0,1,1,1,1,1,1,0,1,1,0,0,0,0,1,0,0,0,1,1,1,1,1,0,1,1,1,1,0,1,1,0,1,0,1,1,0,1,1,1,1,0,1,1,0,1,0,0,0,1,1,0,0,0,1,1,0,1,1,0,1,1,1,0,1,0,0,0,0,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,0,0,1,0,1,1,0,1,0,1,1,0,1,1,1,1,0,1,1,0,1,0,1,1,1,1,0,1,1,1,1,0,0,0,1,0,1,1,0,1,0,1,1,0,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,1,0,1,1,0,1,1,0,1,0,1,1,1,1,1,1,1,0,1,1,0,1,0,1,1,0,1,0,1,1,0,1,1,1,1,0,1,1,0,1,0,1,1,1,1,0,1,1,1,1,0,1,1,0,1,0,0,1,1,0,1,1,0,1,1,0,1,1,0,0,0,1,1,0,0,0,0,1,1,1,1,1,0,1,1,0,1,1,0,1,0,0,0,0,1,1,1,1,1,0,0,1,1,1,0,0,1,1,1,0,0,1,1,1,1,1,0,0,0,1,1,0,0,0,0,1,0,0,0,0,1,0,1,1,0]]

# colorful thing
# Array for bitmap 4
# This array is stored as [width],[height],[R_list],[G_list],[B_list]
bitmap[4] = [[12],[6],[255,255,184,87,0,0,0,0,54,185,255,255,255,255,184,87,0,0,0,0,54,184,255,255,255,255,185,86,0,0,0,1,54,184,255,255,255,255,185,87,0,0,0,0,54,185,255,255,255,255,184,87,0,0,0,0,54,185,255,255,255,255,185,87,0,0,0,0,54,185,255,255],[65,196,255,255,255,255,206,76,0,0,0,0,65,195,255,255,255,255,206,76,0,0,0,0,65,195,255,255,255,255,206,76,0,0,0,0,65,195,255,255,255,255,206,76,0,0,0,0,65,195,255,255,255,255,207,76,0,0,0,0,65,196,255,255,255,255,206,76,0,0,0,1],[0,0,0,0,43,174,255,255,255,255,195,65,0,0,0,0,44,174,255,255,255,255,195,65,0,0,0,0,43,174,255,255,255,255,195,65,0,0,0,0,44,174,255,255,255,255,195,65,0,0,0,0,44,174,255,255,255,255,196,65,0,0,0,0,43,174,255,255,255,255,196,65]]




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



# for this example you need one neopixel
# set screens_h = 1
# set screens_w = 1
for i in range(17,-17,-1):
    clear()
    bitmap_set1(i,2,bitmap[2],40,0,40,False)
    pixels_show()

# for this example you need one neopixel
# set screens_h = 1
# set screens_w = 1
bg_pos = -11
for i in range(100):
    # draw the background which is a tiled 12 pixel image
    for j in range(3):
        bitmap_set24(j*12+bg_pos,2,bitmap[4],1,1)
    bg_pos = bg_pos + 1
    if bg_pos == 0:
        bg_pos = -11
    pixels_show()



# fancy scrolling text example with utime.sleep used to make frame times consistent
# this uses all the CPU power the Pico can muster because of the image size.
# I need to make things like this render more efficienetly.

# for this example, you need two neopixels to see it all
# set screens_h = 1
# set screens_w = 2
for sadfjhasd in range(2):
    bg_pos = -11
    for i in range(32,-82,-1):
        TimeCounter = utime.ticks_ms()
        # draw the background which is a tiled 12 pixel image
        for j in range(4):
            bitmap_set24(j*12+math.floor(bg_pos),2,bitmap[4],1,1)
        bg_pos = bg_pos + .5
        if bg_pos == 0:
            bg_pos = -11
        # draw the text
        bitmap_set1(i,2,bitmap[3],0,0,0,True)
        # draw black pixels to prevent the background from being visible once the text passes
        if i > 0:
            for j in range(2,8,1):
                horiz(0,j,i,0,0,0)
        if i < 32-81:
            for j in range(2,8,1):
                horiz(i+81,j,32-i-81,0,0,0)
        
        utime.sleep_ms(150 - (utime.ticks_ms() - TimeCounter))
        pixels_show()


# for this example, you need two neopixels to see it all
# set screens_h = 2
# set screens_w = 1
TimeCounter = utime.ticks_ms()
for i in range(17,-17,-1):
    # this example scrolls the bitmap from right to left over a static background
    # bitmap_set defines which bitmap to use.
    # normally clear() would be needed, but with a background it isn't needed so it is commented out
    # clear()
    bitmap_set24(0,0,bitmap[1],2,.3)
    # draw the bitmap over the background with black pixels treated as transparent
    bitmap_set24(i,0,bitmap[0],1.7,.8,True)
    # draw a few random pixels over the bitmap
    for i in range(12):
        xy_set(math.ceil(screen_total_width*random.random()),math.ceil(screen_total_height*random.random()),(200,200,200))
    # display the result
    pixels_show()
print("Animation took " + str(utime.ticks_ms()-TimeCounter) + "ms")
utime.sleep_ms(100)




clear()
pixels_show()
