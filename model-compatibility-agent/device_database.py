"""Built-in, deliberately conservative database of common edge devices."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EdgeDevice:
    name: str
    ram_gb: float
    storage_gb: float
    architectures: tuple[str, ...]
    frameworks: tuple[str, ...]
    runtimes: tuple[str, ...]
    accelerators: tuple[str, ...]


EDGE_DEVICES: dict[str, EdgeDevice] = {
    "raspberry pi 5": EdgeDevice("Raspberry Pi 5", 8, 32, ("arm64", "aarch64"), ("tensorflow lite", "onnx", "pytorch", "openvino"), ("tflite", "onnx runtime", "pytorch", "openvino"), ("cpu", "videocore vii gpu")),
    "nvidia jetson orin nano": EdgeDevice("NVIDIA Jetson Orin Nano", 8, 64, ("arm64", "aarch64"), ("tensorflow", "tensorflow lite", "onnx", "pytorch", "tensorrt"), ("tensorrt", "onnx runtime", "pytorch", "tensorflow"), ("nvidia gpu", "cuda", "tensorrt")),
    "nvidia jetson xavier nx": EdgeDevice("NVIDIA Jetson Xavier NX", 8, 16, ("arm64", "aarch64"), ("tensorflow", "tensorflow lite", "onnx", "pytorch", "tensorrt"), ("tensorrt", "onnx runtime", "pytorch", "tensorflow"), ("nvidia gpu", "cuda", "tensorrt")),
    "intel nuc": EdgeDevice("Intel NUC", 16, 256, ("x86_64", "amd64", "x86"), ("tensorflow", "tensorflow lite", "onnx", "pytorch", "openvino"), ("openvino", "onnx runtime", "pytorch", "tensorflow", "tflite"), ("cpu", "intel gpu", "openvino")),
    "google coral dev board": EdgeDevice("Google Coral Dev Board", 1, 8, ("arm64", "aarch64"), ("tensorflow lite",), ("tflite", "edgetpu runtime"), ("google edgetpu",)),
}


def get_device(name: str) -> EdgeDevice | None:
    return EDGE_DEVICES.get(name.strip().casefold())


def list_device_names() -> list[str]:
    return [device.name for device in EDGE_DEVICES.values()]
