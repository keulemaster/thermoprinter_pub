import os
import random
import string
import sys
import threading
import time
import requests
import numpy as np

import evdev
#from datetime import datetime as dt
import time

import qrcode
import cv2
from PIL import Image
#from PIL import ImageDraw
#from PIL import ImageFont

#sudo apt install python3-dotenv
from dotenv import load_dotenv

from gpiozero import Button, LED, Buzzer
from picamera2 import Picamera2, Preview
#from libcamera import Transform #need for hflip

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

## SOME FINALs
EVENT_VAL_MUTE = 32769
EVENT_VAL_NR5 = 32776
EVENT_VAL_JUMP = 32782
WAIT_TIME_BETWEEN_EVENTS = 10

PRINT_IMAGE_SCALEFACTOR = 85

BUZZER_SLEEP_TIME = 0.05

GPIO_NR_PHOTO_BUTTON = 14
GPIO_NR_LED = 17
GPIO_NR_BUZZER = 12

NR_RANDOM_LETTERS = int(os.environ.get('NR_RANDOM_LETTERS'))
CUPS_PRINTER_NAME = 'RaspiThermo'
WEBSERVER_URL = os.environ.get('WEBSERVER_URL')
PIC_URL_ON_WEBSERVER = f'https://{WEBSERVER_URL}/thermocamera_images/'
UPLOAD_URL_TO_WEBSERVICE = os.environ.get('UPLOAD_URL_TO_WEBSERVICE')
PIC_PATH_QRCODE = '/tmp/qrcode.png'
PIC_PATH_URL = '/home/pi/picamera/url2.png'
PATH_FOR_IMG_SAVE = os.environ.get('PATH_FOR_IMG_SAVE')

def get_ir_device():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if (device.name == "gpio_ir_recv"):
            #print("Using device", device.path, "n")
            return device
    print("No IR device found!")
    return None

def generate_unique_string_for_filename():
    mpool = string.ascii_letters + string.digits
    uniqstr = ''.join([random.choice(mpool) for _ in range(NR_RANDOM_LETTERS)])
    return 'pic_'+uniqstr+'.jpg'

def upload_taken_pic(pic_name):
    url = UPLOAD_URL_TO_WEBSERVICE
    r = requests.post(url, files={'image': open(pic_name, 'rb')})
    if r != 200:
        ## do something if upload doesnt work, ie no internet
        # TODO
        pass

## gibt text auf dem preview aus
def create_overlay_text(mtext, showtimeinsec=2):
    colour = (0, 255, 0, 255)
    origin = (30, 150)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1
    thickness = 3
    overlay = np.zeros((320, 240, 4), dtype=np.uint8)
    cv2.putText(overlay, mtext, origin, font, scale, colour, thickness)
    picam2.set_overlay(overlay)
    time.sleep(showtimeinsec)
    picam2.set_overlay(None)

def show_message_on_screen(msg, showtime):
    t = threading.Thread(target=create_overlay_text, args=(msg, showtime))
    t.start()

def stick_qr_code2_image(picname_with_path):
    picname = picname_with_path.split('/')[-1]
    
    qr_file_name = PIC_PATH_QRCODE
    def create_qrcode_for_image(picname):
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        url = f'{PIC_URL_ON_WEBSERVER}{picname}'
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_file_name)

    create_qrcode_for_image(picname)
    images = [Image.open(x) for x in [qr_file_name, picname_with_path]]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height), color='white')
    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset,0))
        x_offset += im.size[0]
    img_url = Image.open(PIC_PATH_URL)
    new_im.paste(img_url, (0, 333))

    print_file_name = f'/tmp/{picname}'
    new_im.save(print_file_name)
    return print_file_name

def blink_fast():
    for _ in range(4):
        led.on()
        time.sleep(0.05)
        led.off()
        time.sleep(0.05)

def piep():
    buzz.on()
    time.sleep(BUZZER_SLEEP_TIME)
    buzz.off()
    time.sleep(BUZZER_SLEEP_TIME)
    buzz.on()
    time.sleep(BUZZER_SLEEP_TIME)
    buzz.off()

## hardware definitions
## ----------------------------------------------------------------------------
take_pic_button = Button(GPIO_NR_PHOTO_BUTTON)
led = LED(GPIO_NR_LED) #Led for showing photo is taken
buzz = Buzzer(GPIO_NR_BUZZER) # Buzzer
ir_dev = get_ir_device()
## ----------------------------------------------------------------------------

