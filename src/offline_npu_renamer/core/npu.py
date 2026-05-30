from __future__ import annotations

from collections.abc import Sequence

from offline_npu_renamer.core.models import NpuStatus

SUPPORTED_NPU_PROVIDERS = (
    "QNNExecutionProvider",
    "OpenVINOExecutionProvider",
    "VitisAIExecutionProvider",
)


def get_onnxruntime_providers() -> tuple[str, ...]:
    import onnxruntime as ort

    return tuple(ort.get_available_providers())


def detect_npu_status(
    available_providers: Sequence[str] | None = None,
) -> NpuStatus:
    providers = tuple(available_providers or get_onnxruntime_providers())
    if "QNNExecutionProvider" in providers:
        return NpuStatus(
            available=True,
            provider="QNNExecutionProvider",
            message="NPU-backed provider available: QNNExecutionProvider",
            available_providers=providers,
            provider_options=({"backend_type": "htp"},),
        )
    if "OpenVINOExecutionProvider" in providers:
        return NpuStatus(
            available=True,
            provider="OpenVINOExecutionProvider",
            message="NPU-backed provider available: OpenVINOExecutionProvider",
            available_providers=providers,
            provider_options=({"device_type": "NPU"},),
        )
    if "VitisAIExecutionProvider" in providers:
        return NpuStatus(
            available=True,
            provider="VitisAIExecutionProvider",
            message="NPU-backed provider available: VitisAIExecutionProvider",
            available_providers=providers,
        )

    return NpuStatus(
        available=False,
        provider=None,
        message=(
            "No supported NPU-backed ONNX Runtime provider was found. "
            "Analysis is disabled to avoid CPU/GPU AI fallback."
        ),
        available_providers=providers,
    )
