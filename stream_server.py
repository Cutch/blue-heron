import socketserver
import threading
import io
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import json
from http import server
import os
import shutil

server_thread = None
output = None
class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            # rgb = cv2.cvtColor(yuv420, cv2.COLOR_YUV420p2RGB)
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(self.path)
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = open('./index.html', mode="r", encoding="utf-8").read().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/data.json':
            found_images = os.listdir('./found/')
            found_images_json={}
            for file in found_images:
                (date, tag) = file.replace('.jpg', '').split('__')
                if date in found_images_json: 
                    found_images_json[date][tag] = '/found/'+file
                else:
                    found_images_json[date]={(tag): '/found/'+file}
            content = json.dumps({
                'found': found_images_json
            }).encode("utf-8")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif 'favicon' in self.path:
            self.send_response(200)
            self.send_header('Content-type', 'image/png' if '.png' in self.path else 'image/x-icon')
            self.send_header('Cache-Control', 'public, max-age=604800')
            self.end_headers()
            with open('.'+self.path, 'rb') as content:
                shutil.copyfileobj(content, self.wfile)
        elif '/found/' in self.path:
            self.send_response(200)
            self.send_header('Content-type', 'image/jpeg')
            self.send_header('Cache-Control', 'public, max-age=604800')
            self.end_headers()
            with open('./found/' + self.path.replace('/found/', ''), 'rb') as content:
                shutil.copyfileobj(content, self.wfile)
        elif '/log.txt' in self.path:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            with open('./log.txt', 'rb') as content:
                shutil.copyfileobj(content, self.wfile)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                print(e)
                pass
                # logging.warning(
                #     'Removed streaming client %s: %s',
                #     self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
    
def start_recording(picam):
    global output
    output = StreamingOutput()
    picam.start_recording(MJPEGEncoder(), FileOutput(output))

def start_server():
    address = ('', 8000)
    streamServer = StreamingServer(address, StreamingHandler)
    # streamServer.serve_forever()
    server_thread = threading.Thread(target=streamServer.serve_forever, daemon=True)
    server_thread.start()

def stop_recording(picam):
    # server_thread.stop()
    picam.stop_recording()
