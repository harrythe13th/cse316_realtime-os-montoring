# Real Time Process Monitoring Dashboard

# **Project Overview**

## **Goals**
The **Resource Monitoring Dashboard** aims to provide real-time insights into system resource usage. It helps users monitor CPU, memory, disk, and network performance efficiently through a user-friendly interface.

## **Expected Outcomes**
* A dashboard displaying real-time system metrics.
* Search and filter functionalities to analyze resource usage trends.
* The ability to terminate resource-intensive processes directly from the dashboard.

## **Scope**
* **Monitoring**: Tracks CPU, RAM, disk, and network usage.
* **Data Visualization**: Presents metrics in an understandable format using graphs and charts.
* **Process Control**: Enables users to find and terminate resource-heavy processes.

# Installation and Usage
## Local Setup

You need to have Python(>=3.12) installed on your system.
```
#For Debian based
sudo apt install python3 -y

$ python --version
Python 3.13.1
```

Clone this repo.
```
git clone https://github.com/harrythe13th/cse316_realtime-os-montoring && cd cse316_realtime-os-montoring
```

Create a venv for the dependencies.
```
python -m venv venv
```

Activate the venv.
```
source venv/bin/activate
```

Install the dependencies.
```
pip install -r requirements.txt
```

Start monitor.
```
python3 enhanced_process_monitor.py
```

## Usage
### Web Mode
The WebUI will be available at port 9999 accessible from your browser as:
```
localhost:9999
```

# **Features**

## **Data Collection & Processing**

✅ **Real-time monitoring**: Fetch CPU, memory, disk, and network usage every second.

✅ **Process monitoring**: Display running processes with resource consumption.

✅ **Historical data storage**: Save previous logs for trend analysis.

## **User Interface & Data Visualization**

✅ **Live graphs & charts**: Real-time plots for CPU, RAM, and network usage.

✅ **Resource breakdown**: Show system-wide and per-process resource usage.

✅ **Dark & light theme support**: User preference-based UI.

## **Search, Filter & Process Control**

✅ **Search & filter**: Find processes by name, PID, or high resource usage.

✅ **Sort processes**: Arrange by CPU, memory, or disk usage.

✅ **Terminate processes**: Kill selected processes from the dashboard.
