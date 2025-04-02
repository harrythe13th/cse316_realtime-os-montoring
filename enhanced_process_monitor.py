import psutil
import time
import json
import os
import signal
import platform
import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'process-monitor-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Create templates directory if it doesn't exist
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

# Write HTML template
with open('templates/index.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Process Monitor Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.socket.io/4.6.0/socket.io.min.js"></script>
    <style>
        body {
            padding-top: 20px;
            background-color: #f8f9fa;
        }
        .card {
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card-header {
            font-weight: bold;
            background-color: #f1f3f5;
        }
        .table-responsive {
            max-height: 400px;
            overflow-y: auto;
        }
        .progress {
            height: 20px;
        }
        .chart-container {
            position: relative;
            height: 250px;
            width: 100%;
        }
        .system-metric {
            font-size: 24px;
            font-weight: bold;
        }
        .metric-label {
            font-size: 14px;
            color: #6c757d;
        }
        .high-usage {
            color: #dc3545;
        }
        .medium-usage {
            color: #fd7e14;
        }
        .low-usage {
            color: #198754;
        }
        .process-row {
            cursor: pointer;
        }
        .process-row:hover {
            background-color: rgba(0,0,0,0.05);
        }
        .action-icon {
            cursor: pointer;
            padding: 5px;
            border-radius: 4px;
        }
        .action-icon:hover {
            background-color: rgba(0,0,0,0.1);
        }
        .filter-badge {
            cursor: pointer;
            margin-right: 5px;
        }
        .filter-badge:hover {
            opacity: 0.8;
        }
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1050;
        }
        .process-details-table td {
            padding: 8px;
        }
        .process-details-table td:first-child {
            font-weight: bold;
            width: 150px;
        }
        .btn-sm-custom {
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-running {
            background-color: #198754;
        }
        .status-sleeping {
            background-color: #0dcaf0;
        }
        .status-stopped {
            background-color: #ffc107;
        }
        .status-zombie {
            background-color: #dc3545;
        }
        .status-disk-sleep {
            background-color: #6c757d;
        }
        .refresh-btn-container {
            position: relative;
            display: inline-block;
        }
        .refresh-spinner {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: none;
        }
        .refresh-btn-container.refreshing .refresh-icon {
            opacity: 0;
        }
        .refresh-btn-container.refreshing .refresh-spinner {
            display: inline-block;
        }
        .sort-icon {
            font-size: 0.7rem;
            margin-left: 5px;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1>Enhanced Process Monitor Dashboard</h1>
            <div class="d-flex gap-2">
                <div class="form-check form-switch mt-2">
                    <input class="form-check-input" type="checkbox" id="auto-refresh" checked>
                    <label class="form-check-label" for="auto-refresh">Auto Refresh</label>
                </div>
                <button id="refresh-btn" class="btn btn-outline-primary">
                    <div class="refresh-btn-container">
                        <i class="bi bi-arrow-clockwise refresh-icon"></i>
                        <div class="refresh-spinner spinner-border spinner-border-sm" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                    Refresh
                </button>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header">CPU Usage</div>
                    <div class="card-body text-center">
                        <div id="cpu-usage" class="system-metric">0%</div>
                        <div class="progress mt-2">
                            <div id="cpu-progress" class="progress-bar" role="progressbar" style="width: 0%"></div>
                        </div>
                        <div class="mt-2 metric-label">Total CPU Usage</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header">Memory Usage</div>
                    <div class="card-body text-center">
                        <div id="memory-usage" class="system-metric">0%</div>
                        <div class="progress mt-2">
                            <div id="memory-progress" class="progress-bar" role="progressbar" style="width: 0%"></div>
                        </div>
                        <div class="mt-2 metric-label"><span id="memory-used">0</span> / <span id="memory-total">0</span> GB</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header">Disk I/O</div>
                    <div class="card-body text-center">
                        <div id="disk-read" class="system-metric">0 MB/s</div>
                        <div class="mt-2 metric-label">Read</div>
                        <div id="disk-write" class="system-metric mt-2">0 MB/s</div>
                        <div class="mt-2 metric-label">Write</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header">Network</div>
                    <div class="card-body text-center">
                        <div id="net-sent" class="system-metric">0 MB/s</div>
                        <div class="mt-2 metric-label">Sent</div>
                        <div id="net-recv" class="system-metric mt-2">0 MB/s</div>
                        <div class="mt-2 metric-label">Received</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">CPU & Memory History</div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="resourceChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">I/O History</div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="ioChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <div class="row align-items-center">
                            <div class="col-md-4">
                                <h5 class="mb-0">Process List</h5>
                            </div>
                            <div class="col-md-8">
                                <div class="d-flex justify-content-end gap-2">
                                    <div class="input-group" style="max-width: 250px;">
                                        <input type="text" id="process-search" class="form-control" placeholder="Search processes...">
                                        <button class="btn btn-outline-secondary" type="button" id="clear-search">
                                            <i class="bi bi-x"></i>
                                        </button>
                                    </div>
                                    <div class="dropdown">
                                        <button class="btn btn-outline-secondary dropdown-toggle" type="button" id="filterDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                                            <i class="bi bi-funnel"></i> Filter
                                        </button>
                                        <ul class="dropdown-menu" aria-labelledby="filterDropdown">
                                            <li><h6 class="dropdown-header">Status</h6></li>
                                            <li><a class="dropdown-item filter-item" data-filter="status" data-value="all" href="#">All</a></li>
                                            <li><a class="dropdown-item filter-item" data-filter="status" data-value="running" href="#">Running</a></li>
                                            <li><a class="dropdown-item filter-item" data-filter="status" data-value="sleeping" href="#">Sleeping</a></li>
                                            <li><a class="dropdown-item filter-item" data-filter="status" data-value="stopped" href="#">Stopped</a></li>
                                            <li><a class="dropdown-item filter-item" data-filter="status" data-value="zombie" href="#">Zombie</a></li>
                                            <li><hr class="dropdown-divider"></li>
                                            <li><h6 class="dropdown-header">Resource Usage</h6></li>
                                            <li><a class="dropdown-item filter-item" data-filter="resource" data-value="high-cpu" href="#">High CPU (>10%)</a></li>
                                            <li><a class="dropdown-item filter-item" data-filter="resource" data-value="high-memory" href="#">High Memory (>10%)</a></li>
                                        </ul>
                                    </div>
                                    <div class="dropdown">
                                        <button class="btn btn-outline-secondary dropdown-toggle" type="button" id="sortDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                                            <i class="bi bi-sort-down"></i> Sort
                                        </button>
                                        <ul class="dropdown-menu" aria-labelledby="sortDropdown">
                                            <li><a class="dropdown-item sort-item" data-sort="cpu" data-order="desc" href="#">CPU Usage (High to Low)</a></li>
                                            <li><a class="dropdown-item sort-item" data-sort="cpu" data-order="asc" href="#">CPU Usage (Low to High)</a></li>
                                            <li><a class="dropdown-item sort-item" data-sort="memory" data-order="desc" href="#">Memory Usage (High to Low)</a></li>
                                            <li><a class="dropdown-item sort-item" data-sort="memory" data-order="asc" href="#">Memory Usage (Low to High)</a></li>
                                            <li><a class="dropdown-item sort-item" data-sort="pid" data-order="asc" href="#">PID (Ascending)</a></li>
                                            <li><a class="dropdown-item sort-item" data-sort="pid" data-order="desc" href="#">PID (Descending)</a></li>
                                            <li><a class="dropdown-item sort-item" data-sort="name" data-order="asc" href="#">Name (A-Z)</a></li>
                                            <li><a class="dropdown-item sort-item" data-sort="name" data-order="desc" href="#">Name (Z-A)</a></li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div id="active-filters" class="mt-2"></div>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th class="sortable" data-sort="pid">PID <span class="sort-icon"></span></th>
                                        <th class="sortable" data-sort="name">Name <span class="sort-icon"></span></th>
                                        <th class="sortable" data-sort="status">Status <span class="sort-icon"></span></th>
                                        <th class="sortable" data-sort="cpu">CPU % <span class="sort-icon"></span></th>
                                        <th class="sortable" data-sort="memory">Memory % <span class="sort-icon"></span></th>
                                        <th class="sortable" data-sort="memory_mb">Memory (MB) <span class="sort-icon"></span></th>
                                        <th class="sortable" data-sort="user">User <span class="sort-icon"></span></th>
                                        <th class="sortable" data-sort="threads">Threads <span class="sort-icon"></span></th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="process-table">
                                    <!-- Process data will be inserted here -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Process Details Modal -->
    <div class="modal fade" id="processDetailsModal" tabindex="-1" aria-labelledby="processDetailsModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="processDetailsModalLabel">Process Details</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <table class="table table-sm process-details-table">
                                <tr>
                                    <td>PID:</td>
                                    <td id="detail-pid"></td>
                                </tr>
                                <tr>
                                    <td>Name:</td>
                                    <td id="detail-name"></td>
                                </tr>
                                <tr>
                                    <td>Status:</td>
                                    <td id="detail-status"></td>
                                </tr>
                                <tr>
                                    <td>User:</td>
                                    <td id="detail-user"></td>
                                </tr>
                                <tr>
                                    <td>CPU Usage:</td>
                                    <td id="detail-cpu"></td>
                                </tr>
                                <tr>
                                    <td>Memory Usage:</td>
                                    <td id="detail-memory"></td>
                                </tr>
                                <tr>
                                    <td>Created:</td>
                                    <td id="detail-created"></td>
                                </tr>
                                <tr>
                                    <td>Threads:</td>
                                    <td id="detail-threads"></td>
                                </tr>
                            </table>
                        </div>
                        <div class="col-md-6">
                            <table class="table table-sm process-details-table">
                                <tr>
                                    <td>Parent PID:</td>
                                    <td id="detail-ppid"></td>
                                </tr>
                                <tr>
                                    <td>Nice Value:</td>
                                    <td id="detail-nice"></td>
                                </tr>
                                <tr>
                                    <td>Priority:</td>
                                    <td id="detail-priority"></td>
                                </tr>
                                <tr>
                                    <td>Terminal:</td>
                                    <td id="detail-terminal"></td>
                                </tr>
                                <tr>
                                    <td>IO Read:</td>
                                    <td id="detail-io-read"></td>
                                </tr>
                                <tr>
                                    <td>IO Write:</td>
                                    <td id="detail-io-write"></td>
                                </tr>
                                <tr>
                                    <td>CPU Time:</td>
                                    <td id="detail-cpu-times"></td>
                                </tr>
                                <tr>
                                    <td>Connections:</td>
                                    <td id="detail-connections"></td>
                                </tr>
                            </table>
                        </div>
                    </div>
                    <div class="mt-3">
                        <h6>Command Line:</h6>
                        <div class="border rounded p-2 bg-light">
                            <code id="detail-cmdline" class="text-break"></code>
                        </div>
                    </div>
                    <div class="mt-3">
                        <h6>Open Files:</h6>
                        <div class="border rounded p-2 bg-light" style="max-height: 150px; overflow-y: auto;">
                            <code id="detail-open-files" class="text-break"></code>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-warning" id="detail-suspend-btn">Suspend</button>
                    <button type="button" class="btn btn-success" id="detail-resume-btn">Resume</button>
                    <button type="button" class="btn btn-danger" id="detail-terminate-btn">Terminate</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Kill Process Confirmation Modal -->
    <div class="modal fade" id="killProcessModal" tabindex="-1" aria-labelledby="killProcessModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="killProcessModalLabel">Confirm Process Termination</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>Are you sure you want to terminate the process <strong id="kill-process-name"></strong> (PID: <span id="kill-process-pid"></span>)?</p>
                    <div class="alert alert-warning">
                        <i class="bi bi-exclamation-triangle-fill"></i> Warning: Terminating a process may cause data loss or system instability.
                    </div>
                    <div class="form-check mt-3">
                        <input class="form-check-input" type="checkbox" id="force-kill">
                        <label class="form-check-label" for="force-kill">
                            Force kill (SIGKILL) - Use only if normal termination doesn't work
                        </label>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-danger" id="confirm-kill-btn">Terminate Process</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Toast Container for Notifications -->
    <div class="toast-container"></div>
    
    <!-- Bootstrap JS Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    
    <script>
        // Connect to Socket.IO server
        const socket = io();
        
        // Global variables
        let allProcesses = [];
        let currentFilters = {
            search: '',
            status: 'all',
            resource: 'all'
        };
        let currentSort = {
            field: 'cpu',
            order: 'desc'
        };
        let selectedPid = null;
        let autoRefresh = true;
        
        // Initialize Bootstrap tooltips
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize all tooltips
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
            
            // Initialize modals
            const processDetailsModal = new bootstrap.Modal(document.getElementById('processDetailsModal'));
            const killProcessModal = new bootstrap.Modal(document.getElementById('killProcessModal'));
        });
        
        // Initialize charts
        const resourceCtx = document.getElementById('resourceChart').getContext('2d');
        const resourceChart = new Chart(resourceCtx, {
            type: 'line',
            data: {
                labels: Array(20).fill(''),
                datasets: [
                    {
                        label: 'CPU Usage %',
                        data: Array(20).fill(0),
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Memory Usage %',
                        data: Array(20).fill(0),
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Usage %'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
        
        const ioCtx = document.getElementById('ioChart').getContext('2d');
        const ioChart = new Chart(ioCtx, {
            type: 'line',
            data: {
                labels: Array(20).fill(''),
                datasets: [
                    {
                        label: 'Disk Read (MB/s)',
                        data: Array(20).fill(0),
                        borderColor: 'rgba(255, 159, 64, 1)',
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Disk Write (MB/s)',
                        data: Array(20).fill(0),
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Network Sent (MB/s)',
                        data: Array(20).fill(0),
                        borderColor: 'rgba(153, 102, 255, 1)',
                        backgroundColor: 'rgba(153, 102, 255, 0.2)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Network Received (MB/s)',
                        data: Array(20).fill(0),
                        borderColor: 'rgba(201, 203, 207, 1)',
                        backgroundColor: 'rgba(201, 203, 207, 0.2)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'MB/s'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                animation: {
                    duration: 0
                }
            }
        });
        
        // Update UI with system metrics
        socket.on('system_metrics', function(data) {
            // Update CPU usage
            document.getElementById('cpu-usage').textContent = data.cpu.toFixed(1) + '%';
            document.getElementById('cpu-progress').style.width = data.cpu + '%';
            updateMetricColor('cpu-usage', data.cpu);
            updateProgressBarColor('cpu-progress', data.cpu);
            
            // Update memory usage
            document.getElementById('memory-usage').textContent = data.memory_percent.toFixed(1) + '%';
            document.getElementById('memory-progress').style.width = data.memory_percent + '%';
            document.getElementById('memory-used').textContent = data.memory_used.toFixed(2);
            document.getElementById('memory-total').textContent = data.memory_total.toFixed(2);
            updateMetricColor('memory-usage', data.memory_percent);
            updateProgressBarColor('memory-progress', data.memory_percent);
            
            // Update disk I/O
            document.getElementById('disk-read').textContent = data.disk_read.toFixed(2) + ' MB/s';
            document.getElementById('disk-write').textContent = data.disk_write.toFixed(2) + ' MB/s';
            
            // Update network
            document.getElementById('net-sent').textContent = data.net_sent.toFixed(2) + ' MB/s';
            document.getElementById('net-recv').textContent = data.net_recv.toFixed(2) + ' MB/s';
            
            // Update charts
            const timestamp = new Date().toLocaleTimeString();
            
            // Update resource chart
            resourceChart.data.labels.shift();
            resourceChart.data.labels.push(timestamp);
            resourceChart.data.datasets[0].data.shift();
            resourceChart.data.datasets[0].data.push(data.cpu);
            resourceChart.data.datasets[1].data.shift();
            resourceChart.data.datasets[1].data.push(data.memory_percent);
            resourceChart.update();
            
            // Update I/O chart
            ioChart.data.labels.shift();
            ioChart.data.labels.push(timestamp);
            ioChart.data.datasets[0].data.shift();
            ioChart.data.datasets[0].data.push(data.disk_read);
            ioChart.data.datasets[1].data.shift();
            ioChart.data.datasets[1].data.push(data.disk_write);
            ioChart.data.datasets[2].data.shift();
            ioChart.data.datasets[2].data.push(data.net_sent);
            ioChart.data.datasets[3].data.shift();
            ioChart.data.datasets[3].data.push(data.net_recv);
            ioChart.update();
        });
        
        // Update process table
        socket.on('process_list', function(processes) {
            // Store all processes
            allProcesses = processes;
            
            // Apply filters and sort
            updateProcessTable();
            
            // Stop refresh animation if it's running
            const refreshBtn = document.getElementById('refresh-btn');
            refreshBtn.querySelector('.refresh-btn-container').classList.remove('refreshing');
        });
        
        // Process details response
        socket.on('process_details', function(details) {
            if (details.error) {
                showToast('Error', details.error, 'danger');
                return;
            }
            
            // Fill in the modal with process details
            document.getElementById('detail-pid').textContent = details.pid;
            document.getElementById('detail-name').textContent = details.name;
            document.getElementById('detail-status').textContent = details.status;
            document.getElementById('detail-user').textContent = details.username;
            document.getElementById('detail-cpu').textContent = details.cpu_percent.toFixed(2) + '%';
            document.getElementById('detail-memory').textContent = details.memory_percent.toFixed(2) + '% (' + details.memory_mb.toFixed(2) + ' MB)';
            document.getElementById('detail-created').textContent = details.create_time;
            document.getElementById('detail-threads').textContent = details.num_threads;
            document.getElementById('detail-ppid').textContent = details.ppid || 'N/A';
            document.getElementById('detail-nice').textContent = details.nice !== undefined ? details.nice : 'N/A';
            document.getElementById('detail-priority').textContent = details.priority !== undefined ? details.priority : 'N/A';
            document.getElementById('detail-terminal').textContent = details.terminal || 'N/A';
            document.getElementById('detail-io-read').textContent = details.io_read || 'N/A';
            document.getElementById('detail-io-write').textContent = details.io_write || 'N/A';
            document.getElementById('detail-cpu-times').textContent = details.cpu_times || 'N/A';
            document.getElementById('detail-connections').textContent = details.connections || '0';
            document.getElementById('detail-cmdline').textContent = details.cmdline || 'N/A';
            document.getElementById('detail-open-files').textContent = details.open_files || 'None';
            
            // Show the modal
            const processDetailsModal = new bootstrap.Modal(document.getElementById('processDetailsModal'));
            processDetailsModal.show();
            
            // Set up action buttons
            document.getElementById('detail-terminate-btn').onclick = function() {
                processDetailsModal.hide();
                showKillProcessModal(details.pid, details.name);
            };
            
            document.getElementById('detail-suspend-btn').onclick = function() {
                socket.emit('suspend_process', { pid: details.pid });
            };
            
            document.getElementById('detail-resume-btn').onclick = function() {
                socket.emit('resume_process', { pid: details.pid });
            };
        });
        
        // Process action responses
        socket.on('process_killed', function(data) {
            if (data.success) {
                showToast('Success', `Process ${data.name} (PID: ${data.pid}) has been terminated.`, 'success');
                // Request updated process list
                socket.emit('request_process_list');
            } else {
                showToast('Error', `Failed to terminate process: ${data.error}`, 'danger');
            }
        });
        
        socket.on('process_suspended', function(data) {
            if (data.success) {
                showToast('Success', `Process ${data.name} (PID: ${data.pid}) has been suspended.`, 'info');
                // Request updated process list
                socket.emit('request_process_list');
            } else {
                showToast('Error', `Failed to suspend process: ${data.error}`, 'danger');
            }
        });
        
        socket.on('process_resumed', function(data) {
            if (data.success) {
                showToast('Success', `Process ${data.name} (PID: ${data.pid}) has been resumed.`, 'success');
                // Request updated process list
                socket.emit('request_process_list');
            } else {
                showToast('Error', `Failed to resume process: ${data.error}`, 'danger');
            }
        });
        
        // Filter processes based on current filters and sort
        function updateProcessTable() {
            const filteredProcesses = allProcesses.filter(process => {
                // Apply search filter
                const searchMatch = 
                    process.name.toLowerCase().includes(currentFilters.search.toLowerCase()) || 
                    process.pid.toString().includes(currentFilters.search) ||
                    (process.username && process.username.toLowerCase().includes(currentFilters.search.toLowerCase()));
                
                // Apply status filter
                const statusMatch = currentFilters.status === 'all' || process.status === currentFilters.status;
                
                // Apply resource filter
                let resourceMatch = true;
                if (currentFilters.resource === 'high-cpu') {
                    resourceMatch = process.cpu_percent > 10;
                } else if (currentFilters.resource === 'high-memory') {
                    resourceMatch = process.memory_percent > 10;
                }
                
                return searchMatch && statusMatch && resourceMatch;
            });
            
            // Sort processes
            filteredProcesses.sort((a, b) => {
                let comparison = 0;
                
                switch (currentSort.field) {
                    case 'pid':
                        comparison = a.pid - b.pid;
                        break;
                    case 'name':
                        comparison = a.name.localeCompare(b.name);
                        break;
                    case 'status':
                        comparison = a.status.localeCompare(b.status);
                        break;
                    case 'cpu':
                        comparison = a.cpu_percent - b.cpu_percent;
                        break;
                    case 'memory':
                        comparison = a.memory_percent - b.memory_percent;
                        break;
                    case 'memory_mb':
                        comparison = a.memory_mb - b.memory_mb;
                        break;
                    case 'user':
                        comparison = (a.username || '').localeCompare(b.username || '');
                        break;
                    case 'threads':
                        comparison = a.num_threads - b.num_threads;
                        break;
                    default:
                        comparison = a.cpu_percent - b.cpu_percent;
                }
                
                return currentSort.order === 'asc' ? comparison : -comparison;
            });
            
            // Update table
            const tableBody = document.getElementById('process-table');
            tableBody.innerHTML = '';
            
            // Add rows
            filteredProcesses.forEach(process => {
                const row = document.createElement('tr');
                row.classList.add('process-row');
                row.dataset.pid = process.pid;
                
                // Get status indicator class
                const statusClass = `status-${process.status.toLowerCase()}`;
                
                row.innerHTML = `
                    <td>${process.pid}</td>
                    <td>${process.name}</td>
                    <td><span class="status-indicator ${statusClass}"></span>${process.status}</td>
                    <td>${process.cpu_percent.toFixed(1)}%</td>
                    <td>${process.memory_percent.toFixed(1)}%</td>
                    <td>${process.memory_mb.toFixed(1)}</td>
                    <td>${process.username || 'N/A'}</td>
                    <td>${process.num_threads}</td>
                    <td>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-outline-info view-process" data-pid="${process.pid}" title="View Details">
                                <i class="bi bi-info-circle"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger kill-process" data-pid="${process.pid}" data-name="${process.name}" title="Terminate Process">
                                <i class="bi bi-x-circle"></i>
                            </button>
                        </div>
                    </td>
                `;
                
                tableBody.appendChild(row);
            });
            
            // Update event listeners for process actions
            document.querySelectorAll('.view-process').forEach(button => {
                button.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const pid = parseInt(this.dataset.pid);
                    socket.emit('get_process_details', { pid: pid });
                });
            });
            
            document.querySelectorAll('.kill-process').forEach(button => {
                button.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const pid = parseInt(this.dataset.pid);
                    const name = this.dataset.name;
                    showKillProcessModal(pid, name);
                });
            });
            
            // Add click event to rows for process details
            document.querySelectorAll('.process-row').forEach(row => {
                row.addEventListener('click', function() {
                    const pid = parseInt(this.dataset.pid);
                    socket.emit('get_process_details', { pid: pid });
                });
            });
            
            // Update sort icons
            document.querySelectorAll('.sortable').forEach(th => {
                const sortIcon = th.querySelector('.sort-icon');
                sortIcon.innerHTML = '';
                
                if (th.dataset.sort === currentSort.field) {
                    sortIcon.innerHTML = currentSort.order === 'asc' ? 
                        '<i class="bi bi-caret-up-fill"></i>' : 
                        '<i class="bi bi-caret-down-fill"></i>';
                }
            });
            
            // Update active filters display
            updateActiveFiltersDisplay();
        }
        
        // Show kill process confirmation modal
        function showKillProcessModal(pid, name) {
            document.getElementById('kill-process-pid').textContent = pid;
            document.getElementById('kill-process-name').textContent = name;
            document.getElementById('force-kill').checked = false;
            
            const killProcessModal = new bootstrap.Modal(document.getElementById('killProcessModal'));
            killProcessModal.show();
            
            // Set up confirm button
            document.getElementById('confirm-kill-btn').onclick = function() {
                const forceKill = document.getElementById('force-kill').checked;
                socket.emit('kill_process', { 
                    pid: pid,
                    force: forceKill
                });
                killProcessModal.hide();
            };
        }
        
        // Update active filters display
        function updateActiveFiltersDisplay() {
            const container = document.getElementById('active-filters');
            container.innerHTML = '';
            
            // Add search filter if present
            if (currentFilters.search) {
                const badge = document.createElement('span');
                badge.classList.add('badge', 'bg-primary', 'filter-badge');
                badge.innerHTML = `Search: ${currentFilters.search} <i class="bi bi-x"></i>`;
                badge.addEventListener('click', function() {
                    document.getElementById('process-search').value = '';
                    currentFilters.search = '';
                    updateProcessTable();
                });
                container.appendChild(badge);
            }
            
            // Add status filter if not 'all'
            if (currentFilters.status !== 'all') {
                const badge = document.createElement('span');
                badge.classList.add('badge', 'bg-info', 'filter-badge');
                badge.innerHTML = `Status: ${currentFilters.status} <i class="bi bi-x"></i>`;
                badge.addEventListener('click', function() {
                    currentFilters.status = 'all';
                    updateProcessTable();
                });
                container.appendChild(badge);
            }
            
            // Add resource filter if not 'all'
            if (currentFilters.resource !== 'all') {
                const badge = document.createElement('span');
                badge.classList.add('badge', 'bg-warning', 'text-dark', 'filter-badge');
                const label = currentFilters.resource === 'high-cpu' ? 'High CPU' : 'High Memory';
                badge.innerHTML = `${label} <i class="bi bi-x"></i>`;
                badge.addEventListener('click', function() {
                    currentFilters.resource = 'all';
                    updateProcessTable();
                });
                container.appendChild(badge);
            }
        }
        
        // Show toast notification
        function showToast(title, message, type) {
            const toastContainer = document.querySelector('.toast-container');
            
            const toastEl = document.createElement('div');
            toastEl.classList.add('toast', 'show');
            toastEl.setAttribute('role', 'alert');
            toastEl.setAttribute('aria-live', 'assertive');
            toastEl.setAttribute('aria-atomic', 'true');
            
            const iconClass = type === 'success' ? 'bi-check-circle-fill' :
                             type === 'danger' ? 'bi-exclamation-circle-fill' :
                             type === 'warning' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill';
            
            toastEl.innerHTML = `
                <div class="toast-header bg-${type} text-white">
                    <i class="bi ${iconClass} me-2"></i>
                    <strong class="me-auto">${title}</strong>
                    <small>just now</small>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            `;
            
            toastContainer.appendChild(toastEl);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                toastEl.remove();
            }, 5000);
            
            // Add close button functionality
            toastEl.querySelector('.btn-close').addEventListener('click', function() {
                toastEl.remove();
            });
        }
        
        // Helper functions
        function updateMetricColor(elementId, value) {
            const element = document.getElementById(elementId);
            element.classList.remove('high-usage', 'medium-usage', 'low-usage');
            
            if (value >= 80) {
                element.classList.add('high-usage');
            } else if (value >= 50) {
                element.classList.add('medium-usage');
            } else {
                element.classList.add('low-usage');
            }
        }
        
        function updateProgressBarColor(elementId, value) {
            const element = document.getElementById(elementId);
            element.classList.remove('bg-danger', 'bg-warning', 'bg-success', 'bg-info');
            
            if (value >= 80) {
                element.classList.add('bg-danger');
            } else if (value >= 50) {
                element.classList.add('bg-warning');
            } else if (value >= 20) {
                element.classList.add('bg-success');
            } else {
                element.classList.add('bg-info');
            }
        }
        
        // Event Listeners
        document.addEventListener('DOMContentLoaded', function() {
            // Process search
            document.getElementById('process-search').addEventListener('input', function() {
                currentFilters.search = this.value;
                updateProcessTable();
            });
            
            // Clear search button
            document.getElementById('clear-search').addEventListener('click', function() {
                document.getElementById('process-search').value = '';
                currentFilters.search = '';
                updateProcessTable();
            });
            
            // Filter dropdown items
            document.querySelectorAll('.filter-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    const filterType = this.dataset.filter;
                    const filterValue = this.dataset.value;
                    
                    if (filterType === 'status') {
                        currentFilters.status = filterValue;
                    } else if (filterType === 'resource') {
                        currentFilters.resource = filterValue;
                    }
                    
                    updateProcessTable();
                });
            });
            
            // Sort dropdown items
            document.querySelectorAll('.sort-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    currentSort.field = this.dataset.sort;
                    currentSort.order = this.dataset.order;
                    updateProcessTable();
                });
            });
            
            // Table header sorting
            document.querySelectorAll('.sortable').forEach(th => {
                th.addEventListener('click', function() {
                    const field = this.dataset.sort;
                    
                    if (currentSort.field === field) {
                        // Toggle order if same field
                        currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
                    } else {
                        // New field, default to descending for most fields
                        currentSort.field = field;
                        currentSort.order = field === 'name' ? 'asc' : 'desc';
                    }
                    
                    updateProcessTable();
                });
            });
            
            // Auto-refresh toggle
            document.getElementById('auto-refresh').addEventListener('change', function() {
                autoRefresh = this.checked;
                if (autoRefresh) {
                    socket.emit('set_auto_refresh', { enabled: true });
                } else {
                    socket.emit('set_auto_refresh', { enabled: false });
                }
            });
            
            // Manual refresh button
            document.getElementById('refresh-btn').addEventListener('click', function() {
                this.querySelector('.refresh-btn-container').classList.add('refreshing');
                socket.emit('request_process_list');
            });
        });
    </script>
