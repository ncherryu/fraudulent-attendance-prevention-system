
import cv2
import numpy as np
import threading
from datetime import datetime
import socket
from time import sleep
import tkinter as tk
from tkinter import *
from tkinter import ttk, END
from tkinter import messagebox
from enum import Enum
from threading import Thread 
start = False

SocketChat_PortNumber = 24000

CameraCount = 100 # 카메라로 확인한 재실 인원
AttendanceCount = 0 # 출결시스템 내 출석 인원
sharpen_filter = np.array([[-1, -1, -1,], [-1, 9, -1], [-1, -1, -1]])

class LectureTime(Enum):
  START = 0
  END = 1

class ServerCompare:
  def __init__(self, mode):
    global CameraCount
    global hostAddr

    self.win = tk.Tk()
    self.win.title("ServerCompare")
    self.mode = mode
    
    # 호스트 이름과 IP 추출
    hostname = socket.gethostname()
    hostAddr = socket.gethostbyname(hostname)
    print("IP address = {}".format(hostAddr))
    self.myAddr = hostAddr
    self.createWidgets()
    
    # TCP 스레드 생성
    serv_thread = Thread(target=self.RecvCompare, daemon=True) 
    serv_thread.start()

    send_thread = Thread(target=self.SendCompare, daemon=True) 
    send_thread.start()
    print("send 스레드 생성")

  def init_time(self, servRecvMsg, time):
      time = servRecvMsg.split(':') # : 기준으로 문자열 자름. (ex, '4:30' -> ['4', '30'])
      time[1] = time[1].replace("\n", "")
      #print(time) # 디버그

      return time

    
  # TCP server
  def RecvCompare(self):
    global CameraCount
    global AttendanceCount
    global lecture_start_time # 강의 시작 시, 분
    global lecture_end_time # 강의 종료 시, 분
    global time_serv # 강의 시작, 종료 시간 수신 여부 표시
    global flag
    flag = False
    time_serv= 0
    lecture_start_time=(0, 0)
    lecture_end_time=(0, 0)
    count = 0
    TIME = False

    self.servSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    self.servSock.bind((hostAddr, SocketChat_PortNumber)) 
    self.scr_servDisplay.insert(tk.INSERT,"** 출결시스템과 연결하세요. \n" )
    self.servSock.listen(1)
    self.conn, self.cliAddr = self.servSock.accept() # cliAddr : (IPaddr, port_no)

    print("** 출결시스템과 연결되었습니다. ({})\n".format(self.cliAddr))
    self.scr_servDisplay.insert(tk.INSERT,"** 출결시스템과 연결되었습니다.\n" )
    self.peerAddr_entry.insert(END, self.cliAddr[0])

    while True:
      # ================= 수신 ======================
      servRecvMsg = self.conn.recv(512).decode()

      now = datetime.now()
      nowHour = now.hour
      nowMinute = now.minute

      if (TIME == False):
        if (count == 0): # 시작 시간 
          lecture_start_time = self.init_time(servRecvMsg, lecture_start_time)
          count+=1
      
        else:
          lecture_end_time = self.init_time(servRecvMsg, lecture_end_time)
          count+=1
          TIME = True
        
      else:
        # 강의가 시작했거나, 아직 끝나지 않았는지 검사
        if (self.isLectureTime(nowHour, nowMinute, int(lecture_start_time[0]), int(lecture_start_time[1]), LectureTime.START) == True) and\
          (self.isLectureTime(nowHour, nowMinute, int(lecture_end_time[0]), int(lecture_end_time[1]), LectureTime.END) == True):
          
          if not servRecvMsg: # 수신한 메시지 없음
            break

          flag = True
        # 수신한 메시지 있음
          self.scr_servDisplay.delete("1.0", "end")
          self.scr_servDisplay.insert(tk.INSERT,"출석: " + servRecvMsg + "명  (" + str(now.time()) + ")" + "\n")
          AttendanceCount = int(servRecvMsg)
          self.scr_servDisplay.insert(tk.INSERT,"재실 인원: " + str(CameraCount) + "명  (" + str(now.time()) + ")" + "\n")

        else: # 강의 시간이 아님
          self.scr_servDisplay.delete("1.0", "end")
          self.scr_servDisplay.insert(tk.INSERT,"** 강의 시간이 아닙니다.\n" )
          st = self.isLectureTime(nowHour, nowMinute, int(lecture_start_time[0]), int(lecture_start_time[1]), LectureTime.START) 
          ed = self.isLectureTime(nowHour, nowMinute, int(lecture_end_time[0]), int(lecture_end_time[1]), LectureTime.END)
      
    self.conn.close()

  def isLectureTime(self, nowHour, nowMinute, hour, minute, lectureTime): # 강의가 시작했는지, 마친 시간인지 검사하는 함수
    if (lectureTime == LectureTime.START): # 강의가 시작했는지 검사하길 요구
      if (hour < nowHour): # 지금 시간이 강의시작 시간을 지났음 -> 당연히 강의 시작
        return True
      elif (hour == nowHour): # 지금 시간이 강의시작 시간과 같음 -> 분까지 검사해야 함
        if (minute <= nowMinute): # 지금 분이 강의시작 분을 지났음
          return True
        else: # 아직 강의시작 분을 넘지 않음
          return False
      else:
        return False # 강의 시작 시간이 아님
        
    else: # 강의가 끝났는지 검사하길 요구
      if (hour < nowHour): # 지금 시간이 강의종료 시간을 지났음 -> 당연히 강의 끝
        return False
      elif (hour == nowHour): # 지금 시간이 강의종료 시간과 같음 -> 분까지 검사해야 함
        if (minute <= nowMinute): # 지금 시간이 강의종료 시간을 넘었음
          return False # 수업 끝
        else:
          return True
      else: 
        return True
  

  def SendCompare(self):
    while True:
      if (flag == False):
        sleep(1)

      else:
        if (self.countCompare() < 0):
          print(self.countCompare())
          messagebox.showinfo("부정 출석 방지 시스템","부정 출석이 감지되었습니다!") #메시지 박스를 띄운다.
          sleep(60)


  def _quit(self):
    self.win.quit()
    self.win.destroy()
    exit()

  def countCompare(self): # 재실 인원과 출결시스템 인원을 비교하는 함수
    global CameraCount
    global AttendanceCount

    cc = CameraCount
    ac = AttendanceCount
    #a = AttendanceCount - CameraCount # 출결인원과 재실인원 차이가 
    #b = AttendanceCount * 0.1 # 오차 범위 
    a = ac - cc
    b = ac * 0.1
    gap = b - a # 오차 범위보다 크면 음수 오차범위보다 작으면 양수

    return gap

  def serv_send(self):
    msgToCli = "출결 초기화\n"
    self.scr_servDisplay.insert(tk.INSERT,"<< " + msgToCli)
    self.conn.send(bytes(msgToCli.encode()))

  def show_img(self):
      global ResultImg

      tkImg = ResultImg
      cv2.imshow("Image", tkImg)
      #cv2.waitKey(3000)
      #cv2.destroyAllWindows()
      

  def createWidgets(self):
    frame = ttk.LabelFrame(self.win, text="부정 출석 방지 시스템 서버")
    frame.grid(column=0, row=0, padx=8, pady=4)
    
    frame_addr_connect = ttk.LabelFrame(frame, text="")
    frame_addr_connect.grid(column=0, row=0, padx=40, pady=20, columnspan=2)

    myAddr_label = ttk.Label(frame_addr_connect, text="내 IP")
    myAddr_label.grid(column=0, row=0, sticky='W') #
    peerAddr_label = ttk.Label(frame_addr_connect, text="출결시스템 IP")
    peerAddr_label.grid(column=1, row=0, sticky='W') #

    self.myAddr = tk.StringVar()
    self.myAddr_entry = ttk.Entry(frame_addr_connect, width=15,textvariable=self.myAddr)
    self.myAddr_entry.insert(END, hostAddr)
    self.myAddr_entry.grid(column=0, row=1, sticky='W')

    self.peerAddr = tk.StringVar()
    self.peerAddr_entry = ttk.Entry(frame_addr_connect, width=15, textvariable="")
    self.peerAddr_entry.grid(column=1, row=1, sticky='W')

    scrol_w, scrol_h = 40, 5
    servDisplay_label = ttk.Label(frame, text="전송 내역")
    servDisplay_label.grid(column=0, row=1 )
    self.scr_servDisplay = tk.Text(frame, width=scrol_w, height=scrol_h, wrap=tk.WORD)
    self.scr_servDisplay.grid(column=0, row=2, sticky='E') #, columnspan=3

    # Add Buttons (cli_send, serv_send)
    serv_send_button = ttk.Button(frame, text="초기화", command=self.serv_send) 
    serv_send_button.grid(column=0, row=5, sticky='E')

    # Image show Button
    img_button = ttk.Button(frame, text = "이미지 보기", command=self.show_img) ##
    img_button.grid(column=0, row=5, sticky='W')






