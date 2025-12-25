"""
Xsens Sensor Recorder Module
Handles device configuration and data recording to .mtb and .csv files
"""

import sys
import xsensdeviceapi as xda
from threading import Lock
import datetime
import csv
import math
import os


class XdaCallback(xda.XsCallback):
    """Callback handler for receiving data packets from the device"""
    def __init__(self, max_buffer_size=5):
        xda.XsCallback.__init__(self)
        self.m_maxNumberOfPacketsInBuffer = max_buffer_size
        self.m_packetBuffer = list()
        self.m_lock = Lock()

    def packetAvailable(self):
        self.m_lock.acquire()
        res = len(self.m_packetBuffer) > 0
        self.m_lock.release()
        return res

    def getNextPacket(self):
        self.m_lock.acquire()
        assert(len(self.m_packetBuffer) > 0)
        oldest_packet = xda.XsDataPacket(self.m_packetBuffer.pop(0))
        self.m_lock.release()
        return oldest_packet

    def onLiveDataAvailable(self, dev, packet):
        self.m_lock.acquire()
        assert(packet != 0)
        while len(self.m_packetBuffer) >= self.m_maxNumberOfPacketsInBuffer:
            self.m_packetBuffer.pop()
        self.m_packetBuffer.append(xda.XsDataPacket(packet))
        self.m_lock.release()


