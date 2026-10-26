import psutil
import logging
import platform
import shutil

# Configure logging
logger = logging.getLogger(__name__)

# Try to import PyNVML
try:
    import pynvml

    pynvml.nvmlInit()
    HAS_NVML = True
    logger.info("NVIDIA Management Library (NVML) initialized.")
except Exception as e:
    HAS_NVML = False
    logger.warning(f"NVML not available: {e}. Falling back to standard sensors.")


def get_ram_gb():
    """Returns total system RAM in gigabytes."""
    try:
        return psutil.virtual_memory().total / (1024**3)
    except Exception as e:
        logger.error(f"Could not determine RAM: {e}")
        return 0


def get_cpu_temp():
    """Attempts to get CPU temperature via psutil sensors."""
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None

        # Common keys for CPU temp on Linux
        for name in ["coretemp", "cpu_thermal", "k10temp"]:
            if name in temps:
                for entry in temps[name]:
                    if entry.current > 0:
                        return entry.current

        # Fallback: grab first available positive temp
        for name, entries in temps.items():
            for entry in entries:
                if entry.current > 0:
                    return entry.current
    except Exception as e:
        logger.debug(f"Could not read CPU temp sensors: {e}")
    return None


def get_gpu_info():
    """
    Detects GPU presence and VRAM using a hierarchical strategy.
    Returns (gpu_type, vram_gb).
    """
    # 1. Try NVML (Robust)
    if HAS_NVML:
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            if device_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                return "nvidia", mem_info.total / (1024**3)
        except Exception as e:
            logger.error(f"NVML runtime error: {e}")

    # 2. Try nvidia-smi (Fallback CLI)
    if shutil.which("nvidia-smi"):
        try:
            import subprocess

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                vram_mb = int(result.stdout.strip())
                return "nvidia", vram_mb / 1024
        except Exception as e:
            logger.debug(f"nvidia-smi check failed: {e}")

    # 3. Try AMD (rocm-smi)
    if shutil.which("rocm-smi"):
        try:
            import subprocess

            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram"], capture_output=True, text=True
            )
            if "VRAM Total Memory" in result.stdout:
                return (
                    "amd",
                    8.0,
                )  # Placeholder/parsing logic simplification for resilience
        except Exception as e:
            logger.debug(f"rocm-smi check failed: {e}")

    # 4. Intel/Integrated
    return "integrated", 0


def get_system_metrics() -> dict:
    """Returns a dictionary of current system health for PID controller."""
    metrics = {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": psutil.virtual_memory().percent,
        "temperature": get_cpu_temp() or 0.0,
        "gpu_load": 0.0,
    }

    if HAS_NVML:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            metrics["gpu_load"] = util.gpu
            # Prefer GPU temp if available as it's the bottleneck for LLMs
            gpu_temp = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )
            if gpu_temp > 0:
                metrics["temperature"] = gpu_temp
        except Exception as e:
            logger.debug(f"NVML utilization read failed: {e}")

    return metrics


def determine_tier():
    """
    Determines the operational tier based on available hardware.
    """
    try:
        ram_gb = get_ram_gb()
        gpu_type, vram_gb = get_gpu_info()

        logger.info(
            f"Hardware Detected: RAM={ram_gb:.2f}GB, GPU={gpu_type}, VRAM={vram_gb:.2f}GB"
        )

        # Tier 3: Strong GPU
        if gpu_type in ["nvidia", "amd"] and vram_gb >= 6:
            return 3, "GPU-Accelerated AI Mode (High Performance)"

        # Tier 2+: Low VRAM GPU
        if gpu_type in ["nvidia", "amd"] and vram_gb >= 4:
            return 3, "GPU-Accelerated AI Mode (Standard)"

        # Tier 2: No Discrete GPU but decent RAM (CPU Inference possible)
        if ram_gb >= 12:
            return 2, "Lightweight AI Mode (CPU)"

        # Tier 1: Rules only
        return 1, "Rules-Only Mode (Low Spec)"

    except Exception as e:
        logger.error(f"Hardware detection failed: {e}")
        return 1, "Rules-Only Mode (Fallback)"