def receive_all(sock, count):
        buffer = b''
        while count:
            new_buffer = sock.recv(count)
            if not new_buffer:
                return None
            buffer += new_buffer
            count = count - len(new_buffer)
        return buffer

def person_detection(img_name, type):

    # Yolo Load
    net = cv2.dnn.readNet("D:\Python_project\yolo\yolov3.weights", "D:\Python_project\yolo\yolov3.cfg")
    classes = []
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

    # Get Image
    img = img_name
    #img = cv2.imread(img_name)
    if type == "filter":
        img = cv2.GaussianBlur(img, (0, 0), 2.3)
        img = cv2.filter2D(img, -1, sharpen_filter)
    img = cv2.resize(img, None, fx=1, fy=1)
    height, width, channels = img.shape

    # Detecting objects
    blob = cv2.dnn.blobFromImage(img, 0.00392, (608, 608), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    # Calc
    class_ids = []
    confidences = []
    boxes = []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if class_id==0 and confidence > 0.5:
                # Object detected
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                # 좌표
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)


    # Remove Noise
    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

    # Detection area define
    x_max = 1920
    y_max = 1080
    x_start = 1400
    y_start = y_max - 1080
    x_end = 1920
    y_end = y_max - 600
    a = (y_end - y_start)/(x_end - x_start) # 기울기
    b = y_start - a * x_start # y 절편
    cv2.line(img, (x_start, 1080), (x_end, 600), (0, 0, 255), 3)
    font = cv2.FONT_HERSHEY_PLAIN
    cv2.putText(img, "Exception Area", (1620, 980), font, 2, (0, 0, 255), 2, cv2.LINE_AA)

    #Print Screen
    total_people = 0
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            if (a * (x+w) + b - (y_max - (y + h)) > 0) or (a * x + b - (y_max - (y + h)) > 0): # 제외 영역
                continue
            cv2.rectangle(img, (x, y), (x + w, y + h), (255,0,0), 1)
            total_people += 1

    #img = cv2.resize(img, None, fx=0.4, fy=0.4)

    return total_people, img

