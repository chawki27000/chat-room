import select
import socket
import sys
import _pickle
import struct


# Some utilities
def send(channel, *args):
    """ Function to serialize data (with dumps()) and determines her size (with struct) and send it """
    buffer = _pickle.dumps(args)  # serialize data
    value = socket.htonl(len(buffer))
    size = struct.pack("L", value)  # evaluate the size of data

    # send it
    channel.send(size)
    channel.send(buffer)


def receive(channel):
    """ Function to receive data and return it"""
    size = struct.calcsize("L")  # recalculate the size of data
    size = channel.recv(size)

    try:
        size = socket.ntohl(struct.unpack("L", size)[0])
    except struct.error as e:
        return ''

    buf = ""

    # loop for receiving all chunk of data
    while len(buf) < size:
        buf = channel.recv(size - len(buf))
    return _pickle.loads(buf)[0]


class ChatClient():
    def __init__(self, name, port, host):
        self.name = name
        self.connected = False
        self.host = host
        self.port = int(port)

        # Initial prompt
        self.prompt = '[' + '@'.join((name, socket.gethostname().split('.')[0])) + ']> '

        # Connect to server at port
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, self.port))
            print("Now connected to chat server@ port %d" % self.port)
            self.connected = True

            # Send my name...
            send(self.sock, 'NAME: ' + self.name)
            data = receive(self.sock)

            # Contains client address, set it
            addr = data.split('CLIENT: ')[1]
            self.prompt = '[' + '@'.join((self.name, addr)) + ']> '

        except socket.error as e:
            print("Failed to connect to chat server @ port %d" % self.port)
            sys.exit(1)

    def run(self):
        """ Chat client main loop """
        while self.connected:
            try:
                sys.stdout.write(self.prompt)
                sys.stdout.flush()

                # Wait for input from stdin and socket
                readable, writeable, exceptional = select.select([0, self.sock], [], [])

                for sock in readable:  # only readable socket
                    if sock == 0:  # sending data statement
                        data = sys.stdin.readline().strip()
                        if data: send(self.sock, data)  # Sending data

                    elif sock == self.sock:  # receiving data statement
                        data = receive(self.sock)
                        if not data:
                            print('Client shutting down.')
                            self.connected = False
                            break
                        else:
                            sys.stdout.write(data + '\n')
                            sys.stdout.flush()

            except KeyboardInterrupt:
                print(" Client interrupted. """)
                self.sock.close()
                break


################################################################################################

if __name__ == '__main__':
    # presentation
    print("\t\t# # # #   Chat Room V0.1 - Client   # # # #\n")

    # Information reading
    host = input("Please entre the server IP : ")
    port = input("Please entre the server port : ")
    name = input("Please entre your name : ")

    # Lunch
    client = ChatClient(name=name, port=port, host=host)
    client.run()