## camera definitions and start preview
## ----------------------------------------------------------------------------
picam2 = Picamera2()

#https://www.tomshardware.com/how-to/use-picamera2-take-photos-with-raspberry-pi
camera_still_config = picam2.create_still_configuration(
   main={"size": (1920, 1080)}, lores={"size": (640, 480)}, display="main")
#picam2.configure(camera_still_config)

camera_preview_config = picam2.create_preview_configuration()
picam2.configure(camera_preview_config)

## if we need hflip, depends how the TFT screen is built in inside the case
#picam2.start_preview(Preview.DRM, width=320, height=240, transform=Transform(hflip=1))
picam2.start_preview(Preview.DRM, width=320, height=240)
picam2.start()
## ----------------------------------------------------------------------------

def worker_image_creation_and_printing():
    img_file = generate_unique_string_for_filename()
    img_file_with_path = PATH_FOR_IMG_SAVE + os.sep + img_file

    ## maybe there is a better solution for capturing with: 
    ## picam2.switch_mode_and_capture_array(capture_config)
    ## but not tested

    ## to shoot a bigger picture, i have to add the still config
    picam2.stop()
    picam2.configure(camera_still_config)
    picam2.start()

    picam2.capture_file(img_file_with_path)

    ## after taking the phote i habe to move back to the preview config
    picam2.stop()
    picam2.configure(camera_preview_config)
    picam2.start()

    ## blink led
    t00 = threading.Thread(target=blink_fast)
    t00.start()

    ## start buzzer
    t01 = threading.Thread(target=piep)
    t01.start()

    ##now show text that pic was taken
    #showtext = 'PIC taken!'
    #t0 = threading.Thread(target=create_overlay_text, args=(showtext,))
    #t0.start()
    show_message_on_screen('PIC taken!', 3)

    ## now upload the shooted pic
    t1 = threading.Thread(target=upload_taken_pic, args=(img_file_with_path,))
    t1.start()

    ## make better picture for printing
    ## so nocht nicht probiert, erst zum schluss vllt testen
    # os.system(f"convert {img_file} -rotate 90 -resize 384 -dither FloydSteinberg -remap pattern:gray50 {output_grey}")
    ## schaut mit floyd steinberg schlechter aus
    # os.system(f"convert {img_file} -dither FloydSteinberg -remap pattern:gray50 {output_grey}")

    ## now create qrcode and stick to picture
    print_file_name = stick_qr_code2_image(img_file_with_path)

    ## now print picture on printer

    ## -o fit-to-page ist default
    ## bisher fehler unten schneidets ein wenig ab..
    #os.system(f'lp -o fit-to-page {print_file_name} -d RaspiThermo')
    #os.system(f'lp {print_file_name} -d RaspiThermo')
    ## die -o fill ist ganz eine schlechte option da kommt was riesiges raus

    ## so bekommt man fast alles drauf
    if not printer_muted:
        os.system(f'lp -o scaling={PRINT_IMAGE_SCALEFACTOR} {print_file_name} -d {CUPS_PRINTER_NAME}')
        #print(f'wuerde jetzt bild: {print_file_name} drucken')

#mute printer switcher
printer_muted = False

## needed because event fires more then one time
event_time = 0
allow_next_event_input = True

while(True):
    event = ir_dev.read_one()

    if (event_time+WAIT_TIME_BETWEEN_EVENTS) < time.time():
        allow_next_event_input = True

    if take_pic_button.is_pressed:
        #print('...bin im button teil')
        worker_image_creation_and_printing()
    
    ## 32776 is 5 on the ir remote
    if event and event.value == EVENT_VAL_NR5 and allow_next_event_input:
        #print('...bin im IR teil')
        event_time = time.time()
        #print('...verbiete drucken')
        allow_next_event_input = False
        #print('time.time()', time.time()) 
        #print('event.timestamp()', event.timestamp())
        worker_image_creation_and_printing()

    if event and event.value == EVENT_VAL_MUTE and allow_next_event_input:
        event_time = time.time()
        allow_next_event_input = False
        if printer_muted:
            printer_muted = False
            #print('printer UNmuted')
            show_message_on_screen('print UNmuted', 3)
        else:
            printer_muted = True
            #print('printer muted')
            show_message_on_screen('print muted', 3)

    if event and event.value == EVENT_VAL_JUMP and allow_next_event_input:
        show_message_on_screen('...EXIT', 2)
        event_time = time.time()
        allow_next_event_input = False
        #picam2.stop()
        sys.exit()
