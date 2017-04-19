import select
import socket
import sys
import signal
import _pickle
import struct

CHAT_SERVER_NAME = 'server'


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


################################################################################################
class ChatServer():
    def sighandler(self, signum, frame):
        """ Clean up client outputs"""
        # Close the server
        print('Shutting down server...')

        # Close existing client sockets
        for output in self.outputs:
            output.close()
        self.server.close()

    def __init__(self, host, port, backlog=5):
        self.clients = 0
        self.clientmap = {}
        self.outputs = []  # list output sockets
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket initialization

        # Enable re-using socket address
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, int(port)))
        print('Server listening to port: %s ...' % port)
        self.server.listen(backlog)

        # Catch keyboard interrupts
        signal.signal(signal.SIGINT, self.sighandler)

    def get_client_name(self, client):
        """ Return the name of the client """
        info = self.clientmap[client]
        host, name = info[0][0], info[1]
        return '@'.join((name, host))

    def run(self):
        inputs = [self.server, sys.stdin]
        self.outputs = []
        running = True

        while running:  # Main execution
            try:
                # returning 3 types of socket (only readable sockets are going to be processed)
                readable, writeable, exceptional = select.select(inputs, self.outputs, [])
            except select.error as e:
                break

            for sock in readable:  # processing the readable sockets
                if sock == self.server:  # SERVER SOCKET
                    # handle the server socket
                    client, address = self.server.accept()
                    print("Chat server: got connection %d from %s" % (client.fileno(), address))

                    # Read the login name
                    cname = receive(client).split('NAME: ')[1]

                    # Compute client name and send back
                    self.clients += 1
                    send(client, 'CLIENT: ' + str(address[0]))
                    inputs.append(client)
                    self.clientmap[client] = (address, cname)

                    # Send joining information to other clients
                    msg = "\n(Connected: New client (%d) from %s)" % (self.clients, self.get_client_name(client))

                    # loop for broadcasting the new clients to others
                    for output in self.outputs:
                        send(output, msg)

                    self.outputs.append(client)  # add client to outputs array

                elif sock == sys.stdin:
                    # handle standard input
                    junk = sys.stdin.readline()
                    running = False

                else:  # RECEPTION
                    # handle all other sockets
                    try:
                        data = receive(sock)
                        if data:
                            # Send as new client's message...
                            msg = '\n#[' + self.get_client_name(sock) \
                                  + ']>>' + data

                            # Send data to all except ourself
                            for output in self.outputs:
                                if output != sock:
                                    send(output, msg)

                        else:
                            print("Chat server: %d hung up" % sock.fileno())
                            self.clients -= 1
                            sock.close()
                            inputs.remove(sock)
                            self.outputs.remove(sock)

                            # Sending client leaving info to others
                            msg = "\n(Now hung up: Client from %s)" % self.get_client_name(sock)

                            for output in self.outputs:
                                send(output, msg)

                    except socket.error as e:
                        # Remove
                        inputs.remove(sock)

                        self.outputs.remove(sock)

        self.server.close()


################################################################################################

if __name__ == '__main__':
    # presentation
    print("\t\t# # # #   Chat Room V0.1 - Server   # # # #\n")

    # Information reading
    host = input("Please entre the server IP : ")
    port = input("Please entre the server port : ")

    # Lunch
    server = ChatServer(port=port, host=host)
    server.run()
