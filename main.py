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


# ==================================== screen stuff ===================================
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

# If you are using two NeoPixels on pins 5 and 6 to improve performance when using exactly 2 neopixels,
# set this to True. Otherwise, set it to False. This is an optimization specific to using two neopixels
# on those pins.
ImUsingPins6and5 = True

# I couldn't figure out how to check if the second thread is locked correctly so instead I'm using a global variable
global threadLocked
threadLocked = False

# Configure the number of WS2812 LEDs.
PIN_NUM = 6
brightness = 0.1


if screens_w == 2 and screens_h == 1 and gap_w == 0 and gap_h == 0:
    # use better optimized code if the layout is 2 screens wide with no gap.
    # this will let my 2x1 namebadge run a little faster without getting rid of
    # the code to use any number of neopixels.
    screen_total_width = 32
    screen_total_height = 10
    NUM_LEDS = 320
elif screens_w == 1 and screens_h == 1 and gap_w == 0 and gap_h == 0:
    # use better optimized code if the layout is 1 screen.
    screen_total_width = 16
    screen_total_height = 10
    NUM_LEDS = 160
else:
    # use slower code for any other configuration
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

if ImUsingPins6and5:
    sm1 = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(6))
    sm2 = rp2.StateMachine(1, ws2812, freq=8_000_000, sideset_base=Pin(5))
    sm1.active(1)
    sm2.active(1)
    ar = array.array("I", [0 for _ in range(320)])
    ar2 = array.array("I", [0 for _ in range(160)])
    ar3 = array.array("I", [0 for _ in range(160)])
else:
    # Create the StateMachine with the ws2812 program, outputting on pin
    # You can also increase the frequency to improve performance by 1-2ms
    sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(PIN_NUM))

    # Start the StateMachine, it will wait for data on its FIFO.
    sm.active(1)

    # Display a pattern on the LEDs via an array of LED RGB values.
    ar = array.array("I", [0 for _ in range(NUM_LEDS)])

