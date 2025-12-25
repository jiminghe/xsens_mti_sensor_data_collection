"""
Main Application for Xsens Sensor Data Collection and Analysis

This application:
1. Requests device information (device ID, product code)
2. Configures sensor output at 100Hz
3. Records data to .mtb and .csv files for 30 seconds
4. Computes statistics and saves to database
"""

import sys
import datetime
from sensor_recorder import SensorRecorder
from data_analyzer import DataAnalyzer


def main():
    """Main application entry point"""
    
    print("="*70)
    print("XSENS SENSOR DATA COLLECTION AND ANALYSIS SYSTEM")
    print("="*70)
    print(f"Started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    recorder = None
    
    try:
        # Step 1: Initialize and get device information
        print("\n--- STEP 1: DEVICE INITIALIZATION ---")
        recorder = SensorRecorder()
        recorder.initialize()
        
        device_info = recorder.get_device_info()
        print(f"\nDevice Information:")
        print(f"  Product Code: {device_info['product_code']}")
        print(f"  Device ID: {device_info['device_id']}")
        
        # Step 2: Configure device
        print("\n--- STEP 2: DEVICE CONFIGURATION ---")
        recorder.configure_device()
        print("Configuration complete - All sensors set to 100Hz output")
        
        # Step 3: Record data
        print("\n--- STEP 3: DATA RECORDING ---")
        duration = 30  # Recording duration in seconds
        print(f"Recording duration: {duration} seconds")
        print("Data will be saved to .mtb and .csv files")
        
        mtb_file, csv_file = recorder.record_data(duration_sec=duration)
        
        print(f"\nRecording complete!")
        print(f"  MTB file: {mtb_file}")
        print(f"  CSV file: {csv_file}")
        
        # Step 4: Analyze data and save to database
        print("\n--- STEP 4: DATA ANALYSIS ---")
        analyzer = DataAnalyzer(db_name='sensor_db.db')
        
        # Compute statistics from CSV file
        statistics = analyzer.compute_statistics(csv_file)
        
        # Display statistics
        analyzer.display_statistics()
        
        # Extract timestamp from filename
        timestamp = csv_file.split('_')[0] + '_' + csv_file.split('_')[1]
        
        # Save to database
        print("\n--- STEP 5: SAVE TO DATABASE ---")
        record_id = analyzer.save_to_database(device_info, statistics, timestamp)
        
        print("\n" + "="*70)
        print("DATA COLLECTION AND ANALYSIS COMPLETED SUCCESSFULLY")
        print("="*70)
        print(f"Files generated:")
        print(f"  - {mtb_file}")
        print(f"  - {csv_file}")
        print(f"  - sensor_db.db (Record ID: {record_id})")
        print("="*70 + "\n")
        
    except RuntimeError as error:
        print(f"\n[ERROR] Runtime error: {error}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        if recorder is not None:
            print("\n--- CLEANUP ---")
            recorder.cleanup()
            print("Cleanup complete.")
        
        print(f"\nProgram terminated at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()