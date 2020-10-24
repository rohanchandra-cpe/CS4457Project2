#!/usr/bin/env python3

import socket
import sys
import os
import select
import queue

from file_reader import FileReader

class Jewel:
    def __init__(self, port, file_path, file_reader):
        self.file_path = file_path
        self.file_reader = file_reader

        port = int(os.environ.get('PORT', 80))

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(0)
        s.bind(('localhost', port))
        s.listen(5)

        inputs = [s]
        outputs = []
        messages_queue = {}

        while inputs:
            readable, writeable, exceptional = select.select(inputs, outputs, inputs)

            for soc in readable:
                if soc is s:
                    (client, address) = soc.accept()
                    print('[CONN] Connection from ' + str(address[0]) + " on port " + str(address[1]))
                    client.setblocking(0)
                    inputs.append(client)
                    messages_queue[client] = queue.Queue()
                else:
                    data = soc.recv(1024)
                    if not data:
                        if soc in outputs:
                            outputs.remove(soc)
                        inputs.remove(soc)
                        soc.close()
                        del messages_queue[soc]
                        continue
                    to_return_bytes = data.split(b' ')[1]
                    print(data.split(b' '))
                    cookies = data.split(b' ')[-1]
                    to_return = to_return_bytes.replace(b'/', b'\\').decode('utf-8')
                    file_path = file_path + to_return

                    response = ()
                    mime_type = ''

                    (head, tail) = os.path.split(file_path)
                    period_character = tail.find('.')
                    file_type = tail[period_character + 1:]

                    if os.path.isdir(file_path):
                        mime_type ="dir"
                    elif file_type == 'png':
                        mime_type = b'image/png'
                    elif file_type == 'jpg':
                        mime_type = b'image/jpg'
                    elif file_type == 'gif':
                        mime_type = b'image/gif'
                    elif file_type == 'css':
                        mime_type = b'text/css'
                    elif file_type == 'html':
                        mime_type = b'text/html'

                    if data[0:3] == b'GET':
                        if not os.path.exists(file_path):
                            print('[ERRO] [' + str(address[0]) + ':' + str(address[1]) + '] GET request returned error 404')
                            response = (
                                b'HTTP/1.1 404 Not Found' +
                                b'\r\n'
                            )
                            messages_queue[soc].put(response)
                            file_path = file_path.replace(to_return, "")
                            if soc not in outputs:
                                outputs.append(soc)
                        elif mime_type == 'dir':
                            print('[REQU] [' + str(address[0]) + ':' + str(address[1]) + '] GET request for ' + to_return)
                            response = (
                                'HTTP/1.1 200 OK\r\n',
                                'Content-Type: text/html\r\n',
                                '\r\n',
                                """
                                <html>
                                <body>
                                <h1>""" + to_return_bytes.decode() + """</h1>
                                </body>
                                </html>
                                """
                            )
                            response = "".join(response)
                            file_path = file_path.replace(to_return, "")
                            mime_type = ''
                            messages_queue[soc].put(str.encode(response))
                            if soc not in outputs:
                                outputs.append(soc)
                        else:
                            print('[REQU] [' + str(address[0]) + ':' + str(address[1]) + '] GET request for ' + to_return)
                            response_body = file_reader.get(file_path, cookies)
                            content_length = file_reader.head(file_path, cookies)
                            response = (
                                b'HTTP/1.1 200 OK\r\n' +
                                b'Content-Type: ' + mime_type + b'\r\n' +
                                b'Content-Length: '+ str(content_length).encode() + b'\r\n' +
                                b'\r\n' +
                                response_body
                            )
                            print(response_body)
                            file_path = file_path.replace(to_return, "")
                            mime_type = ''
                            messages_queue[soc].put(response)
                            if soc not in outputs:
                                outputs.append(soc)
                    elif data[0:4] == b'HEAD':
                        if not os.path.exists(file_path):
                            print('[ERRO] [' + str(address[0]) + ':' + str(address[1]) + '] HEAD request returned error 404')
                            response = (
                                    b'HTTP/1.1 404 Not Found' +
                                    b'\r\n'
                            )
                            file_path = file_path.replace(to_return, "")
                            messages_queue[soc].put(response)
                            if soc not in outputs:
                                outputs.append(soc)
                        elif mime_type == 'dir':
                            print('[REQU] [' + str(address[0]) + ':' + str(address[1]) + '] HEAD request for ' + to_return)
                            response = (
                                'HTTP/1.1 200 OK\r\n',
                                'Content-Type: text/html\r\n',
                                '\r\n'
                            )
                            response = "".join(response)
                            file_path = file_path.replace(to_return, "")
                            mime_type = ''
                            messages_queue[soc].put(str.encode(response))
                            if soc not in outputs:
                                outputs.append(soc)
                        else:
                            print('[REQU] [' + str(address[0]) + ':' + str(address[1]) + '] HEAD request for ' + to_return)
                            content_length = file_reader.head(file_path, cookies)
                            response = (
                                    b'HTTP/1.1 200 OK\r\n' +
                                    b'Content-Type: ' + mime_type + b'\r\n' +
                                    b'Content-Length: ' + str(content_length).encode() + b'\r\n' +
                                    b'\r\n'
                            )
                            file_path = file_path.replace(to_return, "")
                            mime_type = ''
                            messages_queue[soc].put(response)
                            if soc not in outputs:
                                outputs.append(soc)
                    else:
                        print("501: Method Unimplemented")
                        response = (
                            b'HTTP/1.1 501 Method Unimplemented\r\n'
                            b'\r\n'
                        )
                        file_path = file_path.replace(to_return, "")
                        mime_type = ''
                        messages_queue[soc].put(response)
                        if soc not in outputs:
                            outputs.append(soc)
            for soc in writeable:
                try:
                    next_msg = messages_queue[soc].get_nowait()
                except queue.Empty:
                    outputs.remove(soc)
                else:
                    soc.sendall(next_msg)
            for soc in exceptional:
                inputs.remove(soc)
                if soc in outputs:
                    outputs.remove(soc)
                soc.close()
                del messages_queue[soc]


if __name__ == "__main__":
    port = int(sys.argv[1])
    file_path = sys.argv[2]

    if not os.path.exists(file_path):
        print("Invalid root directory. Please try again.")
        exit(1)

    FR = FileReader()

    J = Jewel(port, file_path, FR)