</body>
</html>
    ''')

# Global variables to store previous I/O counters
prev_disk_io = psutil.disk_io_counters()
prev_net_io = psutil.net_io_counters()
prev_time = time.time()
auto_refresh_enabled = True

def get_system_metrics():
    """Collect system metrics"""
    global prev_disk_io, prev_net_io, prev_time
    
    current_time = time.time()
    time_delta = current_time - prev_time
    
    # CPU usage
    cpu_percent = psutil.cpu_percent()
    
    # Memory usage
    memory = psutil.virtual_memory()
    memory_total = memory.total / (1024 ** 3)  # GB
    memory_used = memory.used / (1024 ** 3)    # GB
    memory_percent = memory.percent
    
    # Disk I/O
    current_disk_io = psutil.disk_io_counters()
    disk_read = (current_disk_io.read_bytes - prev_disk_io.read_bytes) / (1024 ** 2) / time_delta  # MB/s
    disk_write = (current_disk_io.write_bytes - prev_disk_io.write_bytes) / (1024 ** 2) / time_delta  # MB/s
    prev_disk_io = current_disk_io
    
    # Network I/O
    current_net_io = psutil.net_io_counters()
    net_sent = (current_net_io.bytes_sent - prev_net_io.bytes_sent) / (1024 ** 2) / time_delta  # MB/s
    net_recv = (current_net_io.bytes_recv - prev_net_io.bytes_recv) / (1024 ** 2) / time_delta  # MB/s
    prev_net_io = current_net_io
    
    prev_time = current_time
    
    return {
        'cpu': cpu_percent,
        'memory_percent': memory_percent,
        'memory_total': memory_total,
        'memory_used': memory_used,
        'disk_read': disk_read,
        'disk_write': disk_write,
        'net_sent': net_sent,
        'net_recv': net_recv
    }

def get_process_list():
    """Get list of running processes with details"""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'username', 'status', 'cpu_percent', 'memory_percent', 'memory_info', 'num_threads', 'create_time']):
        try:
            # Get process info
            proc_info = proc.info
            
            # Convert create time to readable format
            create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(proc_info['create_time']))
            
            # Calculate memory in MB
            memory_mb = proc_info['memory_info'].rss / (1024 * 1024) if proc_info['memory_info'] else 0
            
            processes.append({
                'pid': proc_info['pid'],
                'name': proc_info['name'],
                'status': proc_info['status'],
                'cpu_percent': proc_info['cpu_percent'],
                'memory_percent': proc_info['memory_percent'],
                'memory_mb': memory_mb,
                'num_threads': proc_info['num_threads'],
                'create_time': create_time,
                'username': proc_info['username']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Sort by CPU usage (descending)
    processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
    
    return processes

def get_process_details(pid):
    """Get detailed information about a specific process"""
    try:
        proc = psutil.Process(pid)
        
        # Basic info
        info = proc.as_dict(attrs=[
            'pid', 'name', 'status', 'username', 'cpu_percent', 
            'memory_percent', 'memory_info', 'num_threads', 'create_time',
            'nice', 'ppid', 'cwd', 'exe', 'cmdline', 'terminal'
        ])
        
        # Convert create time to readable format
        info['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(info['create_time']))
        
        # Calculate memory in MB
        info['memory_mb'] = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
        
        # Additional info
        try:
            info['cpu_times'] = f"User: {proc.cpu_times().user:.2f}s, System: {proc.cpu_times().system:.2f}s"
        except:
            info['cpu_times'] = "N/A"
            
        try:
            io_counters = proc.io_counters()
            info['io_read'] = f"{io_counters.read_bytes / (1024 * 1024):.2f} MB"
            info['io_write'] = f"{io_counters.write_bytes / (1024 * 1024):.2f} MB"
        except:
            info['io_read'] = "N/A"
            info['io_write'] = "N/A"
            
        try:
            connections = proc.connections()
            info['connections'] = str(len(connections))
        except:
            info['connections'] = "N/A"
            
        try:
            open_files = proc.open_files()
            if open_files:
                info['open_files'] = "\n".join([f.path for f in open_files[:10]])
                if len(open_files) > 10:
                    info['open_files'] += f"\n... and {len(open_files) - 10} more"
            else:
                info['open_files'] = "None"
        except:
            info['open_files'] = "N/A"
            
        # Convert cmdline list to string
        if info['cmdline']:
            info['cmdline'] = " ".join(info['cmdline'])
        else:
            info['cmdline'] = "N/A"
            
        return info
        
    except psutil.NoSuchProcess:
        return {"error": "Process no longer exists"}
    except psutil.AccessDenied:
        return {"error": "Access denied to process information"}
    except Exception as e:
        return {"error": f"Error retrieving process details: {str(e)}"}

def kill_process(pid, force=False):
    """Kill a process by PID"""
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        
        if force:
            proc.kill()  # SIGKILL
        else:
            proc.terminate()  # SIGTERM
            
        # Wait briefly to see if the process is gone
        gone, still_alive = psutil.wait_procs([proc], timeout=1)
        if still_alive:
            # If still alive and force was requested, kill it
            if force:
                return {"success": False, "error": "Process could not be terminated even with SIGKILL", "pid": pid, "name": proc_name}
            else:
                return {"success": False, "error": "Process did not terminate gracefully. Try force kill.", "pid": pid, "name": proc_name}
                
        return {"success": True, "pid": pid, "name": proc_name}
        
    except psutil.NoSuchProcess:
        return {"success": False, "error": "Process no longer exists", "pid": pid}
    except psutil.AccessDenied:
        return {"success": False, "error": "Access denied. You may need elevated privileges.", "pid": pid}
    except Exception as e:
        return {"success": False, "error": f"Error killing process: {str(e)}", "pid": pid}

def suspend_process(pid):
    """Suspend a process by PID"""
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        
        proc.suspend()
        return {"success": True, "pid": pid, "name": proc_name}
        
    except psutil.NoSuchProcess:
        return {"success": False, "error": "Process no longer exists", "pid": pid}
    except psutil.AccessDenied:
        return {"success": False, "error": "Access denied. You may need elevated privileges.", "pid": pid}
    except Exception as e:
        return {"success": False, "error": f"Error suspending process: {str(e)}", "pid": pid}

def resume_process(pid):
    """Resume a suspended process by PID"""
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
        
        proc.resume()
        return {"success": True, "pid": pid, "name": proc_name}
        
    except psutil.NoSuchProcess:
        return {"success": False, "error": "Process no longer exists", "pid": pid}
    except psutil.AccessDenied:
        return {"success": False, "error": "Access denied. You may need elevated privileges.", "pid": pid}
    except Exception as e:
        return {"success": False, "error": f"Error resuming process: {str(e)}", "pid": pid}

def background_task():
    """Background task to emit metrics periodically"""
    global auto_refresh_enabled
    
    while True:
        try:
            # Get system metrics
            metrics = get_system_metrics()
            socketio.emit('system_metrics', metrics)
            
            # Get process list if auto-refresh is enabled
            if auto_refresh_enabled:
                processes = get_process_list()
                socketio.emit('process_list', processes)
            
            # Sleep for 2 seconds
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error in background task: {e}")
            time.sleep(5)  # Wait a bit longer if there's an error

@app.route('/')
def index():
    """Serve the dashboard page"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    
    # Send initial data
    socketio.emit('system_metrics', get_system_metrics())
    socketio.emit('process_list', get_process_list())

@socketio.on('request_process_list')
def handle_request_process_list():
    """Handle request for process list"""
    socketio.emit('process_list', get_process_list())

@socketio.on('get_process_details')
def handle_get_process_details(data):
    """Handle request for process details"""
    pid = data.get('pid')
    if pid:
        details = get_process_details(pid)
        socketio.emit('process_details', details)

@socketio.on('kill_process')
def handle_kill_process(data):
    """Handle request to kill a process"""
    pid = data.get('pid')
    force = data.get('force', False)
    
    if pid:
        result = kill_process(pid, force)
        socketio.emit('process_killed', result)

@socketio.on('suspend_process')
def handle_suspend_process(data):
    """Handle request to suspend a process"""
    pid = data.get('pid')
    
    if pid:
        result = suspend_process(pid)
        socketio.emit('process_suspended', result)

@socketio.on('resume_process')
def handle_resume_process(data):
    """Handle request to resume a process"""
    pid = data.get('pid')
    
    if pid:
        result = resume_process(pid)
        socketio.emit('process_resumed', result)

@socketio.on('set_auto_refresh')
def handle_set_auto_refresh(data):
    """Handle setting auto-refresh state"""
    global auto_refresh_enabled
    auto_refresh_enabled = data.get('enabled', True)

if __name__ == '__main__':
    # Start background task
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()
    
    # Start the server
    logger.info("Starting Enhanced Process Monitor Dashboard on http://localhost:9999")
    socketio.run(app, host='0.0.0.0', port=9999, debug=False)

# Run this script with: python enhanced_process_monitor.py
print("Enhanced Process Monitor Dashboard is running at http://localhost:9999")