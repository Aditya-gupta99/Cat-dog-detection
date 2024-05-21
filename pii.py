from flask import Flask, request, jsonify,json
from fastapi import FastAPI, HTTPException
from ultralytics import YOLO
import cv2
import math
import requests
import time
import threading
import firebase_admin
from firebase_admin import credentials
from google.oauth2 import service_account
import google.auth.transport.requests
from picamera2 import Picamera2
import RPi.GPIO as GPIO
import time

app = Flask(__name__)

# FCM notification for Video Screen to On
def sendFcmForCallScreenNotification():
    
    title = "PetCall"
    body = "Sound"

    fcm_endpoint = "https://fcm.googleapis.com/v1/projects/petsync-dd38d/messages:send"

    try:
        access_token = _get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "message": {
                "token": "cE6Ip-gERHG95yKpnTySP8:APA91bHhh4H3sQzv-PfkG8GLlNHgmGe8w09I0qC874K5MnF2-ECD7Oa3zIMCjgf4OxyFNrDkUFKgCDG-agDIqPjLVW4DyKrMXAyjmWzLjc-Z4aqOGeo0s_R4jHHMKpQAbvU4gIkdmllY",
                "data": {
                    "title": title,
                    "body": body
                }
            }
        }

        response = requests.post(fcm_endpoint, headers=headers, json=payload)

        if response.ok:
            print("Notification sent successfully")
            ultrasonicSensor()
        else:
            print(f"Failed to send notification. Response code: {response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")


@app.post("/petSync/raspberry/onOff")
def onOff():
    try:
        if request.method == 'POST':
            data = request.data.decode('utf-8')
            threading.Thread(target=onMachine, args=(data,), daemon=True).start()
            return jsonify({'Status': 'On'})
        else:
            return "Method Not Allowed", 405
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch onOff:{str(e)}")
    

def onMachine(data):
    sendFcmForCallScreenNotification()


BACKEND_ENDPOINT = "http://192.168.1.5:5000/petSync/food"


# Payload for FCM Feed details user
def createPetFoodPayload(animal):
    return {
        "message": {
                "token": "eV4a10hMQcWKPNRkVjqjgC:APA91bHUiipbLh8pvoq2qN3ZzyQhL-ahn1A1NQGNszPj9XGuKyziee1bJ82V8UUwvqyZwyn_6NJLeJRPPqT45sJTXKpRPTrh8MB0TirRFqqYIqtN4bQ8-vz-TKywyFTJCGYNavhDAfvr",
                "notification": {
                    "title": "Feed Alert",
                    "body": animal+" has been feeded"
                }
            }
    }

# FCM notification to Pet Owner for Feed details
def sendPetFeedNotification(animal):
    fcm_endpoint = "https://fcm.googleapis.com/v1/projects/petsync-dd38d/messages:send"

    try:
        access_token = _get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(fcm_endpoint, headers=headers, json=createPetFoodPayload(animal))

        if response.ok:
            print("Notification sent successfully")
        else:
            print(f"Failed to send notification. Response code: {response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")


# Payload data for Save Pet Feed Spring boot
def createFoodPayload(animal):
    return {
        "pet": animal,
        "timestamp": str(int(round(time.time() * 1000)))
    }


# Save Pet Feed Details into Spring boot
def saveFoodDetails(animal):
    foodPayload = createFoodPayload(animal)
    headers = {
        "Content-Type": "application/json"
    }
    try :
        response = requests.post(BACKEND_ENDPOINT,json=foodPayload,headers=headers)
        if(response.status_code == 200):
            print("Success")
        else:
            print(response.text)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save food data:{str(e)}")



# PetDetection Model Yolo
def dogCatDetection():

    # model
    model = YOLO("yolo-Weights/yolov8n.pt")

    # object classes
    classNames = ["person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat",
              "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
              "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
              "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat",
              "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
              "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
              "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", "pottedplant", "bed",
              "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote", "keyboard", "cell phone",
              "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
              "teddy bear", "hair drier", "toothbrush"
              ]

    cooldown_duration = 60
    last_notification_time = 0
    
    # Camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
    picam2.start()
    
    checkClose = True

    while checkClose:

        current_time = time.time()
    
        img = picam2.capture_array("main")
        
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        
        results = model(img, stream=True)

        # coordinates
        for r in results:
            boxes = r.boxes

            for box in boxes:
            # bounding box
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2) # convert to int values

                # put box in cam
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

                # confidence
                confidence = math.ceil((box.conf[0]*100))/100
                print("Confidence --->",confidence)

                # class name
                cls = int(box.cls[0])
                print("Class name -->", classNames[cls])

                # object details
                org = [x1, y1]
                font = cv2.FONT_HERSHEY_SIMPLEX
                fontScale = 1
                color = (255, 0, 0)
                thickness = 2

                if cls in [15, 16]:
                    cv2.putText(img, classNames[cls], org, font, fontScale, color, thickness)
                    if current_time - last_notification_time >= cooldown_duration:
                        sendPetFeedNotification(classNames[cls])
                        saveFoodDetails(classNames[cls])
                        sendFcmForVideoCallScreenNotification()
                        if(cls == 15):
                            foodDespenserCat()
                        if(cls == 16):
                            foodDespenserDog()
                        last_notification_time = current_time
                        checkClose = False


        cv2.imshow('Webcam', img)
        if cv2.waitKey(1) == ord('q'):
            break

    picam2.close()
    cv2.destroyAllWindows()