def person_cognition():
    host_ip = ''
    port_num = 9000
    camera_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('카메라 소켓 생성 완료')
    camera_server_socket.bind((host_ip, port_num))
    print('카메라 소켓 바인드 완료')
    camera_server_socket.listen(2)
    print('카메라 소켓 대기 중')
    camera_socket, addr_socket = camera_server_socket.accept()
    print('카메라 연결 완료')
    while(True):
        global CameraCount
        global ResultImg

        max_person = 0
        person_num = 0
        for i in range(2):
            # 이미지 수신
            receive_string = receive_all(camera_socket, 16)
            img2str = receive_all(camera_socket, int(receive_string))
            img_array = np.fromstring(img2str, dtype='uint8')
            recv_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            print("이미지 수신 완료")

            # 객체 검출
            person_num1, img1 = person_detection(recv_img, "none")
            person_num2, img2 = person_detection(recv_img, "filter")
            if person_num1 > person_num2:
                person_num = person_num1
                img = img1
            else:
                person_num = person_num2
                img = img2

            if max_person < person_num:
                max_person = person_num
                max_img = img
            if max_person == 0:
                max_img = recv_img

            print("i = {0}, person_none = {1}, person_filter = {2},  person_num = {3}, max_person = {4}".format(i, person_num1, person_num2, person_num, max_person))
            #sleep(30000)
            camera_socket.sendall('request image'.encode()) # 이미지 요청

        # 최종 인원수와 이미지 결정
        CameraCount = max_person
        ResultImg = max_img
        print("result_person = ", CameraCount)


###################### main ######################
t = threading.Thread(target=person_cognition)
t.start()
sockChat = ServerCompare("ServerCompare")
sockChat.win.mainloop()
