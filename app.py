"""
Flask Web Application for Xsens Sensor Data Collection
Main application file with routes and server configuration
"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
import threading
import sys
import io
import datetime
import os
from sensor_recorder import SensorRecorder
from data_analyzer import DataAnalyzer
from gyro_bias_manager import GyroBiasManager
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'xsens-sensor-data-collection-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for measurement process
measurement_thread = None
measurement_running = False
current_recorder = None  # Keep recorder instance for bias application


class WebLogger:
    """Custom logger that emits messages to web interface via SocketIO"""
    def __init__(self):
        self.terminal = sys.stdout
        
    def write(self, message):
        if message.strip():  # Only emit non-empty messages
            socketio.emit('log_message', {'data': message.strip()}, namespace='/measurement')
        self.terminal.write(message)
        
    def flush(self):
        self.terminal.flush()


@app.route('/')
def index():
    """Main page with two buttons: Measure Data and View Historical Data"""
    return render_template('index.html')


@app.route('/measure')
def measure_page():
    """Measurement page - configure, connect, and record data"""
    return render_template('measure.html')


@app.route('/history')
def history_page():
    """Historical data viewing page with filters"""
    return render_template('history.html')


@app.route('/api/start_measurement', methods=['POST'])
def start_measurement():
    """API endpoint to start measurement process"""
    global measurement_thread, measurement_running
    
    if measurement_running:
        return jsonify({'success': False, 'error': 'Measurement already in progress'}), 400
    
    measurement_running = True
    measurement_thread = threading.Thread(target=run_measurement)
    measurement_thread.start()
    
    return jsonify({'success': True, 'message': 'Measurement started'})


def run_measurement():
    """Run the measurement process in a separate thread"""
    global measurement_running, current_recorder
    
    # Redirect stdout to web logger
    web_logger = WebLogger()
    old_stdout = sys.stdout
    sys.stdout = web_logger
    
    recorder = None
    original_bias = None
    
    try:
        socketio.emit('measurement_status', {'status': 'initializing'}, namespace='/measurement')
        
        # Step 1: Initialize device
        socketio.emit('log_message', {'data': '--- STEP 1: DEVICE INITIALIZATION ---'}, namespace='/measurement')
        recorder = SensorRecorder()
        recorder.initialize()
        
        device_info = recorder.get_device_info()
        socketio.emit('device_info', device_info, namespace='/measurement')
        
        # Check firmware version and handle bias
        firmware_version = device_info.get('firmware_version', '')
        socketio.emit('log_message', {'data': f'Firmware Version: {firmware_version}'}, namespace='/measurement')
        
        if firmware_version == '1.13.0':
            socketio.emit('log_message', {'data': '--- GYRO BIAS PRE-PROCESSING (Firmware 1.13.0) ---'}, namespace='/measurement')
            socketio.emit('log_message', {'data': 'Reading current gyro bias...'}, namespace='/measurement')
            
            # Create bias manager
            bias_manager = GyroBiasManager(recorder.device, recorder.callback)
            
            # Put device into config mode to read bias
            if recorder.device.gotoConfig():
                original_bias = bias_manager.request_gyro_bias()
                
                if original_bias is not None:
                    socketio.emit('log_message', {'data': f'Original bias: X={original_bias[0]:.4f}, Y={original_bias[1]:.4f}, Z={original_bias[2]:.4f} deg/s'}, namespace='/measurement')
                    
                    # Set bias to zero before measurement
                    socketio.emit('log_message', {'data': 'Setting gyro bias to zero for measurement...'}, namespace='/measurement')
                    if bias_manager.set_gyro_bias(0.0, 0.0, 0.0):
                        socketio.emit('log_message', {'data': 'Gyro bias set to zero successfully'}, namespace='/measurement')
                    else:
                        socketio.emit('log_message', {'data': 'Warning: Failed to set bias to zero'}, namespace='/measurement')
                else:
                    socketio.emit('log_message', {'data': 'Warning: Could not read original bias, will proceed with measurement'}, namespace='/measurement')
                    original_bias = None
                
                # Return to measurement mode
                recorder.device.gotoMeasurement()
            else:
                socketio.emit('log_message', {'data': 'Warning: Could not enter config mode for bias reading'}, namespace='/measurement')
        
        # Step 2: Configure device
        socketio.emit('measurement_status', {'status': 'configuring'}, namespace='/measurement')
        socketio.emit('log_message', {'data': '--- STEP 2: DEVICE CONFIGURATION ---'}, namespace='/measurement')
        recorder.configure_device()
        
        # Step 3: Record data
        socketio.emit('measurement_status', {'status': 'recording'}, namespace='/measurement')
        socketio.emit('log_message', {'data': '--- STEP 3: DATA RECORDING (30 seconds) ---'}, namespace='/measurement')
        
        mtb_file, csv_file = recorder.record_data(duration_sec=30)
        
        socketio.emit('log_message', {'data': f'MTB file: {mtb_file}'}, namespace='/measurement')
        socketio.emit('log_message', {'data': f'CSV file: {csv_file}'}, namespace='/measurement')
        
        # Step 4: Analyze data
        socketio.emit('measurement_status', {'status': 'analyzing'}, namespace='/measurement')
        socketio.emit('log_message', {'data': '--- STEP 4: DATA ANALYSIS ---'}, namespace='/measurement')
        
        analyzer = DataAnalyzer(db_name='sensor_db.db')
        statistics = analyzer.compute_statistics(csv_file)
        
        # Extract timestamp from filename
        timestamp = csv_file.split(os.sep)[-1].split('_')[0] + '_' + csv_file.split(os.sep)[-1].split('_')[1]
        
        # Step 5: Save to database
        socketio.emit('log_message', {'data': '--- STEP 5: SAVE TO DATABASE ---'}, namespace='/measurement')
        record_id = analyzer.save_to_database(device_info, statistics, timestamp)
        
        # Step 6: Bias calibration option (only for firmware 1.13.0)
        bias_data = None
        should_keep_connection = False
        
        if firmware_version == '1.13.0':
            socketio.emit('log_message', {'data': '\n--- STEP 6: GYRO BIAS CALIBRATION ---'}, namespace='/measurement')
            
            # Calculate new bias from recorded data
            bias_manager = GyroBiasManager(recorder.device, recorder.callback)
            result = bias_manager.estimate_and_apply_bias(csv_filename=csv_file)
            
            if result['success']:
                new_bias = result['bias']
                new_stddev = result['stddev']
                
                bias_data = {
                    'available': True,
                    'original_bias_x': float(original_bias[0]) if original_bias is not None else 0.0,
                    'original_bias_y': float(original_bias[1]) if original_bias is not None else 0.0,
                    'original_bias_z': float(original_bias[2]) if original_bias is not None else 0.0,
                    'new_bias_x': float(new_bias[0]),
                    'new_bias_y': float(new_bias[1]),
                    'new_bias_z': float(new_bias[2]),
                    'std_x': float(new_stddev[0]),
                    'std_y': float(new_stddev[1]),
                    'std_z': float(new_stddev[2]),
                    'quality_good': result['quality_good'],
                    'message': result['message']
                }
                
                socketio.emit('log_message', {'data': f'New bias calculated: X={new_bias[0]:.4f}, Y={new_bias[1]:.4f}, Z={new_bias[2]:.4f} deg/s'}, namespace='/measurement')
                socketio.emit('log_message', {'data': f'Quality: {result["message"]}'}, namespace='/measurement')
                socketio.emit('bias_calibration_available', bias_data, namespace='/measurement')
                
                # Keep the recorder connection alive for bias application
                current_recorder = recorder
                should_keep_connection = True
                socketio.emit('log_message', {'data': 'Device connection kept alive for bias selection...'}, namespace='/measurement')
            else:
                socketio.emit('log_message', {'data': f'Bias calculation failed: {result["message"]}'}, namespace='/measurement')
                
                # If bias calculation failed but we have original bias, restore it
                if original_bias is not None:
                    socketio.emit('log_message', {'data': 'Restoring original bias values...'}, namespace='/measurement')
                    bias_manager = GyroBiasManager(recorder.device, recorder.callback)
                    if recorder.device.gotoConfig():
                        bias_manager.set_gyro_bias(original_bias[0], original_bias[1], original_bias[2])
                        recorder.device.gotoMeasurement()
        else:
            socketio.emit('log_message', {'data': f'\n--- STEP 6: GYRO BIAS CALIBRATION SKIPPED ---'}, namespace='/measurement')
            socketio.emit('log_message', {'data': f'Firmware version {firmware_version} does not support bias calibration (requires 1.13.0)'}, namespace='/measurement')
        
        socketio.emit('measurement_status', {'status': 'complete'}, namespace='/measurement')
        socketio.emit('log_message', {'data': f'✓ Measurement complete! Record ID: {record_id}'}, namespace='/measurement')
        socketio.emit('measurement_complete', {
            'success': True,
            'record_id': record_id,
            'mtb_file': mtb_file,
            'csv_file': csv_file,
            'bias_data': bias_data
        }, namespace='/measurement')
        
        # Only cleanup if we're not keeping connection for bias calibration
        if not should_keep_connection and recorder is not None:
            socketio.emit('log_message', {'data': '--- CLEANUP ---'}, namespace='/measurement')
            recorder.cleanup()
            recorder = None
        
    except Exception as e:
        import traceback
        error_msg = f'Error: {str(e)}'
        error_details = traceback.format_exc()
        socketio.emit('measurement_status', {'status': 'error'}, namespace='/measurement')
        socketio.emit('log_message', {'data': error_msg}, namespace='/measurement')
        socketio.emit('log_message', {'data': error_details}, namespace='/measurement')
        socketio.emit('measurement_complete', {
            'success': False,
            'error': error_msg
        }, namespace='/measurement')
        
        if recorder is not None:
            socketio.emit('log_message', {'data': '--- CLEANUP ---'}, namespace='/measurement')
            recorder.cleanup()
        
    finally:
        measurement_running = False
        sys.stdout = old_stdout


@app.route('/api/historical_data')
def get_historical_data():
    """API endpoint to retrieve historical data with filters"""
    # Get filter parameters
    year = request.args.get('year', '')
    month = request.args.get('month', '')
    date = request.args.get('date', '')
    device_id = request.args.get('device_id', '')
    
    try:
        conn = sqlite3.connect('sensor_db.db')
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        # Build query with filters
        query = "SELECT * FROM sensor_data WHERE 1=1"
        params = []
        
        if year:
            query += " AND substr(time, 1, 4) = ?"
            params.append(year)
        
        if month:
            query += " AND substr(time, 5, 2) = ?"
            params.append(month)
        
        if date:
            query += " AND substr(time, 7, 2) = ?"
            params.append(date)
        
        if device_id:
            query += " AND device_id LIKE ?"
            params.append(f'%{device_id}%')
        
        query += " ORDER BY time DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert rows to list of dictionaries
        data = []
        for row in rows:
            data.append({
                'id': row['id'],
                'time': row['time'],
                'product_code': row['product_code'],
                'device_id': row['device_id'],
                'firmware_version': row['firmware_version'],
                'filter_profile': row['filter_profile'],
                'gyro_x_mean': row['gyro_x_mean'],
                'gyro_x_stddev': row['gyro_x_stddev'],
                'gyro_y_mean': row['gyro_y_mean'],
                'gyro_y_stddev': row['gyro_y_stddev'],
                'gyro_z_mean': row['gyro_z_mean'],
                'gyro_z_stddev': row['gyro_z_stddev'],
                'acc_x_mean': row['acc_x_mean'],
                'acc_x_stddev': row['acc_x_stddev'],
                'acc_y_mean': row['acc_y_mean'],
                'acc_y_stddev': row['acc_y_stddev'],
                'acc_z_mean': row['acc_z_mean'],
                'acc_z_stddev': row['acc_z_stddev'],
                'mag_x_mean': row['mag_x_mean'],
                'mag_x_stddev': row['mag_x_stddev'],
                'mag_y_mean': row['mag_y_mean'],
                'mag_y_stddev': row['mag_y_stddev'],
                'mag_z_mean': row['mag_z_mean'],
                'mag_z_stddev': row['mag_z_stddev'],
                'roll_mean': row['roll_mean'],
                'roll_stddev': row['roll_stddev'],
                'pitch_mean': row['pitch_mean'],
                'pitch_stddev': row['pitch_stddev'],
                'yaw_mean': row['yaw_mean'],
                'yaw_stddev': row['yaw_stddev'],
                'temperature_mean': row['temperature_mean'],
                'temperature_stddev': row['temperature_stddev']
            })
        
        conn.close()
        return jsonify({'success': True, 'data': data})
        
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/get_filters')
def get_filter_options():
    """API endpoint to get available filter options from database"""
    try:
        conn = sqlite3.connect('sensor_db.db')
        cursor = conn.cursor()
        
        # Get unique years
        cursor.execute("SELECT DISTINCT substr(time, 1, 4) as year FROM sensor_data ORDER BY year DESC")
        years = [row[0] for row in cursor.fetchall()]
        
        # Get unique device IDs
        cursor.execute("SELECT DISTINCT device_id FROM sensor_data ORDER BY device_id")
        device_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'years': years,
            'device_ids': device_ids
        })
        
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@socketio.on('connect', namespace='/measurement')
def handle_connect():
    """Handle WebSocket connection"""
    emit('connected', {'data': 'Connected to server'})


@app.route('/api/apply_bias', methods=['POST'])
def apply_bias():
    """API endpoint to apply gyro bias calibration"""
    global current_recorder
    
    try:
        data = request.get_json()
        bias_x = float(data.get('bias_x', 0))
        bias_y = float(data.get('bias_y', 0))
        bias_z = float(data.get('bias_z', 0))
        
        if current_recorder is None:
            return jsonify({
                'success': False,
                'error': 'Device connection not available. Please run a new measurement.'
            }), 400
        
        # Create bias manager with current device
        bias_manager = GyroBiasManager(current_recorder.device, current_recorder.callback)
        
        # Apply the bias values
        success = bias_manager.apply_bias(bias_x, bias_y, bias_z)
        
        # Cleanup the recorder after applying bias
        if success:
            print(f"Successfully applied gyro bias: X={bias_x:.4f}, Y={bias_y:.4f}, Z={bias_z:.4f}")
            current_recorder.cleanup()
            current_recorder = None
            
            return jsonify({
                'success': True,
                'message': f'Bias successfully applied to sensor: X={bias_x:.4f}, Y={bias_y:.4f}, Z={bias_z:.4f} deg/s'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to write bias values to device'
            }), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skip_bias', methods=['POST'])
def skip_bias():
    """API endpoint to skip new bias and restore original bias"""
    global current_recorder
    
    try:
        data = request.get_json()
        original_bias_x = float(data.get('original_bias_x', 0))
        original_bias_y = float(data.get('original_bias_y', 0))
        original_bias_z = float(data.get('original_bias_z', 0))
        
        if current_recorder is None:
            return jsonify({
                'success': False,
                'error': 'Device connection not available'
            }), 400
        
        # Restore original bias
        bias_manager = GyroBiasManager(current_recorder.device, current_recorder.callback)
        
        print(f"Restoring original bias: X={original_bias_x:.4f}, Y={original_bias_y:.4f}, Z={original_bias_z:.4f}")
        success = bias_manager.apply_bias(original_bias_x, original_bias_y, original_bias_z)
        
        # Cleanup the recorder
        current_recorder.cleanup()
        current_recorder = None
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Original bias restored: X={original_bias_x:.4f}, Y={original_bias_y:.4f}, Z={original_bias_z:.4f} deg/s'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to restore original bias'
            }), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    # Create templates and static directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("="*70)
    print("XSENS SENSOR DATA COLLECTION - WEB INTERFACE")
    print("="*70)
    print("\nStarting Flask server...")
    print("Access the application at: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("="*70 + "\n")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)