import re
import os
import sys
import time
import binascii
import urllib
import SocketServer
import SimpleHTTPServer
import threading
from collections import deque
import xbmc
import xbmcaddon
import xbmcgui

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon(id='service.mission.control')
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__addonname__    = __addon__.getAddonInfo('name')
__author__       = __addon__.getAddonInfo('author')
__icon__         = __addon__.getAddonInfo('icon')
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)

import serial

PORT = 8000
SWITCH_COM = 2
TUNER_COM = 12

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

class DeviceStatus(SimpleHTTPServer.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == '/':
            print >>self.wfile, "<html><body>" + str(theCounter) + "<a href='/json'>Patient Test</a>" + str(theStatus) + "</body></html>"
        if self.path == '/counter':
            print >>self.wfile, "<html><body>" + str(theCounter) + "</body></html>"
        if 'json' in self.path:
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", '*')
            self.end_headers()
            self.wfile.write(simplejson.dumps(theStatus))
        if 'tuner' in self.path:
            tunerParams = self.path.split('/')
            #print tunerParams
            theTunerQueue.append(tunerParams[1:])
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", '*')
            self.end_headers()
            self.wfile.write(simplejson.dumps(theStatus['tuner']))
        if 'exec' in self.path:
            print >>self.wfile, '<html><body>command from executor'
            execParams = self.path.split('/')
            print >>self.wfile, execParams
            theExecQueue.append(execParams[1:])
        if 'switch' in self.path:
            switchParams = self.path.split('/')
            #print switchParams
            theSwitchQueue.append(switchParams[1:])
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", '*')
            self.end_headers()
            self.wfile.write(simplejson.dumps(theStatus['outputs']))
        if 'display' in self.path:
            displayParams = self.path.split('/')
            #print displayParams
            if displayParams[2] == '1':
                theLeftDisplayQueue.append(displayParams[1:])
            elif displayParams[2] == '2':
                theCenterADisplayQueue.append(displayParams[1:])
            elif displayParams[2] == '3':
                theCenterBDisplayQueue.append(displayParams[1:])
            elif displayParams[2] == '4':
                theRightADisplayQueue.append(displayParams[1:])
            elif displayParams[2] == '5':
                theRightBDisplayQueue.append(displayParams[1:])
            elif displayParams[2] == '6':
                theActionCenterDisplayQueue.append(displayParams[1:])
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", '*')
            self.end_headers()
            self.wfile.write(simplejson.dumps(theStatus['outputs'][int(displayParams[2])]))

            

class switchThread(threading.Thread):
    def __init__(self, threadID, name, theStatus, theQueue, theInputs, theOutputs):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.theStatus = theStatus
        self.theQueue = theQueue
        self.theInputs = theInputs
        self.theOutputs = theOutputs            
    def run(self):
        try:
                ser = serial.Serial(SWITCH_COM, 9600, timeout=0.3)
        except:
            print'Exception in opening Switch serial'
        while (not xbmc.abortRequested):
            if ser.isOpen() == False:
                try:
                        ser = serial.Serial(SWITCH_COM, 9600, timeout=0.3)
                except:
                        print 'Exception in opening Switch serial'
                        continue
            time.sleep(0.1)
            try:            
                while self.theQueue:
                    #print '**  beginning of command queue loop'
                    command = self.theQueue.popleft()
                    time.sleep(0.02)                    
                    if command[0] == 'switch':
                        #print'*   device type: SWITCH'
                        if command[1] == 'reset':
                            #print'    command type: RESET'
                            xbmc.executebuiltin('Notification(Video Source Control, Resetting All Displays to Default')
                            ser.flushInput()
                            ser.flushOutput()
                            ser.write('\x01\x82\x81\x81')
                            time.sleep(0.02)
                            ser.write('\x01\x83\x82\x81')
                            time.sleep(0.02)
                            ser.write('\x01\x84\x83\x81')
                            time.sleep(0.02)
                            ser.write('\x01\x83\x84\x81')
                            time.sleep(0.02)
                            ser.write('\x01\x82\x85\x81')
                            time.sleep(0.02)
                            ser.write('\x01\x87\x86\x81')
                        else:
                            #print'    command type: SET ' + theOutputs[command[2]]["name"] + ' TO ' + theInputs[command[1]]["name"]
                            xbmc.executebuiltin('Notification(Video Source Control, Switching ' + theOutputs[command[2]]["name"] + ' to ' + theInputs[command[1]]["name"] + ')')
                            ser.write('\x01' + theInputs[command[1]]["hexChar"] + theOutputs[command[2]]["hexChar"] + '\x81')
                        ## end switch loop
            except:
                print 'Exception in writing Switch serial'
                continue      
            # This is where the serial status stuff begins
            #print'*** Begin status section'
            try:
                #print'*   begin reading status of Switch Output 1'
                #print'    serial port opened'
                ser.flushInput()
                #print'    serial input flushed'
                ser.write('\x05\x80\x81\x81')
                #print'    serial command written'
                ser.read(2)
                #print'    read 2 bytes to throw away'
                out = ser.read()
                #print'    read output byte'
                #print'    closing serial port'
                foo = binascii.b2a_qp(out)
                #print'    converting binary to ascii'
                source = foo[2]
                ser.read()
                #print'    putting results in status dictionary'
                theStatus['outputs'][0]['inputNumber'] = source
                theStatus['outputs'][0]['inputName'] = theInputs[source]['name']
                #print'*   finished reading status of Switch Output 1'
            except:
                print'Exception in reading status of Switch Output 1'
                continue
            
            try:
                #print'    begin reading status of Switch Output 2'
                ser.flushInput()
                ser.write('\x05\x80\x82\x81')
                ser.read(2)
                out = ser.read()
                foo = binascii.b2a_qp(out)
                source = foo[2]
                ser.read()
                theStatus['outputs'][1]['inputNumber'] = source
                theStatus['outputs'][1]['inputName'] = theInputs[source]['name']
                #print'    finished reading status of Switch Output 2'
            except:
                print'Exception in reading status of Switch Output 2'
                continue
            
            try:
                #print'    begin reading status of Switch Output 3'
                ser.flushInput()
                ser.write('\x05\x80\x83\x81')
                ser.read(2)
                out = ser.read()
                foo = binascii.b2a_qp(out)
                source = foo[2]
                ser.read()
                theStatus['outputs'][2]['inputNumber'] = source
                theStatus['outputs'][2]['inputName'] = theInputs[source]['name']
                #print'    finished reading status of Switch Output 3'
            except:
                print'Exception in reading status of Switch Output 3'
                continue

            try:
                #print'    begin reading status of Switch Output 4'
                ser.flushInput()
                ser.write('\x05\x80\x84\x81')
                ser.read(2)
                out = ser.read()
                foo = binascii.b2a_qp(out)
                source = foo[2]
                ser.read()
                theStatus['outputs'][3]['inputNumber'] = source
                theStatus['outputs'][3]['inputName'] = theInputs[source]['name']
                #print'    finished reading status of Switch Output 4'
            except:
                print 'Exception in reading status of Switch Output 4'
                continue
            
            try:
                #print'    begin reading status of Switch Output 5'
                ser.flushInput()
                ser.write('\x05\x80\x85\x81')
                ser.read(2)
                out = ser.read()
                foo = binascii.b2a_qp(out)
                source = foo[2]
                ser.read()
                theStatus['outputs'][4]['inputNumber'] = source
                theStatus['outputs'][4]['inputName'] = theInputs[source]['name']
                #print'    finished reading status of Switch Output 5'
            except:
                print 'Exception in reading status of Switch Output 5'
                continue
                  
            try:
                #print'    begin reading status of Switch Output 6'
                ser.flushInput()
                ser.write('\x05\x80\x86\x81')
                ser.read(2)
                out = ser.read()
                foo = binascii.b2a_qp(out)
                source = foo[2]
                ser.read()
                theStatus['outputs'][5]['inputNumber'] = source
                theStatus['outputs'][5]['inputName'] = theInputs[source]['name']
                #print'    finished reading status of Switch Output 6'
            except:
                print 'Exception in reading status of Switch Output 6'
                continue
                  
            try:
                #print'    begin reading status of Switch Output 7'
                ser.flushInput()
                ser.write('\x05\x80\x87\x81')
                ser.read(2)
                out = ser.read()
                foo = binascii.b2a_qp(out)
                source = foo[2]
                ser.read()
                theStatus['outputs'][6]['inputNumber'] = source
                theStatus['outputs'][6]['inputName'] = theInputs[source]['name']
                #print'    finished reading status of Switch Output 7'
            except:
                print 'Exception in reading status of Switch Output 7'
                continue
                    
            try:
                #print'    begin reading status of Switch Output 8'
                ser.flushInput()
                ser.write('\x05\x80\x88\x81')
                ser.read(2)
                out = ser.read()
                foo = binascii.b2a_qp(out)
                source = foo[2]
                ser.read()
                theStatus['outputs'][7]['inputNumber'] = source
                theStatus['outputs'][7]['inputName'] = theInputs[source]['name']
                #print'    finished reading status of Switch Output 8'
            except:
                print'Exception in reading status of Switch Output 8'
                continue   
                
        ser.close() #close serial after thread completes    



class displayThread(threading.Thread):
    def __init__(self, threadID, name, theQueue, comPort):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.theQueue = theQueue
        self.comPort = comPort
    def run(self):
        try:
            ser2 = serial.Serial(self.comPort, 9600, timeout=0.3)
        except:
            print 'Exception in opening Display serial'
        while (not xbmc.abortRequested):
            if ser2.isOpen() == False:
                try:
                    ser2 = serial.Serial(self.comPort, 9600, timeout=0.3)
                except:
                    print 'Exception in opening Display serial'
                    continue                    
            time.sleep(0.1)
            try:
                while self.theQueue:
                    #print '**  beginning of command queue loop'
                    command = self.theQueue.popleft()
                    if command[0] == 'display':
                        #print'*   device type: DISPLAY'
                        if command[2] == 'power':
                            #print'    command type: POWER TOGGLE ' + theOutputs[command[1]]["name"]
                            ser2.flushInput()
                            ser2.flushOutput()                          
                            ser2.write('\x08\x22\x00\x00\x00\x00\xd6')
                        elif command[2] == 'volume':
                            #print'    command type: VOLUME ' + theOutputs[command[1]]["name"]
                            if command[3] == '+':
                                #print'    command: VOLUME UP'
                                ser2.flushInput()
                                ser2.flushOutput()  
                                ser2.write('\x08\x22\x01\x00\x01\x00\xd4')
                            elif command[3] == '-':
                                #print'    command: VOLUME DOWN'
                                ser2.flushInput()
                                ser2.flushOutput()  
                                ser2.write('\x08\x22\x01\x00\x02\x00\xd3')
                            else:
                                #print'    command: MUTE'
                                ser2.flushInput()
                                ser2.flushOutput()  
                                ser2.write('\x08\x22\x02\x00\x00\x00\xd4')
                #print'**  ending of command queue loop'
            except:
                print 'Exception in writing to Display serial'
                continue
        ser2.close() #close serial after thread completes
        
class tunerThread(threading.Thread):
    def __init__(self, threadID, name, theQueue, theStatus):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.theQueue = theQueue
        self.theStatus = theStatus
    def run(self):
        try:
            ser3 = serial.Serial(TUNER_COM, 9600, timeout=0.2)
        except:
            print 'Exception in opening Tuner serial'
        try:
            while (not xbmc.abortRequested):
                if ser3.isOpen() == False:
                    try:
                        ser3 = serial.Serial(TUNER_COM, 9600, timeout=0.2)
                    except:
                        print 'Exception in opening Tuner Serial'
                        continue
                time.sleep(0.1)
                try:
                    while self.theQueue:               
                        #print '**  beginning of command queue loop'
                        command = self.theQueue.popleft()
                        if command[0] == 'tuner':   
                            #print '*   device type: TUNER'
                            if command[1] == 'channel':
                                #print '    command type: CHANNEL'
                                if command[2] == '+':
                                    #print '    command: CHANNEL UP'
                                    ser3.flushInput()
                                    ser3.flushOutput()   
                                    ser3.write('>P1\x0d')
                                    ser3.write('>TU\x0d')
                                elif command[2] == '-':
                                    #print '    command: CHANNEL DOWN'
                                    ser3.write('>P1\x0d')
                                    ser3.write('>TD\x0d')
                                else:
                                    #print '    command: TUNE TO ' + command[2]
                                    ser3.flushInput()
                                    ser3.flushOutput()   
                                    ser3.write('>P1\x0d')
                                    ser3.write('>TC=' + command[2] + '\x0d')
                            elif command[1] == 'power':
                                #print '    command type: POWER'
                                if command[2] == 'on':
                                    #print '    command: POWER ON'
                                    ser3.flushInput()
                                    ser3.flushOutput()   
                                    ser3.write('>P1\x0d')
                                elif command[2] == 'off':
                                    #print'    command: POWER OFF'
                                    ser3.flushInput()
                                    ser3.flushOutput()   
                                    ser3.write('>P0\x0d')
                                elif command[2] == 'toggle':
                                    #print'    command: POWER TOGGLE'
                                    ser3.flushInput()
                                    ser3.flushOutput()   
                                    ser3.write('>PT\x0d')
                except:
                    print 'Exception writing to Tuner serial'
                    continue        
                        
                # Tuner read
                #print'**  Begin Tuner status'
                try:
                    #print'    starting tuner channel number read'
                    ser3.flushInput()
                    ser3.write('>ST\x0d')
                    ser3.read(4)
                    majorChannel = ser3.read(3)
                    #print'    ' + majorChannel
                    ser.read(4)
                    minorChannel = ser3.read(3)
                    #print'    ' + minorChannel
                    theStatus['tuner']['majorChannel'] = majorChannel
                    theStatus['tuner']['minorChannel'] = minorChannel
                    #print'    finished tuner channel number read'
                except:
                    print 'Exception in reading Tuner Channel Info'
                    continue
                
                # try:
                    # print '*   starting tuner channel name read'
                    # ser = serial.Serial(TUNER_COM, 9600, timeout=1.0)
                    # print '    serial port opened'
                    # ser.flushInput()
                    # print '    serial input flushed'
                    # ser.write('>NC\x0d')
                    # print '    channel name command written'
                    # ser.read(4)
                    # print '    read and throw away first four bytes'
                    # channelName = ''
                    # print '    read until you see a carriage return'
                    # while True:
                        # byte=ser.read()
                        # if byte == '\r':
                            # break
                        # channelName += byte
                    # print '    ' + channelName
                    # print '    finished reading channel name'
                    # ser.close()
                    # print '    serial port closed'
                    # theStatus['tuner']['channelName'] = channelName
                    # print '*   finished tuner channel name read'
                # except:
                    # print 'Exception in reading Tuner Channel Name'
                    # continue
                
                # try:
                    # print '*   starting tuner program name read'
                    # ser = serial.Serial(TUNER_COM, 9600, timeout=1.0)
                    # print '    serial port opened'
                    # ser.flushInput()
                    # print '    serial input flushed'
                    # ser.write('>NP\x0d')
                    # print '    program name command written'
                    # ser.read(4)
                    # print '    read and throw away first four bytes'
                    # programName = ''
                    # print '    read until you see a carriage return'
                    # while True:
                        # byte=ser.read()
                        # if byte == '\r':
                            # break
                        # programName += byte
                    # print '    ' + programName
                    # print '    finished reading program name'
                    # ser.close()
                    # print '    serial port closed'
                    # theStatus['tuner']['programName'] = programName
                    # print '    finished tuner program name read'
                # except:
                    # print 'Exception in reading Tuner Program Name'
                    # continue
                # print '*** End status section'
        except:
            print 'Exception in opening Tuner serial'
                    

if (__name__  == "__main__"):
    xbmc.log('Version %s started' % __addonversion__)
    theSwitchQueue = deque()
    theLeftDisplayQueue = deque()
    theCenterADisplayQueue = deque()
    theCenterBDisplayQueue = deque()
    theRightADisplayQueue = deque()
    theRightBDisplayQueue = deque()
    theActionCenterDisplayQueue = deque()
    theExecQueue = deque()
    theTunerQueue = deque()
    theCounter = 0
    theInputs = {"1":{"name":"ClickShare","hexChar":'\x81'},"2":{"name":"MCC Video 1","hexChar":'\x82'},"3":{"name":"MCC Video 2","hexChar":'\x83'},"4":{"name":"MCC Video 3","hexChar":'\x84'},"5":{"name":"Apple TV","hexChar":'\x85'},"6":{"name":"WiDi","hexChar":'\x86'},"7":{"name":"VADER","hexChar":'\x87'},"8":{"name":"TV Tuner","hexChar":'\x88'},"0":{"name":"N/A","hexChar":'\x80'}}
    theOutputs = {"1":{"name":"Left","hexChar":'\x81',"comPort":"6"},"2":{"name":"Center A","hexChar":'\x82',"comPort":"9"},"3":{"name":"Center B","hexChar":'\x83',"comPort":"10"},"4":{"name":"Right A","hexChar":'\x84',"comPort":"8"},"5":{"name":"Right B","hexChar":'\x85',"comPort":"7"},"6":{"name":"Action Center","hexChar":'\x86',"comPort":"11"},"7":{"name":"HEVS 1","hexChar":'\x87',"comPort":"0"},"8":{"name":"HEVS 2","hexChar":'\x88',"comPort":"0"}}
    theStatus = {"outputs":[{"outputName":"Left","outputNumber":"1","inputNumber":"1","inputName":"ClickShare"},{"outputName":"Center A","outputNumber":"2","inputNumber":"1","inputName":"ClickShare"},{"outputName":"Center B","outputNumber":"3","inputNumber":"2","inputName":"MCC Video 1"},{"outputName":"Right A","outputNumber":"4","inputNumber":"1","inputName":"ClickShare"},{"outputName":"Right B","outputNumber":"5","inputNumber":"2","inputName":"MCC Video 1"},{"outputName":"Action Center","outputNumber":"6","inputNumber":"3","inputName":"MCC Video 2"},{"outputName":"HEVS 1","outputNumber":"7","inputNumber":"5","inputName":"Apple TV"},{"outputName":"HEVS 2","outputNumber":"8","inputNumber":"6","inputName":"WiDi"}],"tuner":{"majorChannel":"008","minorChannel":"001","channelName":"KUHT-HD","programName":"Daytripper"}}
    #theStatus = {'left': 1, 'center1': 1, 'center2': 2, 'right1': 1, 'right2':2, 'actionCenter': 3, 'HEVS1': 5, 'HEVS2': 6}
    httpd = ThreadedTCPServer(('', PORT), DeviceStatus)
    #print "serving at port", PORT
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    #print "starting the counter"
    
    
    # Create new threads
    switchThread               = switchThread (1, "Switch Thread", theStatus, theSwitchQueue, theInputs, theOutputs)
    leftDisplayThread          = displayThread(2, theOutputs["1"]["name"], theLeftDisplayQueue,   int(theOutputs["1"]["comPort"]))
    centerADisplayThread       = displayThread(3, theOutputs["2"]["name"], theCenterADisplayQueue, int(theOutputs["2"]["comPort"]))
    centerBDisplayThread       = displayThread(4, theOutputs["3"]["name"], theCenterBDisplayQueue, int(theOutputs["3"]["comPort"]))
    rightADisplayThread        = displayThread(5, theOutputs["4"]["name"], theRightADisplayQueue,  int(theOutputs["4"]["comPort"]))
    rightBDisplayThread        = displayThread(6, theOutputs["5"]["name"], theRightBDisplayQueue,  int(theOutputs["5"]["comPort"]))
    actionCenterDisplayThread  = displayThread(7, theOutputs["6"]["name"], theActionCenterDisplayQueue,  int(theOutputs["6"]["comPort"]))
    tunerThread                = tunerThread  (8, "Tuner Thread", theTunerQueue, theStatus)

    # Set threads at daemons
    switchThread.daemon = True
    leftDisplayThread.daemon = True 
    centerADisplayThread.daemon = True  
    centerBDisplayThread.daemon = True  
    rightADisplayThread.daemon = True   
    rightBDisplayThread.daemon = True       
    actionCenterDisplayThread.daemon = True 
    tunerThread.daemon = True   
    
    # Start new threads
    switchThread.start()  
    leftDisplayThread.start()  
    centerADisplayThread.start()  
    centerBDisplayThread.start()  
    rightADisplayThread.start()  
    rightBDisplayThread.start()     
    actionCenterDisplayThread.start()  
    tunerThread.start()  
    
    while (not xbmc.abortRequested):
        time.sleep(0.1)
        theCounter += 1
        while theExecQueue:
            #print '**  beginning of command queue loop'
            command = theExecQueue.popleft()        
            if command[0] == 'exec':
                #print'*   command type: SCRIPT EXECUTION'
                if len(command) == 1:
                    #print'    command: EXEC ERROR - NO SCRIPT SPECIFIED'
                    xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%('Executor Error','No script specified for execution',5000,__icon__))
                elif len(command) == 2:
                    #print'    command: running ' + urllib.unquote_plus(command[1])
                    xbmc.executebuiltin('RunScript(' + urllib.unquote_plus(command[1]) + ')')
                elif len(command) == 3:
                    #print'    command: running ' + urllib.unquote_plus(command[1])
                    xbmc.executebuiltin('RunScript(' + urllib.unquote_plus(command[1]) + ',' + urllib.unquote_plus(command[2]) + ')')
                else:
                    #print'    command: running ' + urllib.unquote_plus(command[1])
                    xbmc.executebuiltin('RunScript(' + urllib.unquote_plus(command[1]) + ',' + urllib.unquote_plus(command[2]) + ',' + urllib.unquote_plus(command[3]) + ')')
    
    print "Exiting Main Thread"

    print "starting server shutdown"
    httpd.shutdown()
    print "finished server shutdown"