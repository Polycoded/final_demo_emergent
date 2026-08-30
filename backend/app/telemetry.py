import csv
import io
import subprocess
from dataclasses import dataclass


@dataclass
class GpuTelemetry:
    available: bool
    utilization_percent: float | None = None
    memory_used_mb: float | None = None
    memory_total_mb: float | None = None
    source: str = "unavailable"


def read_nvidia_gpu() -> GpuTelemetry:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        row = next(csv.reader(io.StringIO(result.stdout)))
        return GpuTelemetry(True, float(row[0]), float(row[1]), float(row[2]), "nvidia-smi")
    except (FileNotFoundError, subprocess.SubprocessError, StopIteration, ValueError):
        return GpuTelemetry(False)
