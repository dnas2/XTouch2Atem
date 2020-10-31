import socket
import threading
import struct
import time

class Source:
    def __init__(self,name):
        self.isPreview = False
        self.isOnAir = False

def dumpHex (buffer):
    s = ''
    for c in buffer:
        s += hex(c) + ' '
    print(s)


def dumpAscii (buffer):
    s = ''
    for c in buffer:
        if (ord(c)>=0x20)and(ord(c)<=0x7F):
            s+=c
        else:
            s+='.'
    print(s)



class Atem:

    # size of header data
    SIZE_OF_HEADER = 0x0c

    # packet types
    CMD_NOCOMMAND   = 0x00
    CMD_ACKREQUEST  = 0x01
    CMD_HELLOPACKET = 0x02
    CMD_RESEND      = 0x04
    CMD_UNDEFINED   = 0x08
    CMD_ACK         = 0x10

    # initializes the class
    def __init__(self, address):
    
        self.isConnected = "Atem not connected"
        self.atemState = [Source("HDMI1"), Source("HDMI2"), Source("HDMI3"), Source("HDMI4"), Source("SDI5"), Source("SDI6"),  Source("SDI7"),  Source("SDI8"), Source("MP1"), Source("MP2"), None, None, Source("Bars")]
        self.hasChangeForXTouch = True
        self.initialSet = True
        self.packetCounter = 0
        self.isInitialized = False
        self.currentUid = 0x1338
        self.address = (address, 9910)
        self.currentLive = -1
        self.currentPreview = -1
        self.udpClient = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.udpClient.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udpClient.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #self.udpClient.setblocking(0)
        self.udpClient.bind(('0.0.0.0', 9910))
        self.connectToSwitcher()
        self.isConnected = "Atem connected"
        time.sleep(1)
        #self.waitForPacket()
        udpWorker = threading.Thread(target = self.waitForPacket)
        udpWorker.start()

    def connectToSwitcher(self):
        datagram = self.createCommandHeader(self.CMD_HELLOPACKET, 8, self.currentUid, 0x0)
        datagram += struct.pack('!I', 0x01000000)
        datagram += struct.pack('!I', 0x00)
        self.sendDatagram(datagram)

    def updateUid(self,newuid):
        self.currentUid = newuid

    def waitForPacket(self):
        while True:
            time.sleep(0.01)
            self.udp_listener()

    def udp_listener(self):
        #print("Started listener")
        try:
            d = self.udpClient.recvfrom(2048)
        except socket.error:
            return False
        datagram, server = d
        #print('received datagram')
        header = self.parseCommandHeader(datagram)
        if header:
            self.updateUid(header['uid'])
            if header['bitmask'] & self.CMD_HELLOPACKET :
                print('not initialized, received HELLOPACKET, sending ACK packet')
                self.isInitialized = False
                ackDatagram = self.createCommandHeader (self.CMD_ACK, 0, header['uid'], 0x0)
                self.sendDatagram (ackDatagram)
            elif (header['bitmask'] & self.CMD_ACKREQUEST) and\
                (self.isInitialized or len(datagram) == self.SIZE_OF_HEADER):
                #print('initialized, received ACKREQUEST, sending ACK packet')
                #print("Sending ACK for packageId %d" % header['packageId'])
                ackDatagram = self.createCommandHeader(self.CMD_ACK, 0, header['uid'], header['packageId'])
                self.sendDatagram(ackDatagram)
                if not self.isInitialized:
                    self.isInitialized = True
            
            if len(datagram) > self.SIZE_OF_HEADER + 2 and not (header['bitmask'] & self.CMD_HELLOPACKET):
                self.parsePayload(datagram)
            return True
        
    
    def createCommandHeader (self, bitmask, payloadSize, uid, ackId):
        buffer = b''
        packageId = 0

        if not (bitmask & (self.CMD_HELLOPACKET | self.CMD_ACK)):
            self.packetCounter += 1
            packageId = self.packetCounter
    
        val = bitmask << 11
        val |= (payloadSize + self.SIZE_OF_HEADER)
        buffer += struct.pack('!H',val)
        buffer += struct.pack('!H',uid)
        buffer += struct.pack('!H',ackId)
        buffer += struct.pack('!I',0)
        buffer += struct.pack('!H',packageId)
        return buffer
    
    # parses the packet header
    def parseCommandHeader (self, datagram):
        header = {}

        if len(datagram)>=self.SIZE_OF_HEADER :
            header['bitmask'] = struct.unpack('B',datagram[0:1])[0] >> 3
            header['size'] = struct.unpack('!H',datagram[0:2])[0] & 0x07FF
            header['uid'] = struct.unpack('!H',datagram[2:4])[0]
            header['ackId'] = struct.unpack('!H',datagram[4:6])[0]
            header['packageId']=struct.unpack('!H',datagram[10:12])[0]
            print(header)
            return header
        return False

    def parsePayload(self, datagram):
        #print('parsing payload')
        # eat up header
        datagram = datagram[self.SIZE_OF_HEADER:]
        # handle data
        while len(datagram) > 0 :
            size = struct.unpack('!H',datagram[0:2])[0]
            packet = datagram[0:size]
            datagram = datagram[size:]

            # skip size and 2 unknown bytes
            packet = packet[4:]
            ptype = packet[:4]
            payload = packet[4:]

            # find the approporiate function in the class
            method = 'recv' + ptype.decode("utf-8")
            if method in dir(self) :
                func = getattr(self, method)
                if callable(func) :
                    print('> calling '+method)
                    func(payload)
                else:
                    print('problem, member '+method+' not callable')
            #else:
                #print('unknown type '+ptype.decode("utf-8"))
                #dumpAscii(payload)

        #sys.exit()

    def sendCommand (self, command, payload) :
        #print('sending command')
        size = len(command) + len(payload) + 4
        dg = self.createCommandHeader(self.CMD_ACKREQUEST, size, self.currentUid, 0)
        dg += struct.pack('!H', size)
        dg += b'\x00\x00'
        dg += command
        dg += payload
        self.sendDatagram(dg)

    # sends a datagram to the switcher
    def sendDatagram (self, datagram) :
        #print('sending packet')
        dumpHex(datagram)
        self.udpClient.sendto(datagram, self.address)

    def byteAddrToSource(self, byteAddr):
        if byteAddr == b'\x00\x01': return 0
        elif byteAddr == b'\x00\x02': return 1
        elif byteAddr == b'\x00\x03': return 2
        elif byteAddr == b'\x00\x04': return 3
        elif byteAddr == b'\x00\x05': return 4
        elif byteAddr == b'\x00\x06': return 5
        elif byteAddr == b'\x00\x07': return 6
        elif byteAddr == b'\x00\x08': return 7
        elif byteAddr == b'\x0b\xc2': return 8
        elif byteAddr == b'\x0b\xcc': return 9
        elif byteAddr == b'\x03\xe8': return 12
        return None
        
    def sourceToByteAddr(self,source):
        if source == 0: return b'\x00\x01'
        elif source == 1: return b'\x00\x02'
        elif source == 2: return b'\x00\x03'
        elif source == 3: return b'\x00\x04'
        elif source == 4: return b'\x00\x05'
        elif source == 5: return  b'\x00\x06'
        elif source == 6: return  b'\x00\x07'
        elif source == 7: return  b'\x00\x08'   
        elif source == 8: return  b'\x0b\xc2'
        elif source == 9: return  b'\x0b\xcc'
        elif source == 12: return  b'\x03\xe8'
        return None
        

    def setPreview(self, source):
        self.initialSet = False
        self.resetPreviewStatus()
        self.atemState[source].isPreview = True
        previewBytes = self.sourceToByteAddr(source)
        if previewBytes is None:
            return
        previewCmd = b'\x43\x50\x76\x49\x00\x75'
        self.sendCommand(previewCmd,previewBytes)
        self.currentPreview = source
        self.hasChangeForXTouch = True
    
    def recvPrgI(self, data):
        if self.initialSet == True:
            meIndex = data[0]
            source = self.byteAddrToSource(data[2:4])
            self.atemState[source].isOnAir = True
            self.currentLive = source
        

    def recvPrvI(self, data):
        if self.initialSet == True:
            meIndex = data[0]
            source = self.byteAddrToSource(data[2:4])
            self.atemState[source].isPreview = True
            self.currentPreview = source

    def resetPreviewStatus(self):
        for i in range(len(self.atemState)):
            currentInput = self.atemState[i]
            if currentInput is not None:
                currentInput.isPreview = False
    
    def resetProgramStatus(self):
        for i in range(len(self.atemState)):
            currentInput = self.atemState[i]
            if currentInput is not None:
                currentInput.isOnAir = False

    def doCut(self):
        cutCmd = b'\x44\x43\x75\x74\x00'
        cutPayload = b'\x56\x96\x23'
        self.sendCommand(cutCmd, cutPayload)
        self.resetPreviewStatus()
        self.resetProgramStatus()
        self.atemState[self.currentPreview].isOnAir = True
        self.atemState[self.currentLive].isPreview = True
        oldPreview = self.currentPreview
        self.currentPreview = self.currentLive
        self.currentLive = oldPreview
        self.hasChangeForXTouch = True

    def doAuto(self):
        cutCmd = b'\x44\x41\x75\x74\x00'
        cutPayload = b'\x57\x96\x23'
        self.sendCommand(cutCmd, cutPayload)
        oldPreview = self.currentPreview
        oldLive = self.currentLive
        self.resetPreviewStatus()
        self.resetProgramStatus()
        self.atemState[oldPreview].isOnAir = True
        self.atemState[oldLive].isPreview = True
        self.currentLive = oldPreview
        self.currentPreview = oldLive
        self.hasChangeForXTouch = True
    
    def doFTB(self):
        cutCmd = b'\x46\x74\x62\x41\x00'
        cutPayload = b'\x62\x96\x23'
        self.sendCommand(cutCmd, cutPayload)

# if __name__ == '__main__':
#     a = Atem("192.168.0.155")
#     print("Connecting to Atem")
#     a.connectToSwitcher()
#     def tallyWatch(atem):
#         print("Tally changed")
#         pprint(atem.state['tally'])
#         pprint(atem.state['tally_by_index'])
#     def inputWatch(atem):
#         print("PGM input changed")
#         pprint(atem.state['program'])
#     a.tallyHandler = tallyWatch
#     a.pgmInputHandler = inputWatch
#     while True:
#         a.waitForPacket()

#    while True:
#        a.waitForPacket()