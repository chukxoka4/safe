#!/bin/bash
set -e

# Generate large PDF for stress test
python tests/performance/generate_large_pdf.py

# Start resource monitoring in background
python tests/performance/monitor_resources.py > tests/performance/resource_usage.csv &

MONITOR_PID=$!

# Run Locust with 20 users for normal test
locust -f tests/performance/locust_suite.py --headless -u 20 -r 5 --run-time 2m --host=http://127.0.0.1:5000/ --html tests/performance/report_20_users.html

# Stress test: 50 users, large PDF
locust -f tests/performance/locust_suite.py --headless -u 50 -r 10 --run-time 2m --host=http://127.0.0.1:5000/ --html tests/performance/report_50_users.html

# Kill resource monitor
kill $MONITOR_PID

echo "Performance tests complete. See HTML reports and resource_usage.csv in tests/performance/"