.PHONY: help run-ai simulate test install

PYTHON ?= python3

help:
	@echo "=========================================================="
	@echo " TerraCortex IoT — Developer Commands"
	@echo "=========================================================="
	@echo " make run-ai    : Run AI Edge Pipeline (ONNX model inference)"
	@echo " make simulate  : Run simulated excavator sensor telemetry"
	@echo " make test      : Run JSON format & contract test suite"
	@echo " make install   : Install required Python dependencies"
	@echo "=========================================================="

run-ai:
	@echo ">> Starting TerraCortex AI Cortex Pipeline..."
	$(PYTHON) -u run_ai_pipeline.py

simulate:
	@echo ">> Starting Excavator IoT Sensor Simulator..."
	$(PYTHON) -u simulator.py

test:
	@echo ">> Running JSON Schema & AI Contract Validation..."
	$(PYTHON) test_json_format.py

install:
	@echo ">> Installing IoT dependencies..."
	$(PYTHON) -m pip install numpy onnxruntime paho-mqtt
