import serial
import time
import numpy

from cmdStrings import *    # definition of serial commands

dvmPortName = "\\\\.\\COM21"
 
dvmPort = serial.Serial()
dvmPort.baudrate = 9600
dvmPort.bytesize = 8
dvmPort.stopbits = 1
dvmPort.xonxoff = 0
dvmPort.rtscts = 0
dvmPort.timeout = 1
dvmPort.port = dvmPortName
dvmPort.parity = serial.PARITY_NONE


dutPortName = "\\\\.\\COM8"
 
dutPort = serial.Serial()
dutPort.baudrate = 115200
dutPort.bytesize = 8
dutPort.stopbits = 1
dutPort.xonxoff = 0
dutPort.rtscts = 0
dutPort.timeout = 1
dutPort.port = dutPortName
dutPort.parity = serial.PARITY_NONE


dvmPort.open()
dutPort.open()

# Identify the DVM
def identifyDVM( port ) :
    port.flushInput()
    port.write( DVM_GET_ID )
    port.flushOutput()
    read_tp4 = dvmPort.readall()
    decode_tp4 = read_tp4.decode('utf-8')
    print(decode_tp4)

# Identify the DUT
def identifyDUT( port ) :
    port.flushInput()
    port.write( DUT_GET_ID )
    port.flushOutput()
    readMsg = dutPort.readall()
    decodeMsg = readMsg.decode('utf-8')
    print(decodeMsg)

# Set DAC output level
def setDAC( port, value ) :
    port.flushInput()

    cmd = "dac {}\r".format(value)
    asBytes = cmd.encode("utf-8")
    numBytes = len(asBytes)
    
    port.write( asBytes )
    port.flushOutput()    
    readDUT = port.readall()
    decodeDUT = readDUT.decode('utf-8')
    print( decodeDUT )


# Get DAC output level
def getDAC( port ) :
    port.flushInput()

    cmd = "dac\r"
    asBytes = cmd.encode("utf-8")
    numBytes = len(asBytes)
    
    port.write( asBytes )
    port.flushOutput()    
    readDUT = port.readall()
    decodeDUT = readDUT.decode('utf-8')
    print( decodeDUT )


# Get DVM voltage reading in volts
def getDVMvolts( port ) :
    port.flushInput()
    port.write( DVM_GET_VOLT )
    port.flushOutput()

    lineData = port.readline()
    decode = lineData.decode('utf-8')
    candidate = decode.split( ' ',1)[0]
    try:
        value = float( candidate )
    except ValueError:
        value = 0
    #print( decode )
    return( value )

# Restart the DUT in case it was crashed
dutPort.send_break( duration = 0.5 )

# Identify the devices
identifyDVM( dvmPort )
identifyDUT( dutPort )

# Check a range of values

checkLength = 42

float_array = numpy.array( [range(checkLength), range(checkLength)], dtype=numpy.float32)
print( float_array.size )

i = 0
index = 0
while index < checkLength :
    setDAC( dutPort, i )
    val = getDVMvolts( dvmPort )
    float_array[0][index] = i
    float_array[1][index] = val
    print( "{}, {}\r\n".format( i, val ) )
    i += 100
    index += 1

#setDAC( dutPort, 1000 )
#val = getDVMvolts( dvmPort )
#print( "Reading was {}\r\n".format( val ) )

#setDAC( dutPort, 2000 )
#val = getDVMvolts( dvmPort )
#print( "Reading was {}\r\n".format( val ) )

for i in range(checkLength) :
    print( "{}, {}".format( int(float_array[0][i]), float_array[1][i] ) )

dvmPort.close()
dutPort.close()

print("Done\r\n")