class SensorRecorder:
    """Main class for sensor configuration and recording"""
    
    def __init__(self):
        self.control = None
        self.device = None
        self.callback = None
        self.mtPort = None
        self.device_info = {}
        
    def initialize(self):
        """Initialize XsControl and scan for devices"""
        print("Creating XsControl object...")
        self.control = xda.XsControl_construct()
        assert(self.control != 0)

        xdaVersion = xda.XsVersion()
        xda.xdaVersion(xdaVersion)
        print("Using XDA version %s" % xdaVersion.toXsString())

        print("Scanning for devices...")
        
        # Method 1: Try automatic scanning first
        print("Method 1: Attempting automatic port scan...")
        portInfoArray = xda.XsScanner_scanPorts()
        self.mtPort = xda.XsPortInfo()
        
        for i in range(portInfoArray.size()):
            if portInfoArray[i].deviceId().isMti() or portInfoArray[i].deviceId().isMtig():
                self.mtPort = portInfoArray[i]
                print(f"Found MTi device on {self.mtPort.portName()}")
                break
        
        # Method 2: If automatic scan failed, try manual scanning
        if self.mtPort.empty():
            print("Method 1 failed. Trying Method 2: Manual port scanning...")
            
            # Get all available COM ports
            import serial.tools.list_ports
            available_ports = [port.device for port in serial.tools.list_ports.comports()]
            print(f"Available COM ports: {available_ports}")
            
            if not available_ports:
                raise RuntimeError("No COM ports found. Aborting.")
            
            # Common baudrates to try
            baudrates = [115200, 921600, 2000000, 460800, 230400]
            
            # Try each port with each baudrate
            found = False
            for port in available_ports:
                for baudrate in baudrates:
                    print(f"Trying {port} at {baudrate} baud...")
                    try:
                        test_port = xda.XsScanner_scanPort(port, baudrate)
                        if not test_port.empty():
                            if test_port.deviceId().isMti() or test_port.deviceId().isMtig():
                                self.mtPort = test_port
                                print(f"Found MTi device on {port} at {baudrate} baud!")
                                found = True
                                break
                    except Exception as e:
                        print(f"Error scanning {port} at {baudrate}: {e}")
                        continue
                
                if found:
                    break
        
        # Final check
        if self.mtPort.empty():
            raise RuntimeError("No MTi device found after trying all methods. Aborting.")

        did = self.mtPort.deviceId()
        print("Found a device with:")
        print(" Device ID: %s" % did.toXsString())
        print(" Port name: %s" % self.mtPort.portName())
        print(" Baudrate: %s" % self.mtPort.baudrate())

        print("Opening port...")
        if not self.control.openPort(self.mtPort.portName(), self.mtPort.baudrate()):
            raise RuntimeError("Could not open port. Aborting.")

        # Get the device object
        self.device = self.control.device(did)
        assert(self.device != 0)

        # Store device information
        self.device_info['device_id'] = self.device.deviceId().toXsString()
        self.device_info['product_code'] = self.device.productCode()
        
        # Get firmware version
        firmware_version = self.device.firmwareVersion()
        self.device_info['firmware_version'] = firmware_version.toXsString()
        
        # Get filter profile
        filter_profile = self.device.onboardFilterProfile()
        self.device_info['filter_profile'] = filter_profile.toXsString()
        
        print("Device: %s, with ID: %s opened." % 
            (self.device_info['product_code'], self.device_info['device_id']))
        print("Firmware version: %s" % self.device_info['firmware_version'])
        print("Onboard Kalman Filter Profile: %s" % self.device_info['filter_profile'])

        # Create and attach callback handler
        self.callback = XdaCallback()
        self.device.addCallbackHandler(self.callback)

    def configure_device(self):
        """Configure device output settings at 100Hz"""
        print("Putting device into configuration mode...")
        if not self.device.gotoConfig():
            raise RuntimeError("Could not put device into configuration mode.")

        print("Configuring the device output at 100Hz...")
        configArray = xda.XsOutputConfigurationArray()
        
        # Configure all requested outputs at 100Hz
        configArray.push_back(xda.XsOutputConfiguration(xda.XDI_PacketCounter, 100))
        configArray.push_back(xda.XsOutputConfiguration(xda.XDI_SampleTimeFine, 100))
        configArray.push_back(xda.XsOutputConfiguration(xda.XDI_StatusWord, 100))
        configArray.push_back(xda.XsOutputConfiguration(xda.XDI_RateOfTurn, 100))
        configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Acceleration, 100))
        configArray.push_back(xda.XsOutputConfiguration(xda.XDI_MagneticField, 100))
        configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Temperature, 100))
        configArray.push_back(xda.XsOutputConfiguration(xda.XDI_Quaternion, 100))

        if not self.device.setOutputConfiguration(configArray):
            raise RuntimeError("Could not configure the device.")

        print("Device configured successfully.")

    def get_device_info(self):
        """Return device information"""
        return self.device_info

    def record_data(self, duration_sec=30):
        """
        Record data to .mtb and .csv files
        
        Args:
            duration_sec: Recording duration in seconds (default: 30)
            
        Returns:
            tuple: (mtb_filename, csv_filename)
        """
        # Generate timestamp and filenames
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        product_code = self.device_info['product_code'].replace(' ', '_')
        device_id = self.device_info['device_id'].replace(' ', '_')
        
        # Create folder structure: sensor_data/{product_code}_{device_id}/
        base_dir = "sensor_data"
        sensor_dir = f"{product_code}_{device_id}"
        full_path = os.path.join(base_dir, sensor_dir)
        
        # Check and create directories if they don't exist
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            print(f"Created directory: {base_dir}")
        
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            print(f"Created directory: {full_path}")
        
        # Generate filenames with full path
        base_filename = f"{timestamp}_{product_code}_{device_id}"
        mtb_filename = os.path.join(full_path, f"{base_filename}.mtb")
        csv_filename = os.path.join(full_path, f"{base_filename}.csv")

        # Create .mtb log file
        print(f"Creating MTB log file: {mtb_filename}")
        if self.device.createLogFile(mtb_filename) != xda.XRV_OK:
            raise RuntimeError("Failed to create MTB log file.")

        # Create .csv file and write header
        print(f"Creating CSV file: {csv_filename}")
        csv_file = open(csv_filename, 'w', newline='')
        csv_writer = csv.writer(csv_file)
        
        # CSV Header
        csv_header = [
            'PacketCounter', 'SampleTimeFine', 'StatusWord',
            'Gyr_X', 'Gyr_Y', 'Gyr_Z',
            'Acc_X', 'Acc_Y', 'Acc_Z',
            'Mag_X', 'Mag_Y', 'Mag_Z',
            'Temperature',
            'Quat_W', 'Quat_X', 'Quat_Y', 'Quat_Z',
            'Roll', 'Pitch', 'Yaw'
        ]
        csv_writer.writerow(csv_header)

        # Put device into measurement mode
        print("Putting device into measurement mode...")
        if not self.device.gotoMeasurement():
            raise RuntimeError("Could not put device into measurement mode.")

        # Start recording
        print("Starting recording...")
        if not self.device.startRecording():
            raise RuntimeError("Failed to start recording.")

        print(f"Recording data for {duration_sec} seconds...")
        
        rad2deg = 180.0 / math.pi
        startTime = xda.XsTimeStamp_nowMs()
        duration_ms = duration_sec * 1000
        packet_count = 0

        while xda.XsTimeStamp_nowMs() - startTime <= duration_ms:
            if self.callback.packetAvailable():
                packet = self.callback.getNextPacket()
                packet_count += 1

                # Extract data from packet
                row_data = []
                
                # Packet Counter
                if packet.containsPacketCounter():
                    row_data.append(packet.packetCounter())
                else:
                    row_data.append('')

                # Sample Time Fine
                if packet.containsSampleTimeFine():
                    row_data.append(packet.sampleTimeFine())
                else:
                    row_data.append('')

                # Status Word
                if packet.containsStatus():
                    row_data.append(packet.status())
                else:
                    row_data.append('')

                # Gyroscope (Rate of Turn) - convert to deg/s
                if packet.containsCalibratedGyroscopeData():
                    gyr = packet.calibratedGyroscopeData()
                    row_data.extend([gyr[0] * rad2deg, gyr[1] * rad2deg, gyr[2] * rad2deg])
                else:
                    row_data.extend(['', '', ''])

                # Acceleration
                if packet.containsCalibratedAcceleration():
                    acc = packet.calibratedAcceleration()
                    row_data.extend([acc[0], acc[1], acc[2]])
                else:
                    row_data.extend(['', '', ''])

                # Magnetic Field
                if packet.containsCalibratedMagneticField():
                    mag = packet.calibratedMagneticField()
                    row_data.extend([mag[0], mag[1], mag[2]])
                else:
                    row_data.extend(['', '', ''])

                # Temperature
                if packet.containsTemperature():
                    row_data.append(packet.temperature())
                else:
                    row_data.append('')

                # Quaternion and Euler angles
                if packet.containsOrientation():
                    quaternion = packet.orientationQuaternion()
                    row_data.extend([quaternion[0], quaternion[1], quaternion[2], quaternion[3]])
                    
                    euler = packet.orientationEuler()
                    row_data.extend([euler.x(), euler.y(), euler.z()])
                else:
                    row_data.extend(['', '', '', '', '', '', ''])

                # Write to CSV
                csv_writer.writerow(row_data)

                # Display progress
                elapsed = (xda.XsTimeStamp_nowMs() - startTime) / 1000.0

                # Get gyroscope data for display
                if packet.containsCalibratedGyroscopeData():
                    gyr = packet.calibratedGyroscopeData()
                    gyr_x = gyr[0] * rad2deg
                    gyr_y = gyr[1] * rad2deg
                    gyr_z = gyr[2] * rad2deg
                    print(f"Recording... {elapsed:.1f}s/{duration_sec}s - Packets: {packet_count} - "
                        f"Gyr: X={gyr_x:7.2f}°/s Y={gyr_y:7.2f}°/s Z={gyr_z:7.2f}°/s\r", 
                        end="", flush=True)
                else:
                    print(f"Recording... {elapsed:.1f}s/{duration_sec}s - Packets: {packet_count}\r", 
                        end="", flush=True)

        print(f"\nRecording complete. Total packets recorded: {packet_count}")

        # Stop recording
        print("Stopping recording...")
        if not self.device.stopRecording():
            raise RuntimeError("Failed to stop recording.")

        # Close MTB log file
        print("Closing MTB log file...")
        if not self.device.closeLogFile():
            raise RuntimeError("Failed to close MTB log file.")

        # Close CSV file
        csv_file.close()
        print(f"CSV file closed: {csv_filename}")

        return mtb_filename, csv_filename

    def cleanup(self):
        """Clean up resources"""
        if self.device is not None and self.callback is not None:
            print("Removing callback handler...")
            self.device.removeCallbackHandler(self.callback)

        if self.control is not None and self.mtPort is not None and not self.mtPort.empty():
            print("Closing port...")
            self.control.closePort(self.mtPort.portName())

        if self.control is not None:
            print("Closing XsControl object...")
            self.control.close()