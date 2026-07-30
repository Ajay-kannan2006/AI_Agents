"""Explainable compatibility scoring plus an optional free-tier Groq insight."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from device_database import EdgeDevice, get_device, list_device_names

load_dotenv()
logger = logging.getLogger(__name__)


class Check(BaseModel):
    name: str
    passed: bool
    detail: str
    weight: int


class CompatibilityResult(BaseModel):
    device: str
    model_name: str
    compatibility_score: int = Field(ge=0, le=100)
    verdict: str
    checks: list[Check]
    recommendations: list[str]
    ai_insight: str | None = None


class CompatibilityAgent:
    """Stateless evaluator. Core scoring never depends on an external LLM."""

    def evaluate(self, request: dict[str, Any]) -> CompatibilityResult:
        device = get_device(str(request["edge_device"]))
        if device is None:
            supported = ", ".join(list_device_names())
            raise ValueError(f"Unknown edge device '{request['edge_device']}'. Supported devices: {supported}.")

        framework = str(request["framework"]).casefold()
        architecture = str(request["architecture"]).casefold()
        ram = float(request["required_ram_gb"])
        storage = float(request["required_storage_gb"])
        model_size = float(request["model_size_mb"])

        checks = [
            self._check("Framework compatibility", framework in device.frameworks, f"{request['framework']} is {'supported' if framework in device.frameworks else 'not listed as supported'} on {device.name}.", 25),
            self._check("RAM", ram <= device.ram_gb, f"Requires {ram:g} GB; device provides {device.ram_gb:g} GB.", 25),
            self._check("Storage", storage <= device.storage_gb, f"Requires {storage:g} GB; device provides {device.storage_gb:g} GB.", 15),
            self._check("CPU architecture", architecture in device.architectures, f"Requested {request['architecture']}; device supports {', '.join(device.architectures)}.", 15),
            self._check("Runtime support", self._runtime_supported(framework, device), f"Available runtimes: {', '.join(device.runtimes)}.", 10),
            self._check("Accelerator support", self._accelerator_supported(framework, device), f"Available accelerators: {', '.join(device.accelerators)}.", 10),
        ]
        score = sum(check.weight for check in checks if check.passed)
        recommendations = self._recommendations(checks, device, framework, ram, storage, model_size)
        verdict = "Compatible" if score >= 80 else "Compatible with constraints" if score >= 50 else "Not recommended"
        result = CompatibilityResult(device=device.name, model_name=str(request["model_name"]), compatibility_score=score, verdict=verdict, checks=checks, recommendations=recommendations)
        result.ai_insight = self._groq_insight(result)
        return result

    @staticmethod
    def _check(name: str, passed: bool, detail: str, weight: int) -> Check:
        return Check(name=name, passed=passed, detail=detail, weight=weight)

    @staticmethod
    def _runtime_supported(framework: str, device: EdgeDevice) -> bool:
        aliases = {"tensorflow lite": "tflite", "tensorflow": "tensorflow", "onnx": "onnx runtime", "pytorch": "pytorch", "openvino": "openvino", "tensorrt": "tensorrt"}
        return aliases.get(framework, framework) in device.runtimes

    @staticmethod
    def _accelerator_supported(framework: str, device: EdgeDevice) -> bool:
        if framework == "tensorrt":
            return "tensorrt" in device.accelerators
        if framework == "openvino":
            return "openvino" in device.accelerators
        if framework == "tensorflow lite" and "google edgetpu" in device.accelerators:
            return True
        return bool(device.accelerators)

    @staticmethod
    def _recommendations(checks: list[Check], device: EdgeDevice, framework: str, ram: float, storage: float, model_size: float) -> list[str]:
        advice = [f"Model artifact size is {model_size:g} MB; reserve space for its runtime, dependencies, and updates."]
        failures = {check.name for check in checks if not check.passed}
        if "Framework compatibility" in failures or "Runtime support" in failures:
            advice.append("Export or convert the model to a device-supported format, such as TensorFlow Lite, ONNX, TensorRT, or OpenVINO where applicable.")
        if "RAM" in failures:
            advice.append("Use quantization, reduce batch size to 1, or select a device with more RAM.")
        elif ram > device.ram_gb * 0.75:
            advice.append("RAM headroom is limited; benchmark peak inference memory under the target workload.")
        if "Storage" in failures:
            advice.append("Increase persistent storage or reduce model and runtime footprint.")
        if "CPU architecture" in failures:
            advice.append("Build or obtain an artifact for the device's native architecture before deployment.")
        if "Accelerator support" in failures:
            advice.append("Use CPU inference or choose a framework optimized for the available accelerator.")
        if framework == "tensorflow lite" and "google edgetpu" in device.accelerators:
            advice.append("Compile the TensorFlow Lite model with the Edge TPU Compiler for Coral acceleration.")
        return advice

    @staticmethod
    def _groq_insight(result: CompatibilityResult) -> str | None:
        """Use Groq only for an optional concise deployment note; never send secrets."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            payload = json.dumps({"device": result.device, "score": result.compatibility_score, "verdict": result.verdict, "recommendations": result.recommendations})
            response = client.chat.completions.create(model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), messages=[{"role": "system", "content": "You are an edge AI deployment expert. Return one practical sentence only."}, {"role": "user", "content": payload}], temperature=0.2, max_tokens=80)
            return response.choices[0].message.content or None
        except Exception as exc:  # Network/model quota failures must not break scoring.
            logger.warning("Optional Groq insight unavailable: %s", exc)
            return None