# FCM notification for Video Screen to On
def sendFcmForVideoCallScreenNotification():
    
    title = "Notification Title"
    body = "Notification Body"

    fcm_endpoint = "https://fcm.googleapis.com/v1/projects/petsync-dd38d/messages:send"

    try:
        access_token = _get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "message": {
                "token": "cE6Ip-gERHG95yKpnTySP8:APA91bHhh4H3sQzv-PfkG8GLlNHgmGe8w09I0qC874K5MnF2-ECD7Oa3zIMCjgf4OxyFNrDkUFKgCDG-agDIqPjLVW4DyKrMXAyjmWzLjc-Z4aqOGeo0s_R4jHHMKpQAbvU4gIkdmllY",
                "data": {
                    "title": title,
                    "body": body
                }
            }
        }

        response = requests.post(fcm_endpoint, headers=headers, json=payload)

        if response.ok:
            print("Notification sent successfully")
        else:
            print(f"Failed to send notification. Response code: {response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")


# Get Access Token for FCM
def _get_access_token():
    
    SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

    credentials = service_account.Credentials.from_service_account_file('serviceAccountKey.json', scopes=SCOPES)
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token
    
    
def foodDespenserCat():
    print("cattttttt is detected")
    control = [5,5.5,6,6.5,7,7.5,8,8.5,9,9.5,10]

    servo = 22

    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(servo,GPIO.OUT)
# in servo motor,
# 1ms pulse for 0 degree (LEFT)
# 1.5ms pulse for 90 degree (MIDDLE)
# 2ms pulse for 180 degree (RIGHT)

# so for 50hz, one frequency is 20ms
# duty cycle for 0 degree = (1/20)*100 = 5%
# duty cycle for 90 degree = (1.5/20)*100 = 7.5%
# duty cycle for 180 degree = (2/20)*100 = 10%

    p=GPIO.PWM(servo,50)# 50hz frequency

    p.start(2.5)# starting duty cycle ( it set the servo to 0 degree )
    try:
        for x in range(11):
            p.ChangeDutyCycle(control[x])
            time.sleep(0.03)
            print(x)
           
        for x in range(9,0,-1):
            p.ChangeDutyCycle(control[x])
            time.sleep(0.03)
            print(x)
        
    except KeyboardInterrupt:
        GPIO.cleanup()
        

def foodDespenserDog():
    print("Dogggg is detected")
    control = [5,5.5,6,6.5,7,7.5,8,8.5,9,9.5,10]

    servo = 18

    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(servo,GPIO.OUT)
# in servo motor,
# 1ms pulse for 0 degree (LEFT)
# 1.5ms pulse for 90 degree (MIDDLE)
# 2ms pulse for 180 degree (RIGHT)

# so for 50hz, one frequency is 20ms
# duty cycle for 0 degree = (1/20)*100 = 5%
# duty cycle for 90 degree = (1.5/20)*100 = 7.5%
# duty cycle for 180 degree = (2/20)*100 = 10%

    p=GPIO.PWM(servo,50)# 50hz frequency

    p.start(2.5)# starting duty cycle ( it set the servo to 0 degree )
    try:
        for x in range(11):
            p.ChangeDutyCycle(control[x])
            time.sleep(0.03)
            print(x)
           
        for x in range(9,0,-1):
            p.ChangeDutyCycle(control[x])
            time.sleep(0.03)
            print(x)
        
    except KeyboardInterrupt:
        GPIO.cleanup()

def ultrasonicSensor():
    #GPIO Mode (BOARD / BCM)
    GPIO.setmode(GPIO.BCM)
 
    #set GPIO Pins
    GPIO_TRIGGER = 4
    GPIO_ECHO = 17
 
    #set GPIO direction (IN / OUT)
    GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
    GPIO.setup(GPIO_ECHO, GPIO.IN)

    def distance():
        # set Trigger to HIGH
        GPIO.output(GPIO_TRIGGER, True)
 
        # set Trigger after 0.01ms to LOW
        time.sleep(0.000001)
        GPIO.output(GPIO_TRIGGER, False)
 
        StartTime = time.time()
        StopTime = time.time()
    
        # save StartTime
        while GPIO.input(GPIO_ECHO) == 0:
            StartTime = time.time()
 
        # save time of arrival
        while GPIO.input(GPIO_ECHO) == 1:
            StopTime = time.time()


 
        # time difference between start and arrival
        TimeElapsed = StopTime - StartTime
        # multiply with the sonic speed (34300 cm/s)
        # and divide by 2, because there and back
        distance = (TimeElapsed * 34600) / 2
        return distance
    
    try:
        while True:
            dist = distance()
            print ("Measured Distance = %.1f cm" % dist)
            if(dist<=30):
                GPIO.cleanup()
                dogCatDetection()
                break
            time.sleep(1)
        GPIO.cleanup()
 
        # Reset by pressing CTRL + C
    except KeyboardInterrupt:
        print("Measurement stopped by User")
        GPIO.cleanup()


# Main function
if __name__ == '__main__':
    #ultrasonicSensor()
    app.run(host='192.168.1.6',port =8000, debug = True)