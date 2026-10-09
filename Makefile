.PHONY: help run-ai simulate manual test install

PYTHON ?= python3

help:
	@echo "=========================================================="
	@echo " TerraCortex IoT — Developer Commands"
	@echo "=========================================================="
	@echo " make run-ai    : Run AI Edge Pipeline (ONNX model inference)"
	@echo " make manual    : Run interactive manual sensor control (NO RANDOM)"
	@echo " make simulate  : Run continuous excavator sensor telemetry"
	@echo " make test      : Run JSON format & contract test suite"
	@echo " make install   : Install required Python dependencies"
	@echo "=========================================================="

run-ai:
	@echo ">> Starting TerraCortex AI Cortex Pipeline..."
	$(PYTHON) -u run_ai_pipeline.py

manual:
	@echo ">> Starting Interactive Manual Sensor Controller..."
	$(PYTHON) -u simulator.py --manual

simulate:
	@echo ">> Starting Excavator IoT Sensor Simulator..."
	$(PYTHON) -u simulator.py

test:
	@echo ">> Running JSON Schema & AI Contract Validation..."
	$(PYTHON) test_json_format.py

install:
	@echo ">> Installing IoT dependencies..."
	$(PYTHON) -m pip install numpy onnxruntime paho-mqtt
