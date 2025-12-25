"""
Xsens Data Analyzer Module
Handles computation of statistics and database storage
"""

import csv
import sqlite3
import numpy as np
import datetime
import os


class DataAnalyzer:
    """Class for analyzing sensor data and storing results in database"""
    
    def __init__(self, db_name='sensor_db.db'):
        self.db_name = db_name
        self.statistics = {}
        
    def compute_statistics(self, csv_filename):
        """
        Compute mean and standard deviation for sensor data
        
        Args:
            csv_filename: Path to CSV file containing sensor data
            
        Returns:
            dict: Dictionary containing all computed statistics
        """
        print(f"\nAnalyzing data from: {csv_filename}")
        
        # Read CSV file
        data = {
            'gyr_x': [], 'gyr_y': [], 'gyr_z': [],
            'acc_x': [], 'acc_y': [], 'acc_z': [],
            'mag_x': [], 'mag_y': [], 'mag_z': [],
            'temperature': [],
            'roll': [], 'pitch': [], 'yaw': []
        }
        
        with open(csv_filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Gyroscope data
                    if row['Gyr_X']:
                        data['gyr_x'].append(float(row['Gyr_X']))
                    if row['Gyr_Y']:
                        data['gyr_y'].append(float(row['Gyr_Y']))
                    if row['Gyr_Z']:
                        data['gyr_z'].append(float(row['Gyr_Z']))
                    
                    # Acceleration data
                    if row['Acc_X']:
                        data['acc_x'].append(float(row['Acc_X']))
                    if row['Acc_Y']:
                        data['acc_y'].append(float(row['Acc_Y']))
                    if row['Acc_Z']:
                        data['acc_z'].append(float(row['Acc_Z']))
                    
                    # Magnetic field data
                    if row['Mag_X']:
                        data['mag_x'].append(float(row['Mag_X']))
                    if row['Mag_Y']:
                        data['mag_y'].append(float(row['Mag_Y']))
                    if row['Mag_Z']:
                        data['mag_z'].append(float(row['Mag_Z']))
                    
                    # Temperature data
                    if row['Temperature']:
                        data['temperature'].append(float(row['Temperature']))
                    
                    # Euler angles
                    if row['Roll']:
                        data['roll'].append(float(row['Roll']))
                    if row['Pitch']:
                        data['pitch'].append(float(row['Pitch']))
                    if row['Yaw']:
                        data['yaw'].append(float(row['Yaw']))
                        
                except (ValueError, KeyError) as e:
                    # Skip rows with missing or invalid data
                    continue
        
        # Compute statistics
        stats = {}
        
        for key, values in data.items():
            if len(values) > 0:
                stats[f'{key}_mean'] = np.mean(values)
                stats[f'{key}_stddev'] = np.std(values)
                print(f"{key}: mean = {stats[f'{key}_mean']:.6f}, stddev = {stats[f'{key}_stddev']:.6f}")
            else:
                stats[f'{key}_mean'] = None
                stats[f'{key}_stddev'] = None
                print(f"{key}: No data available")
        
        self.statistics = stats
        return stats
    
    def create_database(self):
        """Create database and table if they don't exist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create table with all required fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                product_code TEXT NOT NULL,
                device_id TEXT NOT NULL,
                gyro_x_mean REAL,
                gyro_x_stddev REAL,
                gyro_y_mean REAL,
                gyro_y_stddev REAL,
                gyro_z_mean REAL,
                gyro_z_stddev REAL,
                acc_x_mean REAL,
                acc_x_stddev REAL,
                acc_y_mean REAL,
                acc_y_stddev REAL,
                acc_z_mean REAL,
                acc_z_stddev REAL,
                mag_x_mean REAL,
                mag_x_stddev REAL,
                mag_y_mean REAL,
                mag_y_stddev REAL,
                mag_z_mean REAL,
                mag_z_stddev REAL,
                roll_mean REAL,
                roll_stddev REAL,
                pitch_mean REAL,
                pitch_stddev REAL,
                yaw_mean REAL,
                yaw_stddev REAL,
                temperature_mean REAL,
                temperature_stddev REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized: {self.db_name}")
    
    def save_to_database(self, device_info, statistics, timestamp=None):
        """
        Save computed statistics to database
        
        Args:
            device_info: Dictionary containing device_id and product_code
            statistics: Dictionary containing computed mean and stddev values
            timestamp: Optional timestamp string (YYMMDD_HHMMSS format)
        """
        if timestamp is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create database if it doesn't exist
        self.create_database()
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Prepare data for insertion
        insert_data = (
            timestamp,
            device_info['product_code'],
            device_info['device_id'],
            statistics.get('gyr_x_mean'),
            statistics.get('gyr_x_stddev'),
            statistics.get('gyr_y_mean'),
            statistics.get('gyr_y_stddev'),
            statistics.get('gyr_z_mean'),
            statistics.get('gyr_z_stddev'),
            statistics.get('acc_x_mean'),
            statistics.get('acc_x_stddev'),
            statistics.get('acc_y_mean'),
            statistics.get('acc_y_stddev'),
            statistics.get('acc_z_mean'),
            statistics.get('acc_z_stddev'),
            statistics.get('mag_x_mean'),
            statistics.get('mag_x_stddev'),
            statistics.get('mag_y_mean'),
            statistics.get('mag_y_stddev'),
            statistics.get('mag_z_mean'),
            statistics.get('mag_z_stddev'),
            statistics.get('roll_mean'),
            statistics.get('roll_stddev'),
            statistics.get('pitch_mean'),
            statistics.get('pitch_stddev'),
            statistics.get('yaw_mean'),
            statistics.get('yaw_stddev'),
            statistics.get('temperature_mean'),
            statistics.get('temperature_stddev')
        )
        
        # Insert data
        cursor.execute('''
            INSERT INTO sensor_data (
                time, product_code, device_id,
                gyro_x_mean, gyro_x_stddev,
                gyro_y_mean, gyro_y_stddev,
                gyro_z_mean, gyro_z_stddev,
                acc_x_mean, acc_x_stddev,
                acc_y_mean, acc_y_stddev,
                acc_z_mean, acc_z_stddev,
                mag_x_mean, mag_x_stddev,
                mag_y_mean, mag_y_stddev,
                mag_z_mean, mag_z_stddev,
                roll_mean, roll_stddev,
                pitch_mean, pitch_stddev,
                yaw_mean, yaw_stddev,
                temperature_mean, temperature_stddev
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', insert_data)
        
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        
        print(f"\nData saved to database: {self.db_name}")
        print(f"Record ID: {row_id}")
        print(f"Timestamp: {timestamp}")
        print(f"Product Code: {device_info['product_code']}")
        print(f"Device ID: {device_info['device_id']}")
        
        return row_id
    
    def display_statistics(self):
        """Display computed statistics in a formatted manner"""
        if not self.statistics:
            print("No statistics computed yet.")
            return
        
        print("\n" + "="*60)
        print("SENSOR DATA STATISTICS SUMMARY")
        print("="*60)
        
        print("\n--- GYROSCOPE (deg/s) ---")
        print(f"X-axis: Mean = {self.statistics.get('gyr_x_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('gyr_x_stddev', 'N/A'):.6f}")
        print(f"Y-axis: Mean = {self.statistics.get('gyr_y_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('gyr_y_stddev', 'N/A'):.6f}")
        print(f"Z-axis: Mean = {self.statistics.get('gyr_z_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('gyr_z_stddev', 'N/A'):.6f}")
        
        print("\n--- ACCELERATION (m/s²) ---")
        print(f"X-axis: Mean = {self.statistics.get('acc_x_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('acc_x_stddev', 'N/A'):.6f}")
        print(f"Y-axis: Mean = {self.statistics.get('acc_y_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('acc_y_stddev', 'N/A'):.6f}")
        print(f"Z-axis: Mean = {self.statistics.get('acc_z_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('acc_z_stddev', 'N/A'):.6f}")
        
        print("\n--- MAGNETIC FIELD (a.u.) ---")
        print(f"X-axis: Mean = {self.statistics.get('mag_x_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('mag_x_stddev', 'N/A'):.6f}")
        print(f"Y-axis: Mean = {self.statistics.get('mag_y_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('mag_y_stddev', 'N/A'):.6f}")
        print(f"Z-axis: Mean = {self.statistics.get('mag_z_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('mag_z_stddev', 'N/A'):.6f}")
        
        print("\n--- EULER ANGLES (deg) ---")
        print(f"Roll:  Mean = {self.statistics.get('roll_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('roll_stddev', 'N/A'):.6f}")
        print(f"Pitch: Mean = {self.statistics.get('pitch_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('pitch_stddev', 'N/A'):.6f}")
        print(f"Yaw:   Mean = {self.statistics.get('yaw_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('yaw_stddev', 'N/A'):.6f}")
        
        print("\n--- TEMPERATURE (°C) ---")
        print(f"Mean = {self.statistics.get('temperature_mean', 'N/A'):.6f}, "
              f"StdDev = {self.statistics.get('temperature_stddev', 'N/A'):.6f}")
        
        print("="*60 + "\n")