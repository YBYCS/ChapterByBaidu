import websocket
import threading
import uuid
import json
import logging
import sys
import const
import pyaudio
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
global subtitle
logger = logging.getLogger()
class WebSocketThread(QThread):
    connected = pyqtSignal()
    message_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    closed = pyqtSignal()
    def __init__(self, uri):
        super().__init__()
        self.uri = uri

    def run(self):
        self.ws = websocket.WebSocketApp(self.uri,
                               on_open=self.on_open,
                               on_message=self.on_message,
                               on_error=self.on_error,
                               on_close=self.on_close)
        self.ws.run_forever()
    def send_start_params(self,ws):
        """
        开始参数帧
        :param websocket.WebSocket ws:
        :return:
        """
        req = {
            "type": "START",
            "data": {
                "appid": const.APPID,  # 网页上的appid
                "appkey": const.APPKEY,  # 网页上的appid对应的appkey
                "dev_pid": const.DEV_PID,  # 识别模型
                "cuid": "yourself_defined_user_id",  # 随便填不影响使用。机器的mac或者其它唯一id，百度计算UV用。
                "sample": 16000,  # 固定参数
                "format": "pcm"  # 固定参数
            }
        }
        body = json.dumps(req)
        ws.send(body, websocket.ABNF.OPCODE_TEXT)
        logger.info("send START frame with params:" + body)
    def send_audio(ws):
        """
        发送二进制音频数据，注意每个帧之间需要有间隔时间
        :param  websocket.WebSocket ws:
        :return:
        """
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
        while True:
            audio_data = stream.read(8000)
            ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)  
    def send_finish(ws):
        """
        发送结束帧
        :param websocket.WebSocket ws:
        :return:
        """
        req = {
            "type": "FINISH"
        }
        body = json.dumps(req)
        ws.send(body, websocket.ABNF.OPCODE_TEXT)
        logger.info("send FINISH frame") 
    def send_cancel(ws):
        """
        发送取消帧
        :param websocket.WebSocket ws:
        :return:
        """
        req = {
            "type": "CANCEL"
        }
        body = json.dumps(req)
        ws.send(body, websocket.ABNF.OPCODE_TEXT)
        logger.info("send Cancel frame")
    def on_open(self,ws):
        def run(*args):
            """
            发送数据帧
            :param args:
            :return:
            """
            req = {
                "type": "START",
                "data": {
                    "appid": const.APPID,  # 网页上的appid
                    "appkey": const.APPKEY,  # 网页上的appid对应的appkey
                    "dev_pid": const.DEV_PID,  # 识别模型
                    "cuid": "yourself_defined_user_id",  # 随便填不影响使用。机器的mac或者其它唯一id，百度计算UV用。
                    "sample": 16000,  # 固定参数
                    "format": "pcm"  # 固定参数
                }
            }
            body = json.dumps(req)
            ws.send(body, websocket.ABNF.OPCODE_TEXT)
            logger.info("send START frame with params:" + body)
            """
            发送二进制音频数据，注意每个帧之间需要有间隔时间
            :param  websocket.WebSocket ws:
            :return:
            """
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000, input_device_index=1)
            while True:
                audio_data = stream.read(8000)
                ws.send(audio_data, websocket.ABNF.OPCODE_BINARY)     
            req = {
                "type": "FINISH"
            }
            body = json.dumps(req)
            ws.send(body, websocket.ABNF.OPCODE_TEXT)
            logger.info("send FINISH frame")
            logger.debug("thread terminating")

        threading.Thread(target=run).start()
        self.connected.emit()

    def on_message(self,ws, message):
        json_data = json.loads(message)
        if 'result' in json_data:
            result = json_data["result"]
            print(result)
            subtitle.update_text(result)
        self.message_received.emit(message)

    def on_error(self,ws, error):
        logger.error("error: " + str(error))
        self.error_occurred.emit(error)

    def on_close(self,ws):
        self.closed.emit()

class Subtitle(QtWidgets.QWidget):
    def __init__(self, text):
        super().__init__()

        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        self.label = QtWidgets.QLabel(text, self)
        self.label.setStyleSheet("QLabel { background-color : black; color : white; }")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        font = self.label.font()
        font.setPointSize(25)
        self.label.setFont(font)
        uri = const.URI + "?sn=" + str(uuid.uuid1())
        self.websocket_thread = WebSocketThread(uri)
        self.websocket_thread.connected.connect(self.on_connected)
        self.websocket_thread.start()
    def update_text(self, text):
        text_list = [text[i:i+15] for i in range(0, len(text), 15)]
        text = '\n'.join(text_list)
        lines = text.splitlines()
        if len(lines) > 3:
            text = '\n'.join(lines[-3:])
        self.label.setText(text)
        self.label.adjustSize()
        
        self.adjustSize()        
    def on_connected(self):
        print("WebSocket connection")
    def on_message_received(self):
        print("WebSocket message received")
    def on_error_occurred(self):
        print("WebSocket error")

if __name__ == "__main__":
    logging.basicConfig(format='[%(asctime)-15s] [%(funcName)s()][%(levelname)s] %(message)s')
    logger.setLevel(logging.DEBUG)  # 调整为logging.INFO，日志会少一点
    logger.info("begin")
    app = QtWidgets.QApplication(sys.argv)
    subtitle = Subtitle("等待语言中")
    subtitle.show()
    sys.exit(app.exec_())