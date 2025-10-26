#!/bin/bash
# Launch Jupyter Notebook

echo "🚀 Launching Jupyter Notebook..."
echo ""
echo "The notebook will open in your browser at: http://localhost:8888"
echo ""
echo "To stop the notebook server, press Ctrl+C"
echo ""
echo "Opening interactive_demo.ipynb..."
echo ""

cd "$(dirname "$0")"
./venv/bin/jupyter notebook interactive_demo.ipynb
