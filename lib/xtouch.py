from mido import Message, open_input, open_output, get_input_names, get_output_names
import threading
import time

class Xtouch:

    MC_CHANNEL = 0

    MIDI_BUTTONS = [89, 90, 40, 41, 42, 43, 44, 45, 87, 88, 91, 92, 86, 93, 94, 95]
    MIDI_PUSH = [32, 33, 34, 35, 36, 37, 38, 39]
    MIDI_ENCODER = [16, 17, 18, 19, 20, 21, 22, 23]
    MIDI_RING = [48, 49, 50, 51, 52, 53, 54, 55]
    MIDI_LAYER = [84, 85]

    LED_OFF = 0
    LED_BLINK = 1
    LED_ON = 127

    BUTTONS = [
        [
            "HDMI1", "HDMI2", "HDMI3", "HDMI4", "SDI5", "SDI6", "SDI7", "SDI8", "MP1", "MP2", None, None, "Bars", "FTB", "Auto", "Cut"
        ],
        [
            None, "USK1On", "USK2On", "USK3On", "USK4On", None, "DSK1On", "DSK2On", "BkgdPrv", "USK1Prv", "USK2Prv", "USK3Prv", "Usk4Prv", None, "DSK1Prv", "DSK2Prv"           
        ]
    ]

    active_layer = 0
    active_bus = 0

    inport = None
    outport = None
    

    def __init__(self, atem):
        self.isConnected = "XTouch not connected"
        self.pitchwheelInMotion = False
        self.atem = atem

        for name in get_input_names():
            if "x-touch mini" in name.lower():
                print('Using MIDI input: ' + name)
                try:
                    self.inport = open_input(name)
                except IOError as e:
                    print('Error: Can not open MIDI input port ' + name)
                    print ("I/O error({0}): {1}".format(e.errno, e.strerror))
                    exit()
                break

        for name in get_output_names():
            if "x-touch mini" in name.lower():
                print('Using MIDI output: ' + name)
                try:
                    self.outport = open_output(name)
                except IOError:
                    print('Error: Can not open MIDI input port ' + name)
                    exit()
                break
        
        if self.inport is None or self.outport is None:
            print('X-Touch Mini not found. Make sure device is connected!')
            exit()

        self.isConnected = "Connected to XTouch"
        time.sleep(2)
        self.change_layer(0)
        worker = threading.Thread(target = self.midi_listener)
        worker.start()
        xtouchButtonTimer = threading.Thread(target = self.refresh_xtouch)
        xtouchButtonTimer.start()

    def midi_listener(self):
        print("Start thread")
        #self.refresh_controls()
        try:
            for msg in self.inport:
                print('Received {}'.format(msg))
                if msg.type == 'control_change':
                    pass
                elif msg.type == 'note_on' and msg.velocity == 127:
                    if msg.note in self.MIDI_PUSH:
                        self.knob_pushed(self.MIDI_PUSH.index(msg.note))
                    elif msg.note in self.MIDI_BUTTONS:
                        self.button_pushed(self.MIDI_BUTTONS.index(msg.note))
                    elif msg.note in self.MIDI_LAYER:
                        self.change_layer(self.MIDI_LAYER.index(msg.note))
                    else:
                        print('Received unknown {}'.format(msg))
                # elif msg.type == 'pitchwheel':
                #     if self.pitchwheelInMotion == False and (msg.pitch < 8000 and msg.pitch > -8000):
                #         self.atem.doAuto()
                #         self.pitchwheelInMotion = True
                #     else:
                #         self.pitchwheelInMotion = False
            #self.refresh_controls()
        except KeyboardInterrupt:
            self.inport.close()
            self.outport.close()
            print("Closing")
            exit()

    def knob_pushed(self,knob):
        print("TODO: Knob pushed " + str(knob))

    def button_pushed(self,button):
        if self.BUTTONS[self.active_layer][button] is None:
            return    
        buttonName = self.BUTTONS[self.active_layer][button]
        if self.active_layer == 0:
            if button < 13:
                # Change source
                self.atem.setPreview(button)
                self.refresh_controls()
            elif button == 13:
                self.atem.doFTB()
            elif button == 14:
                self.atem.doAuto()
            elif button == 15:
                self.atem.doCut()
            else:
                return
        elif self.active_layer == 1:
            print ("TODO: Keyer for " + buttonName)

    def change_layer(self, layer):
        if layer == 0:
            self.outport.send(Message('note_on', channel = self.MC_CHANNEL, note = self.MIDI_LAYER[0], velocity = self.LED_ON))
            self.outport.send(Message('note_on', channel = self.MC_CHANNEL, note = self.MIDI_LAYER[1], velocity = self.LED_OFF))
            #self.activate_bank(self.state.active_bank)
        else:
            self.outport.send(Message('note_on', channel = self.MC_CHANNEL, note = self.MIDI_LAYER[0], velocity = self.LED_OFF))
            self.outport.send(Message('note_on', channel = self.MC_CHANNEL, note = self.MIDI_LAYER[1], velocity = self.LED_ON))
            #if self.state.active_bank > 2:
            #    self.activate_bank(2)
        self.active_layer = layer
        #self.refresh_controls(self.state.active_bank)
    

    def refresh_xtouch(self):
        while True:
            if self.atem.hasChangeForXTouch == True:
                self.refresh_controls()
                self.atem.hasChangeForXTouch = False
            time.sleep(0.5)
    
    def refresh_controls(self):
        if self.active_layer == 0:
            #Clear lights
            i=0
            for i in range(len(self.BUTTONS[self.active_layer])):
                self.set_button(i,0) 
            for i in range(len(self.atem.atemState)):
                currentInput = self.atem.atemState[i]
                if currentInput is not None:
                    if currentInput.isOnAir == True:
                        self.set_button(i, 2)
                    elif currentInput.isPreview == True:
                        self.set_button(i, 1)
                    else:
                        self.set_button(i,0)
                else:
                    pass
        else:
            print("TODO: Refresh controls for layer 1")
    
    def set_button(self, button, buttonState):
        if buttonState == 2:
            self.outport.send(Message('note_on', channel = self.MC_CHANNEL, note = self.MIDI_BUTTONS[button], velocity = self.LED_ON))
        elif buttonState == 1:
            self.outport.send(Message('note_on', channel = self.MC_CHANNEL, note = self.MIDI_BUTTONS[button], velocity = self.LED_BLINK))
        else:
            self.outport.send(Message('note_on', channel = self.MC_CHANNEL, note = self.MIDI_BUTTONS[button], velocity = self.LED_OFF))
