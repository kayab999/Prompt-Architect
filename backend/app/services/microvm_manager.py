import subprocess
import os
import time
import requests_unixsocket
import json
import logging
import struct
import requests
import asyncio
import sys # Added import
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import tempfile

logger = logging.getLogger(__name__)

class MicroVMLauncher:
    """Manages the lifecycle of a single Firecracker MicroVM."""

    def __init__(self, vm_id: str, kernel_path: Path, rootfs_path: Path):
        self.vm_id = vm_id
        self.kernel_path = kernel_path
        self.rootfs_path = rootfs_path
        self.api_socket_path = Path(f"/tmp/firecracker-{self.vm_id}.sock")
        self.metrics_fifo_path = Path(f"/tmp/firecracker-{self.vm_id}-metrics.fifo")
        self.firecracker_process: Optional[subprocess.Popen] = None
        self.session = requests_unixsocket.Session()
        self.command_image_path: Optional[Path] = None # Path to temporary image for commands
        # Removed firecracker_stdout_file and firecracker_stderr_file

    def _create_command_image(self, command: str, extra_files: Dict[Path, str] = None) -> Path:
        """
        Creates a temporary virtio-block image containing the command script and optional extra files.
        """
        image_path = Path(f"/tmp/firecracker-cmd-{self.vm_id}.ext4")
        script_content = f"#!/bin/sh\n{command}\n"
        
        # Create a small disk image
        subprocess.run(["sudo", "dd", "if=/dev/zero", f"of={image_path}", "bs=1M", "count=1"], check=True)
        subprocess.run(["sudo", "mkfs.ext4", "-F", str(image_path)], check=True)
        
        # Mount and write files
        mount_point = Path(f"/tmp/firecracker-cmd-mount-{self.vm_id}")
        mount_point.mkdir(exist_ok=True)
        
        subprocess.run(["sudo", "mount", str(image_path), str(mount_point)], check=True)
        
        try:
            # Write main test script
            script_file_path_in_mount = mount_point / "test_script.sh"
            with open("/tmp/temp_script.sh", "w") as f:
                f.write(script_content)
            subprocess.run(["sudo", "cp", "/tmp/temp_script.sh", str(script_file_path_in_mount)], check=True)
            subprocess.run(["sudo", "chmod", "755", str(script_file_path_in_mount)], check=True)
            
            # Write extra files
            if extra_files:
                for rel_path, content in extra_files.items():
                    target_path = mount_point / rel_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with open("/tmp/temp_extra_file", "w") as f:
                        f.write(content)
                    subprocess.run(["sudo", "cp", "/tmp/temp_extra_file", str(target_path)], check=True)
        finally:
            subprocess.run(["sudo", "umount", str(mount_point)], check=True)
            mount_point.rmdir()
        
        self.command_image_path = image_path
        return image_path

    def _start_firecracker_process(self):
        """Starts the Firecracker VMM as a subprocess, including metrics FIFO and stdout/stderr redirection."""
        if self.metrics_fifo_path.exists():
            self.metrics_fifo_path.unlink() # Clean up old FIFO
        os.mkfifo(self.metrics_fifo_path) # Create named pipe for metrics

        cmd = [
            "/usr/local/bin/firecracker",
            "--api-sock",
            str(self.api_socket_path),
            "--metrics-path",
            str(self.metrics_fifo_path),
        ]
        logger.info(f"Starting Firecracker: {' '.join(cmd)}")
        self.firecracker_process = subprocess.Popen(
            cmd,
            stdout=sys.stdout, # Redirect stdout to console for debugging
            stderr=sys.stderr, # Redirect stderr to console for debugging
            text=True,
            preexec_fn=os.setsid # Ensure process is in its own group
        )
        
        # Wait for the API socket to become available
        for _ in range(20): # Try for up to 2 seconds
            if self.api_socket_path.exists():
                logger.debug(f"Firecracker API socket {self.api_socket_path} appeared.")
                break
            time.sleep(0.1)
        else:
            if self.firecracker_process and self.firecracker_process.poll() is not None: # Check if it exited
                raise RuntimeError(f"Firecracker exited prematurely during socket wait. Check console output.")
            raise RuntimeError(f"Firecracker API socket {self.api_socket_path} did not appear. Firecracker process might be hung. Killing it.")
        
        # Check for immediate errors
        time.sleep(0.1) # Give it a moment
        if self.firecracker_process and self.firecracker_process.poll() is not None: # Check if it exited
            raise RuntimeError(f"Firecracker exited immediately after socket appeared. Check console output.")

    async def _configure_vm(self, command_image: Optional[Path] = None):
        """Configures the MicroVM via the Firecracker API."""
        base_url = f"http+unix://{str(self.api_socket_path).replace('/', '%2F')}"

        # Boot source
        logger.debug(f"Configuring boot source: {self.kernel_path}")
        try:
            self.session.put(
                f"{base_url}/boot-source",
                json={
                    "kernel_image_path": str(self.kernel_path.resolve()),
                    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off root=/dev/vda rw init=/sbin/init devtmpfs.mount=1"
                }
            ).raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Firecracker API Connection Error (Boot Source): {e}. Check console output for Firecracker logs.")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Firecracker API Error (Boot Source): {e.response.text}")
            raise

        # Root drive
        logger.debug(f"Configuring rootfs: {self.rootfs_path}")
        try:
            response = self.session.put(
                f"{base_url}/drives/rootfs",
                json={
                    "drive_id": "rootfs",
                    "path_on_host": str(self.rootfs_path.resolve()),
                    "is_root_device": True,
                    "is_read_only": False,
                }
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Firecracker API Connection Error (RootFS): {e}. Check console output for Firecracker logs.")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Firecracker API Error (RootFS): {e.response.text}")
            raise

        # Command drive (if provided)
        if command_image:
            logger.debug(f"Configuring command drive: {command_image}")
            try:
                self.session.put(
                    f"{base_url}/drives/cmd_drive",
                    json={
                        "drive_id": "cmd_drive",
                        "path_on_host": str(command_image.resolve()),
                        "is_root_device": False,
                        "is_read_only": True,
                        "partuuid": "42" # Dummy PARTUUID
                    }
                ).raise_for_status()
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Firecracker API Connection Error (Command Drive): {e}. Check console output for Firecracker logs.")
                raise
            except requests.exceptions.HTTPError as e:
                logger.error(f"Firecracker API Error (Command Drive): {e.response.text}")
                raise

        # Machine configuration (2 vCPUs, 512MiB RAM)
        logger.debug("Configuring machine info...")
        try:
            response = self.session.put(
                f"{base_url}/machine-config",
                json={"vcpu_count": 2, "mem_size_mib": 512}
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Firecracker API Connection Error (Machine Config): {e}. Check console output for Firecracker logs.")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Firecracker API Error (Machine Config): {e.response.text}")
            raise

    async def _start_instance(self):
        """Starts the configured Firecracker MicroVM instance."""
        base_url = f"http+unix://{str(self.api_socket_path).replace('/', '%2F')}"
        logger.info(f"Starting MicroVM {self.vm_id} instance...")
        try:
            self.session.put(f"{base_url}/actions", json={"action_type": "InstanceStart"}).raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Firecracker API Connection Error (Start Instance): {e}. Check console output for Firecracker logs.")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Firecracker API Error (Start Instance): {e.response.text}")
            raise
        logger.info(f"MicroVM {self.vm_id} started.")

    async def _read_metrics(self, timeout: int = 5) -> Dict:
        """Reads metrics from the FIFO."""
        metrics_data = {}
        if not self.metrics_fifo_path.exists():
            return metrics_data

        try:
            # Open FIFO for non-blocking read
            # Use asyncio for non-blocking read from FIFO
            proc = await asyncio.create_subprocess_exec(
                "cat", str(self.metrics_fifo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
            if stdout:
                # Firecracker metrics JSON can contain multiple metrics objects
                # Need to split by newline and parse each line
                for line in stdout.decode().splitlines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            metrics_data.update(data) # Merge all metrics
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse metrics JSON: {line}")
            if stderr:
                logger.error(f"Error reading metrics FIFO: {stderr.decode()}")

        except asyncio.TimeoutError:
            logger.warning(f"Timeout reading metrics from FIFO {self.metrics_fifo_path}. (This is normal if VM finished quickly)")
        except Exception as e:
            logger.error(f"Unexpected error reading metrics FIFO: {e}")
        finally:
            # Ensure cat process is terminated
            if proc and proc.returncode is None:
                proc.kill()
        return metrics_data

    async def run_command(self, command: str, timeout: int = 60, extra_files: Dict[Path, str] = None) -> Tuple[int, str, str, Dict]:
        """
        Executes a command inside a fresh MicroVM instance.
        Each call starts a new VM, runs the command, and stops the VM.
        Returns exit_code, stdout, stderr, and metrics.
        """
        if not self.kernel_path.exists() or not self.rootfs_path.exists():
            raise FileNotFoundError("Kernel or rootfs image not found.")

        # Ensure socket is clean if previous run failed
        if self.api_socket_path.exists():
            self.api_socket_path.unlink()

        metrics = {}
        try:
            command_image = self._create_command_image(command, extra_files=extra_files)
            self._start_firecracker_process()
            await self._configure_vm(command_image=command_image) # Await configure_vm
            await self._start_instance()

            # Stdout/stderr are now directed to console, so we can't capture them here.
            # This is temporary for debugging.
            # Await VM to power off (indicated by firecracker_process.wait())
            exit_code = -1 # Default for now
            if self.firecracker_process:
                self.firecracker_process.wait(timeout=timeout)
                exit_code = self.firecracker_process.returncode

            # Flush and read metrics after VM execution
            base_url = f"http+unix://{str(self.api_socket_path).replace('/', '%2F')}"
            try:
                self.session.put(f"{base_url}/actions", json={"action_type": "FlushMetrics"}).raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.warning(f"Failed to flush metrics: {e.response.text}. Continuing.")

            metrics = await self._read_metrics() # Await the async call

            return exit_code, "Output directed to console.", "Errors directed to console.", metrics # Dummy strings for now

        except subprocess.TimeoutExpired:
            self.stop() # Ensure VM is stopped
            return -1, "", "Command execution timed out in MicroVM.", {}
        except Exception as e:
            logger.error(f"Error running command in MicroVM: {e}")
            self.stop() # Ensure VM is stopped
            return -1, "", f"MicroVM execution error: {e}", {}
        finally:
            self.stop()
            if self.command_image_path and self.command_image_path.exists():
                subprocess.run(["sudo", "rm", str(self.command_image_path)], check=False)
                self.command_image_path = None
            # Removed file cleanup for firecracker_stdout_file and firecracker_stderr_file

    def stop(self):
        """Stops the Firecracker MicroVM and cleans up resources."""
        if self.firecracker_process:
            logger.info(f"Stopping MicroVM {self.vm_id}...")
            
            # Temporary: No stdout/stderr capture here, output goes to console
            # Try to send Ctrl+Alt+Del for graceful shutdown
            try:
                base_url = f"http+unix://{str(self.api_socket_path).replace('/', '%2F')}"
                self.session.put(f"{base_url}/actions", json={"action_type": "SendCtrlAltDel"}).raise_for_status()
                time.sleep(1) # Give guest a moment to react
            except requests.exceptions.ConnectionError:
                logger.debug("VM already disconnected/shut down gracefully.")
            except Exception as e:
                logger.warning(f"Error sending Ctrl+Alt+Del to VM: {e}")

            if self.firecracker_process.poll() is None: # Still running?
                os.killpg(os.getpgid(self.firecracker_process.pid), 9) # SIGKILL
                try:
                    self.firecracker_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.error("Firecracker process did not terminate after SIGKILL.")
            logger.info(f"Firecracker process {self.firecracker_process.pid} killed/terminated.")
            self.firecracker_process = None
        
        if self.api_socket_path.exists():
            self.api_socket_path.unlink()
            logger.debug(f"Removed API socket {self.api_socket_path}")
        
        if self.metrics_fifo_path.exists():
            self.metrics_fifo_path.unlink()
            logger.debug(f"Removed metrics FIFO {self.metrics_fifo_path}")