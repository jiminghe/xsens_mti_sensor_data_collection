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
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'xsens-sensor-data-collection-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for measurement process
measurement_thread = None
measurement_running = False


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
    global measurement_running
    
    # Redirect stdout to web logger
    web_logger = WebLogger()
    old_stdout = sys.stdout
    sys.stdout = web_logger
    
    recorder = None
    
    try:
        socketio.emit('measurement_status', {'status': 'initializing'}, namespace='/measurement')
        
        # Step 1: Initialize device
        socketio.emit('log_message', {'data': '--- STEP 1: DEVICE INITIALIZATION ---'}, namespace='/measurement')
        recorder = SensorRecorder()
        recorder.initialize()
        
        device_info = recorder.get_device_info()
        socketio.emit('device_info', device_info, namespace='/measurement')
        
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
        
        socketio.emit('measurement_status', {'status': 'complete'}, namespace='/measurement')
        socketio.emit('log_message', {'data': f'✓ Measurement complete! Record ID: {record_id}'}, namespace='/measurement')
        socketio.emit('measurement_complete', {
            'success': True,
            'record_id': record_id,
            'mtb_file': mtb_file,
            'csv_file': csv_file
        }, namespace='/measurement')
        
    except Exception as e:
        error_msg = f'Error: {str(e)}'
        socketio.emit('measurement_status', {'status': 'error'}, namespace='/measurement')
        socketio.emit('log_message', {'data': error_msg}, namespace='/measurement')
        socketio.emit('measurement_complete', {
            'success': False,
            'error': error_msg
        }, namespace='/measurement')
        
    finally:
        if recorder is not None:
            socketio.emit('log_message', {'data': '--- CLEANUP ---'}, namespace='/measurement')
            recorder.cleanup()
        
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