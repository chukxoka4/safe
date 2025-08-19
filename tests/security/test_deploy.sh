
#!/bin/bash
echo "Simulating deployment..."
pytest ../unit
pytest ../integration