####################### Functions ##############################
if ImUsingPins6and5:
    def pixels_show():
        while threadLocked:
            utime.sleep_ms(1)
        # This 2ms sleep prevents a race condition.
        utime.sleep_ms(2)
        ar2 = ar[:len(ar)//2]
        global ar3
        ar3 = ar[len(ar)//2:]
        _thread.start_new_thread(pixels_show_thread2,())
        dimmer_ar = array.array("I", [0 for _ in range(160)])
        # TimeCounter3 = utime.ticks_ms()
        for i,c in enumerate(ar2):
            r = int(((c >> 8) & 0xFF) * brightness)
            g = int(((c >> 16) & 0xFF) * brightness)
            b = int((c & 0xFF) * brightness)
            dimmer_ar[i] = (g<<16) + (r<<8) + b
        # print('1 took ' + str(utime.ticks_ms()-TimeCounter3) + ' ms')
        sm1.put(dimmer_ar, 8)
        while threadLocked:
            utime.sleep_ms(1)

    def pixels_show_thread2():
        global threadLocked
        threadLocked = True
        dimmer_ar = array.array("I", [0 for _ in range(160)])
        for i,c in enumerate(ar3):
            r = int(((c >> 8) & 0xFF) * brightness)
            g = int(((c >> 16) & 0xFF) * brightness)
            b = int((c & 0xFF) * brightness)
            dimmer_ar[i] = (g<<16) + (r<<8) + b
        sm2.put(dimmer_ar, 8)
        threadLocked = False
else:
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

def xy_set(x, y, colour):
    #check if a pixel is valid and set it if it is
    if valid_pixel(x,y):
        xy_set_valid(x, y, colour)

if screens_w == 2 and screens_h == 1 and gap_w == 0 and gap_h == 0:
    # use better optimized code if the layout is 2 screens wide with no gap.
    # this will let my 2x1 namebadge run a little faster without getting rid of
    # the code to use any number of neopixels.
    def xy_set_valid(x, y, colour):
        # Sets a pixel. This causes errors if you try to set a pixel that doesn't exist.
        # You should use xy_set() instead if you want to set a single pixel.
        if x > 15:
            screen_number = 1
            x = x - 16
        else:
            screen_number = 0
        #calculate which pixel to set on which Neopixel
        pos = (screen_number * 160) + x + y * 16
        pixels_set(pos, colour)

    def valid_pixel(x,y):
        # check if a pixel is valid
        if (x<0) or (y<0) or (x > 31) or (y > 9):
            valid_pixel = False
        else:
            valid_pixel = True
        return valid_pixel
elif screens_w == 1 and screens_h == 1 and gap_w == 0 and gap_h == 0:
    # use even better optimized code if using only one neopixel
    def xy_set_valid(x, y, colour):
        pos = x + y * 16
        pixels_set(pos, colour)
    def valid_pixel(x,y):
        if (x<0) or (y<0) or (x > 15) or (y > 9):
            valid_pixel = False
        else:
            valid_pixel = True
        return valid_pixel
else:
    # Use less optimized bode, but code that supports any layout you could possibly want.
    def xy_set_valid(x, y, colour):
        # +1 to x and y allows me to do pixel math in this function starting at 1 when the input x and y start at 0.
        # it's just easier for me to figure out the math that way.
        x = x + 1
        y = y + 1
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
    # it seems silly to do this but anything that can save an operation two in the valid pixel check will
    # help improve how many μs each frame takes to display
    global screen_total_width_minus_one
    screen_total_width_minus_one = screen_total_width - 1
    global screen_total_height_minus_one
    screen_total_height_minus_one = screen_total_height - 1
    def valid_pixel(x,y):
        valid_pixel = True
        # Check if the pixel you want to set is outside the size of the
        # screen to avoid wasting CPU cycles on pixels that you can't see
        if (x<0) or (y<0) or (x > screen_total_width - 1) or (y > screen_total_height - 1):
            valid_pixel = False
        # If you configured a gap between neopixels, check if the pixel is on a gap
        if valid_pixel:
            for i in missing_x:
                if x == i:
                    valid_pixel = False
            for i in missing_y:
                if y == i:
                    valid_pixel = False
        return valid_pixel

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
            if valid_pixel(i,y):
                xy_set_valid(i,y,cc)       # Top
            if valid_pixel(i,y+h-1):
                xy_set_valid(i,y+h-1,cc)   # Bottom
    else:
        cc = (r,g,b)
        for i in range(y+1,y+h):
            if valid_pixel(x,i):
                xy_set_valid(x,i,cc)       # Left
            if valid_pixel(x+w-1,i):
                xy_set_valid(x+w-1,i,cc)   # Right
    if threadNum:
        threadLocked = False

def vert(x,y,l,r,g,b):
    # Vertical line at (x,y) of length l coloured (r,g,b)
    cc = (r,g,b)
    for i in range(l):
        if valid_pixel(x,i):
            xy_set_valid(x,i,cc)

def horiz(x,y,l,r,g,b):
    # Horizontal line from (x,y) of length l coloured (r,g,b)
    cc = (r,g,b)
    for i in range(l):
        if valid_pixel(i+x,y):
            xy_set_valid(i+x,y,cc)

def bitmap_set_fast(x,y,w,h,r,g,b):
    # bitmap_set(x_coordinate, y_coordinate, bmp_width, bmp_height, bmp_red, bmp_green, bmp_blue)
    # set the pixels for a bitmap. No gama, brightness, or transparency modifications.
    # start at pixel zero
    PxNum = 0
    for i in range(h):
        for j in range(w):
            if valid_pixel(j+x,i+y):
                # use the heavily modified xy_set to set each pixel
                xy_set_valid(j+x,i+y,(r[PxNum],g[PxNum],b[PxNum]))
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
            if valid_pixel(j+x,i+y):
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
                    rr = math.pow(rr,ga) * 246 / math.pow(246,ga)
                    gg = math.pow(gg,ga) * 246 / math.pow(246,ga)
                    bb = math.pow(bb,ga) * 246 / math.pow(246,ga)
                    # undo the compression
                    rr = math.ceil(rr+9)
                    gg = math.ceil(gg+9)
                    bb = math.ceil(bb+9)
                    # use the heavily modified xy_set to set each pixel
                    xy_set_valid(j+x,i+y,(rr,gg,bb))
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
            if valid_pixel(j+x,i+y):
                if tr and p[PxNum] or not tr and j < 33:
                    xy_set_valid(j+x,i+y,(p[PxNum]*r,p[PxNum]*g,p[PxNum]*b))
            PxNum = PxNum + 1
    if threadNum:
        threadLocked = False

# ======================= BUTTON HANDLING ========================
button2 = Pin(2, Pin.IN, Pin.PULL_UP)
button3 = Pin(3, Pin.IN, Pin.PULL_UP)

button_presses = 0 # the count of times the button has been pressed
button_presses_last = 0
button_last_time = 0 # the last time we pressed the button

# This function gets called every time the button is pressed.
def button_pressed(pin):
    global button_presses, button_last_time
    button_new_time = utime.ticks_ms()
    
    # check the time for simple debouncing to prevent the button from triggering like 20 times when pressed
    if (button_new_time - button_last_time) > 200:
        # this should be pin.id but it does not work
        if '3' in str(pin):
            button_presses +=1
        elif '2' in str(pin):
            button_presses -=1
        button_last_time = button_new_time
        print(str(pin))

def buttonBreak():
    # simple function to make code more readable in the animations
    global button_presses, button_presses_last
    if not button_presses == button_presses_last:
        return True

button2.irq(trigger=Pin.IRQ_FALLING, handler = button_pressed)
button3.irq(trigger=Pin.IRQ_FALLING, handler = button_pressed)



# ========= Random information ========
micropython.mem_info()
TimeCounter = utime.ticks_ms()
print(utime.ticks_ms()-TimeCounter)

# ========= Define animation code here as functions ========
# animations that you want to be interrupted by buttons should have the one line
# if buttonBreak():break
# in the animation's loops to make sure the animation can be stopped in a timely manner

import BitmapData

def animation0():
    # blank animation so it doesn't light up super bright when plugged into usb for charging
    clear()
    while True:
        xy_set(1,1,(10,0,10))
        pixels_show()
        utime.sleep_ms(200)
        xy_set(1,1,(0,0,0))
        pixels_show()
        utime.sleep_ms(50)
        if buttonBreak():break

def animation1():
    # Displays the text "load..." which I created thinking there might be a perceptible loading time
    # but there wasn't so it's just one of the example animations.
    for i in range(17,-17,-1):
        clear()
        bitmap_set1(i,2,BitmapData.bitmap(2),40,0,40,False)
        pixels_show()
        # break the for loop if a buttnon is pressed so animation changes are more responsive
        if buttonBreak():break

def animation2():    
    # displays a rainbow gradient using a tiled bitmap
    bg_pos = -12
    for i in range(12):
        # draw the background which is a tiled 12 pixel image
        for j in range(3):
            bitmap_set24(j*12+bg_pos,2,BitmapData.bitmap(4),1.8,.3)
        bg_pos = bg_pos + 1
        if bg_pos == 0:
            bg_pos = -12
        pixels_show()
        if buttonBreak():break

def animation3():
    # fancy scrolling text example with utime.sleep used to make frame times consistent
    # "JAYDE THE GOO DEER" in rainbow
    for sadfjhasd in range(1):
        bg_pos = -11
        for i in range(32,-82,-1):
            FrameTime = utime.ticks_ms()
            # draw the background which is a tiled 12 pixel image
            for j in range(4):
                bitmap_set24(j*12+math.floor(bg_pos),2,BitmapData.bitmap(4),1,1)
            bg_pos = bg_pos + .5
            if bg_pos == 0:
                bg_pos = -11
            # draw the text.
            bitmap_set1(i,2,BitmapData.bitmap(3),0,0,0,True)
            # draw black pixels to prevent the background from being visible once the text passes
            if i > 0:
                for j in range(2,8,1):
                    horiz(0,j,i,0,0,0)
            if i < 32-81:
                for j in range(2,8,1):
                    horiz(i+81,j,32-i-81,0,0,0)
            utime.sleep_ms(100 - (utime.ticks_ms() - FrameTime))
            pixels_show()
            if buttonBreak():break

def animation4():
    # asparagus animation
    for i in range(34,-81,-1):
        FrameTime = utime.ticks_ms()
        clear()
        bitmap_set24(i,0,BitmapData.bitmap(5),3.1,.8)
        utime.sleep_ms(100 - (utime.ticks_ms() - FrameTime))
        pixels_show()
        if buttonBreak():break
    

# ======================= Runs animations on a loop ==================

# set how any animations to loop through with buttons
number_of_animations = 4
while True:
    if not button_presses_last == button_presses:
        # only clear the screen if the animation is changed, otherwise let the
        # animation handle its own screen clearing
        clear()
        button_presses_last = button_presses
    
    if button_presses < 0:
        button_presses = number_of_animations
    if button_presses > number_of_animations:
        button_presses = 0
        
    # play the selected animation
    TimeCounter = utime.ticks_ms()
    eval('animation' + str(button_presses) + '()')
    print('Animation ' + str(button_presses) + ' took ' + str(utime.ticks_ms()-TimeCounter) + 'ms')
    
    
    

clear()
pixels_show()
