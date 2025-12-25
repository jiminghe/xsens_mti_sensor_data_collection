# Xsens Sensor Data Collection - Web Application

## Overview
Professional web-based application for Xsens MTi sensor data collection, analysis, and historical data management. Features a modern, responsive interface built with Flask and Bootstrap.

## Features

### 🎯 Main Dashboard
- Clean, intuitive interface with two main functions
- Quick access to measurement and historical data viewing
- System information display

### 📊 Data Measurement
- One-click automated measurement process
- Real-time console output with color-coded messages
- Live status updates during measurement
- Automatic device detection and configuration
- 30-second data recording at 100Hz
- Automatic statistical analysis
- Database storage

### 📈 Historical Data Viewer
- Browse all recorded sensor measurements
- Advanced filtering by:
  - Year
  - Month
  - Date
  - Device ID
- Detailed statistics view for each record
- Mean ± Standard Deviation display for:
  - Gyroscope (X, Y, Z axes)
  - Accelerometer (X, Y, Z axes)
  - Magnetometer (X, Y, Z axes)
  - Euler Angles (Roll, Pitch, Yaw)
  - Temperature

## Project Structure

```
.
├── app.py                      # Flask application (main server)
├── sensor_recorder.py          # Device configuration and recording
├── data_analyzer.py            # Data analysis and database operations
├── main.py                     # Command-line interface (optional)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── templates/                  # HTML templates
│   ├── base.html              # Base template with navbar
│   ├── index.html             # Main dashboard
│   ├── measure.html           # Measurement page
│   └── history.html           # Historical data viewer
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css          # Custom CSS styles
│   └── js/                    # JavaScript files (if needed)
│
├── sensor_data/               # Data storage (auto-created)
│   └── {product_code}_{device_id}/
│       ├── YYYYMMDD_HHMMSS_*.mtb
│       └── YYYYMMDD_HHMMSS_*.csv
│
└── sensor_db.db               # SQLite database (auto-created)
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Xsens MTi device
- Xsens Device API installed

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Install Xsens Device API
Follow the official Xsens documentation to install the xsensdeviceapi package for your platform.

## Usage

### Starting the Web Application
```bash
python app.py
```

The application will start on `http://localhost:5000`

You should see:
```
XSENS SENSOR DATA COLLECTION - WEB INTERFACE
======================================================================

Starting Flask server...
Access the application at: http://localhost:5000

Press Ctrl+C to stop the server
======================================================================
```

### Accessing the Application
1. Open your web browser
2. Navigate to `http://localhost:5000`
3. You will see the main dashboard with two options

### Measuring Data
1. Click "Start Measurement" button on the main page or navigate to `/measure`
2. Click "Start Measurement" on the measurement page
3. Watch the real-time console output as the system:
   - Initializes the device
   - Configures sensors at 100Hz
   - Records data for 30 seconds
   - Analyzes the data
   - Saves to database
4. View the completion summary with file locations

### Viewing Historical Data
1. Click "View Historical Data" on the main page or navigate to `/history`
2. Use filters to narrow down results:
   - Select Year, Month, Date
   - Choose specific Device ID
   - Click "Apply Filters"
3. Click "View Details" on any record to see complete statistics
4. The detail modal shows mean ± std dev for all sensor axes

## Technical Details

### Sensors Configured (100Hz)
- Packet Counter
- Sample Time Fine
- Status Word
- Rate of Turn (Gyroscope)
- Acceleration
- Magnetic Field
- Temperature
- Orientation (Quaternion)
- Euler Angles (Roll, Pitch, Yaw)

### Data Recording
- **Duration**: 30 seconds
- **Sampling Rate**: 100 Hz
- **Output Formats**:
  - `.mtb` - Binary format for Xsens MT Manager
  - `.csv` - Human-readable text format

### Database Schema
SQLite database with the following fields:
- Timestamp (YYYYMMDD_HHMMSS)
- Device information (product_code, device_id)
- Gyroscope statistics (mean, stddev for X, Y, Z)
- Accelerometer statistics (mean, stddev for X, Y, Z)
- Magnetometer statistics (mean, stddev for X, Y, Z)
- Euler angle statistics (mean, stddev for Roll, Pitch, Yaw)
- Temperature statistics (mean, stddev)

## Web Technologies Used

### Backend
- **Flask** - Web framework
- **Flask-SocketIO** - Real-time bidirectional communication
- **SQLite3** - Database

### Frontend
- **Bootstrap 5.3** - Responsive UI framework
- **Bootstrap Icons** - Icon library
- **jQuery** - DOM manipulation
- **Socket.IO** - Real-time updates

### Features
- Real-time console output via WebSockets
- Responsive design (mobile-friendly)
- Modern, clean UI with professional styling
- Interactive data tables
- Modal dialogs for detailed views
- Color-coded status indicators

## API Endpoints

### POST /api/start_measurement
Start a new measurement session
- Returns: `{success: bool, message: string}`

### GET /api/historical_data
Retrieve historical data with optional filters
- Parameters: `year`, `month`, `date`, `device_id`
- Returns: `{success: bool, data: array}`

### GET /api/get_filters
Get available filter options
- Returns: `{success: bool, years: array, device_ids: array}`

## WebSocket Events

### Namespace: /measurement
- `connect` - Client connected
- `log_message` - Console log message
- `device_info` - Device information received
- `measurement_status` - Status update
- `measurement_complete` - Measurement finished

## Troubleshooting

### Port Already in Use
If port 5000 is already in use, modify `app.py`:
```python
socketio.run(app, debug=True, host='0.0.0.0', port=8080)  # Change port
```

### WebSocket Connection Failed
- Check firewall settings
- Ensure no proxy is blocking WebSocket connections
- Try accessing via `127.0.0.1` instead of `localhost`

### Database Locked Error
- Close any other applications accessing `sensor_db.db`
- Ensure write permissions in the application directory

### Device Not Found
- Ensure Xsens device is properly connected
- Check USB cable and port
- Verify Xsens drivers are installed
- Try disconnecting and reconnecting the device

## Command-Line Interface
The original command-line interface is still available via `main.py`:
```bash
python main.py
```

## Customization

### Changing Recording Duration
In `app.py`, modify the `run_measurement()` function:
```python
mtb_file, csv_file = recorder.record_data(duration_sec=60)  # 60 seconds
```

### Changing Server Port
In `app.py`, modify the last line:
```python
socketio.run(app, debug=True, host='0.0.0.0', port=8080)
```

### Custom Styling
Edit `static/css/style.css` to customize the appearance

## Browser Compatibility
Tested and supported on:
- Google Chrome (recommended)
- Mozilla Firefox
- Microsoft Edge
- Safari

## Security Notes
- This application is designed for local network use
- Do not expose to the public internet without proper security measures
- Consider implementing authentication for production use

## Support
For Xsens device-specific issues:
- Visit: https://www.xsens.com/
- Consult the Xsens Device API documentation

## License
This application is provided as-is for use with Xsens sensors.

## Version History
- **v2.0** - Web-based interface with Flask
- **v1.0** - Command-line interface

## Future Enhancements
- Export historical data to CSV/Excel
- Data visualization with charts
- Comparison between multiple measurements
- User authentication
- Multi-device support
- Real-time data plotting during measurement