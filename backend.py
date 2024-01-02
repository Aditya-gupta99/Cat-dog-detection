from flask import Flask, request, jsonify
from fastapi import FastAPI, HTTPException
from ultralytics import YOLO
import cv2
import math
import requests
import time
import threading

app = Flask(__name__)

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
    dogCatDetection()


FCM_SERVER_KEY = "AAAAOqBZjiA:APA91bE5BugAfPwEZQKIamtS0hkC_zEr0Mg-ygmDofsDlBJXx6JDcj_-IlJZorIb1E7AcLqqenxwo386RudtlY5NFhR1a9XWFmu16kZ1xocK4-ULEhLYNRBECVoMop40kunDxBN7JVHz"
FCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send"
BACKEND_ENDPOINT = "http://localhost:5000/petSync/food"


def createFcmPayload(animal):
    return {
        "to": "/topic/eV4a10hMQcWKPNRkVjqjgC:APA91bHUiipbLh8pvoq2qN3ZzyQhL-ahn1A1NQGNszPj9XGuKyziee1bJ82V8UUwvqyZwyn_6NJLeJRPPqT45sJTXKpRPTrh8MB0TirRFqqYIqtN4bQ8-vz-TKywyFTJCGYNavhDAfvr",
        "data": {
            "title": "Feed alert",
            "message": animal+" has been feeded",
            "type":"food"
        },
    }


def sendNotification(animal):

    payload = createFcmPayload(animal)
    headers = {
        "Authorization": f"key={FCM_SERVER_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(FCM_ENDPOINT, json=payload, headers=headers)

    if response.status_code == 200:
        print("success")
    else:
        print(response.text)


def createFoodPayload(animal):
    return {
        "pet": animal,
        "timestamp": str(int(round(time.time() * 1000)))
    }


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




def dogCatDetection():
    
    # start webcam
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

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

    while True:

        current_time = time.time()
    
        success,img = cap.read()
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
                        sendNotification(classNames[cls])
                        saveFoodDetails(classNames[cls])
                        last_notification_time = current_time


        cv2.imshow('Webcam', img)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    app.run(host='192.168.104.21',port =8000, debug = True)