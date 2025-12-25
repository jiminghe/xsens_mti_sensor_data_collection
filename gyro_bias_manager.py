"""
Gyro Bias Manager Module
Handles gyroscope bias estimation and configuration for Xsens MTi sensors
"""

import xsensdeviceapi as xda
import numpy as np
import math
import struct


class GyroBiasManager:
    """Class for managing gyroscope bias calibration"""
    
    def __init__(self, device, callback):
        """
        Initialize the Gyro Bias Manager
        
        Args:
            device: XsDevice object
            callback: XdaCallback object for receiving data packets
        """
        self.device = device
        self.callback = callback
        
    def request_gyro_bias(self):
        """
        Request current gyro bias values from the device
        
        Returns:
            numpy.array: Current gyro bias [x, y, z] in deg/sec, or None if failed
        """
        snd = xda.XsMessage(0x78, 0x02)
        snd.setDataByte(0x05, 1)
        print(f"Requesting gyro bias, full xbus message to send: {snd.toHexString()}")
        
        rcv = xda.XsMessage()
        if self.device.sendCustomMessage(snd, True, rcv, 500):
            if rcv.getMessageId() == 0x79:
                print(f"Message RequestRateOfTurnOffset ACK received successfully: {rcv.toHexString()}")
                raw_rcv = bytes(rcv.rawMessage())
                gyro_bias_x = struct.unpack('>f', raw_rcv[6:10])[0]
                gyro_bias_y = struct.unpack('>f', raw_rcv[10:14])[0]
                gyro_bias_z = struct.unpack('>f', raw_rcv[14:18])[0]
                print(f"Received gyro bias (deg/sec): X = {gyro_bias_x}, Y = {gyro_bias_y}, Z = {gyro_bias_z}")
                return np.array([gyro_bias_x, gyro_bias_y, gyro_bias_z])
        
        print("Failed to retrieve gyro bias values.")
        return None
    
    def set_gyro_bias(self, bias_x=0.0, bias_y=0.0, bias_z=0.0):
        """
        Set gyro bias values on the device
        
        Args:
            bias_x: X-axis bias in deg/sec
            bias_y: Y-axis bias in deg/sec
            bias_z: Z-axis bias in deg/sec
            
        Returns:
            bool: True if successful, False otherwise
        """
        snd = xda.XsMessage(0x78, 0x0E)
        snd.setDataByte(0x05, 1)
        print(f"Setting gyro bias X/Y/Z to = {bias_x}, {bias_y}, {bias_z} deg/sec.")
        snd.setDataFloat(bias_x, 2)
        snd.setDataFloat(bias_y, 6)
        snd.setDataFloat(bias_z, 10)

        print(f"Setting gyro bias, full xbus message to send: {snd.toHexString()}")
        rcv = xda.XsMessage()
        if self.device.sendCustomMessage(snd, True, rcv, 500):
            if rcv.getMessageId() == 0x79:
                print(f"Message setRateOfTurnOffset ACK received successfully, {rcv.toHexString()}")
                return True
        
        print("Failed to set gyro bias values.")
        return False
    
    def collect_gyro_data(self, seconds_to_measure=5):
        """
        Collect gyro data while the device is stationary
        
        Args:
            seconds_to_measure: Duration of data collection in seconds
            
        Returns:
            numpy.array: Collected gyro data [n_samples, 3] in deg/sec, or None if failed
        """
        print(f"\nCollecting gyroscope data for {seconds_to_measure} seconds...")
        print("Please ensure the device remains completely stationary during measurement.")
        
        gyro_data = []
        rad2deg = 180.0 / math.pi
        
        # Clear any old packets
        while self.callback.packetAvailable():
            self.callback.getNextPacket()
        
        startTime = xda.XsTimeStamp_nowMs()
        measurement_time = seconds_to_measure * 1000  # Convert to milliseconds
        
        while xda.XsTimeStamp_nowMs() - startTime <= measurement_time:
            if self.callback.packetAvailable():
                packet = self.callback.getNextPacket()
                
                if packet.containsCalibratedGyroscopeData():
                    gyr = packet.calibratedGyroscopeData()
                    gyr *= rad2deg
                    gyro_data.append(gyr)
                    
                    # Print current reading (overwrite line)
                    s = f"Gyr X: {gyr[0]:.2f}, Gyr Y: {gyr[1]:.2f}, Gyr Z: {gyr[2]:.2f}"
                    print(f"{s}\r", end="", flush=True)
        
        print(f"\nCollected {len(gyro_data)} samples")
        
        if len(gyro_data) == 0:
            print("Warning: No data collected!")
            return None
        
        return np.array(gyro_data)
    
    def calculate_bias_from_data(self, gyro_data):
        """
        Calculate gyro bias statistics from collected data
        
        Args:
            gyro_data: numpy.array of gyro measurements [n_samples, 3]
            
        Returns:
            tuple: (bias_mean, bias_stddev) as numpy arrays, or (None, None) if failed
        """
        if gyro_data is None or len(gyro_data) == 0:
            return None, None
        
        # Calculate offsets (means)
        offset_x = np.mean(gyro_data[:, 0])
        offset_y = np.mean(gyro_data[:, 1])
        offset_z = np.mean(gyro_data[:, 2])
        
        # Calculate standard deviations for quality assessment
        std_x = np.std(gyro_data[:, 0])
        std_y = np.std(gyro_data[:, 1])
        std_z = np.std(gyro_data[:, 2])
        
        return np.array([offset_x, offset_y, offset_z]), np.array([std_x, std_y, std_z])
    
    def estimate_and_apply_bias(self, csv_filename=None, measurement_duration=5):
        """
        Estimate gyro bias from recorded data or new measurement and optionally apply it
        
        Args:
            csv_filename: Path to CSV file with recorded data (optional)
            measurement_duration: Duration for new measurement if csv_filename not provided
            
        Returns:
            dict: Results including bias values, stddev, quality, and whether applied
        """
        result = {
            'success': False,
            'bias': None,
            'stddev': None,
            'quality_good': False,
            'applied': False,
            'message': ''
        }
        
        # If CSV file provided, extract gyro data from it
        if csv_filename:
            print(f"Extracting gyro data from: {csv_filename}")
            gyro_data = self._extract_gyro_from_csv(csv_filename)
        else:
            # Collect new data
            gyro_data = self.collect_gyro_data(seconds_to_measure=measurement_duration)
        
        if gyro_data is None:
            result['message'] = 'Failed to collect/extract gyroscope data.'
            return result
        
        # Calculate bias
        gyro_bias, gyro_std = self.calculate_bias_from_data(gyro_data)
        
        if gyro_bias is None:
            result['message'] = 'Failed to calculate gyro bias.'
            return result
        
        result['bias'] = gyro_bias
        result['stddev'] = gyro_std
        result['success'] = True
        
        # Quality assessment
        std_threshold = 0.20  # deg/sec
        result['quality_good'] = all(gyro_std <= std_threshold)
        
        print("\n===== CALCULATED GYRO BIAS =====")
        print(f"X-axis: {gyro_bias[0]:.4f} ± {gyro_std[0]:.4f} deg/sec")
        print(f"Y-axis: {gyro_bias[1]:.4f} ± {gyro_std[1]:.4f} deg/sec")
        print(f"Z-axis: {gyro_bias[2]:.4f} ± {gyro_std[2]:.4f} deg/sec")
        
        if result['quality_good']:
            result['message'] = 'Bias calculated successfully. Quality is good.'
        else:
            result['message'] = 'Bias calculated but quality issues detected (high variability).'
        
        return result
    
    def apply_bias(self, bias_x, bias_y, bias_z):
        """
        Apply gyro bias values to the device (wrapper for set_gyro_bias)
        
        Args:
            bias_x: X-axis bias in deg/sec
            bias_y: Y-axis bias in deg/sec  
            bias_z: Z-axis bias in deg/sec
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Put device into config mode
        print("Putting device into configuration mode...")
        if not self.device.gotoConfig():
            print("Could not put device into configuration mode.")
            return False
        
        # Apply bias
        success = self.set_gyro_bias(bias_x, bias_y, bias_z)
        
        # Put device back into measurement mode
        print("Putting device back into measurement mode...")
        if not self.device.gotoMeasurement():
            print("Warning: Could not put device back into measurement mode.")
        
        return success
    
    def _extract_gyro_from_csv(self, csv_filename):
        """
        Extract gyroscope data from CSV file
        
        Args:
            csv_filename: Path to CSV file
            
        Returns:
            numpy.array: Gyro data [n_samples, 3] or None if failed
        """
        import csv
        
        gyro_data = []
        
        try:
            with open(csv_filename, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        gyr_x = float(row['Gyr_X'])
                        gyr_y = float(row['Gyr_Y'])
                        gyr_z = float(row['Gyr_Z'])
                        gyro_data.append([gyr_x, gyr_y, gyr_z])
                    except (ValueError, KeyError):
                        continue
            
            if len(gyro_data) == 0:
                print("No valid gyro data found in CSV file.")
                return None
            
            print(f"Extracted {len(gyro_data)} gyro samples from CSV file.")
            return np.array(gyro_data)
            
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return None