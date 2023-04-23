# sudo apt-get install libatlas-base-dev
# wget https://www.piwheels.org/simple/numpy/numpy-1.24.2-cp39-cp39-linux_armv6l.whl#sha256=bd9c94c75a4e3a2f58329c8095b94ccd9468fb0ec84633dc4eef29df29f6f3e5
# pip install numpy-1.24.2-cp39-cp39-linux_armv6l.whl
# pip install picamera2
# sudo apt-get install python3-picamera2 python3-pidng python3-simplejpeg

from stream_server import start_server, start_recording, stop_recording
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

import shutil
import os
import sys
import numpy as np
import time
from picamera2 import Picamera2
import tflite_runtime.interpreter as tflite
from glob import glob
from PIL import Image
if not os.path.exists("./found"):
    os.mkdir("./found")
if not os.path.exists("./tmp"):
    os.mkdir("./tmp")

# Logger
logger = logging.getLogger("Rotating Log")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("log.txt", maxBytes=2000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

def load_labels(path): # Read the labels from the text file as a Python list.
  with open(path, 'r') as f:
    return {k: v for k, v in [line.strip().split(",") for i, line in enumerate(f.readlines()) if i > 0]}

labels = load_labels("./aiy_birds_V1_labelmap.csv")

# Load the TFLite model and allocate tensors.
interpreter = tflite.Interpreter(model_path="./lite-model_aiy_vision_classifier_birds_V1_3.tflite")

# Get input and output tensors.
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

picam = Picamera2()
# WIDTH=4608
# HEIGHT=2592
WIDTH=2304
HEIGHT=1296
# config = picam.create_video_configuration({"size": (WIDTH, HEIGHT), "format": "BGR888"}, {"size": (640, 480)}, encode="lores")
# picam.configure(config)
picam.configure(picam.create_video_configuration(main={"size": (WIDTH, HEIGHT)}, lores={"size": (640, 480), "format": "YUV420"}, encode="lores"))
start_recording(picam)
start_server()

IMAGE_RES = 224                                                                 # input dimensions required by the CNN model
def predict_image(img_path):
    interpreter.allocate_tensors()
    img = Image.open(img_path).resize((IMAGE_RES, IMAGE_RES))
    input_data = np.expand_dims(img, axis=0)

    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    # The function `get_tensor()` returns a copy of the tensor data.
    # Use `tensor()` in order to get a pointer to the tensor.
    output_data = interpreter.get_tensor(output_details[0]['index'])
    return str(np.argmax(np.squeeze(output_data)))

previously_found_heron = False
def save_image(file):
    request = picam.capture_request()
    request.save("main", file)
    request.release()
    # picam.capture_file(file)
try:
    while True:
        logger.debug('Running')
        time.sleep(5)
        save_image("./full-image.jpg")
        full_image = Image.open("./full-image.jpg")
        
    #    HEIGHT_PARTS=4
    #    WIDTH_PARTS=8
    #    padding = ((HEIGHT/HEIGHT_PARTS)-(WIDTH/WIDTH_PARTS)) / 2
    #    for y in range(0, HEIGHT_PARTS):
    #        for x in range(0, WIDTH_PARTS):
    #            full_image.crop((
    #                    x*(WIDTH/WIDTH_PARTS)-(0 if x == 0 else padding)-(padding if x == WIDTH_PARTS-1 else 0),
    #                    y*(HEIGHT/HEIGHT_PARTS),
    #                    (x+1)*(WIDTH/WIDTH_PARTS)+(padding if x == 0 else 0)+(0 if x == WIDTH_PARTS-1 else padding),
    #                    (y+1)*(HEIGHT/HEIGHT_PARTS))
    #                ) \
    #                .resize((IMAGE_RES, IMAGE_RES)) \
    #                .save("./tmp/crop8x_"+str(x)+"_"+str(y)+".jpg")
    #    
    #    HEIGHT_PARTS=2
    #    WIDTH_PARTS=4
    #    padding = ((HEIGHT/HEIGHT_PARTS)-(WIDTH/WIDTH_PARTS)) / 2
    #    for y in range(0, HEIGHT_PARTS):
    #        for x in range(0, WIDTH_PARTS):
    #            full_image.crop((
    #                    x*(WIDTH/WIDTH_PARTS)-(0 if x == 0 else padding)-(padding if x == WIDTH_PARTS-1 else 0),
    #                    y*(HEIGHT/HEIGHT_PARTS),
    #                    (x+1)*(WIDTH/WIDTH_PARTS)+(padding if x == 0 else 0)+(0 if x == WIDTH_PARTS-1 else padding),
    #                    (y+1)*(HEIGHT/HEIGHT_PARTS))
    #                ) \
    #                .resize((IMAGE_RES, IMAGE_RES)) \
    #                .save("./tmp/crop4x_"+str(x)+"_"+str(y)+".jpg")

        HEIGHT_PARTS=1
        WIDTH_PARTS=2
        padding = ((HEIGHT/HEIGHT_PARTS)-(WIDTH/WIDTH_PARTS)) / 2
        for y in range(0, HEIGHT_PARTS):
            for x in range(0, WIDTH_PARTS):
                full_image.crop((
                        x*(WIDTH/WIDTH_PARTS)-(0 if x == 0 else padding)-(padding if x == WIDTH_PARTS-1 else 0),
                        y*(HEIGHT/HEIGHT_PARTS),
                        (x+1)*(WIDTH/WIDTH_PARTS)+(padding if x == 0 else 0)+(0 if x == WIDTH_PARTS-1 else padding),
                        (y+1)*(HEIGHT/HEIGHT_PARTS))
                    ) \
                    .resize((IMAGE_RES, IMAGE_RES)) \
                    .save("./tmp/crop2x_"+str(x)+"_"+str(y)+".jpg")
        
        img_files = np.array(glob("./tmp/*"))   # collect all images to be analyzed
        found_heron = False
        for index, file in enumerate(img_files):
            prediction = predict_image(file)
            if prediction in labels:
                if "Ardea" in labels[prediction]:
                    found_heron = True
                    previously_found_heron = True
                    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    
                    shutil.copy("./full-image.jpg", './found/'+date_str+'__full.jpg')
                    shutil.copy(file, './found/'+date_str+'__crop.jpg')
                    logger.info("Found Heron")

                    files = os.listdir('./found/')
                    files.sort(reverse=True)
                    if len(files) > 20:
                        for i in range(20, len(files)):
                            logger.debug("Remove "+'./found/'+files[i])
                            os.remove('./found/'+files[i])
        if found_heron:
            # Make noise
            logger.info("Noise Made")
            pass

        if previously_found_heron and not found_heron:
            previously_found_heron = False
            logger.info("Heron Left")
finally:
    stop_recording(picam)
    picam.close()