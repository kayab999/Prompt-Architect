import subprocess
import logging
import tomllib
import uuid # For unique VM IDs
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from .ipc_utils import read_prefixed, write_prefixed
from .microvm_manager import MicroVMLauncher # Import the new manager

logger = logging.getLogger(__name__)

class TribunalEngine:
    """
    Motor proactivo para validación determinista de código generado.
    Refactored: Now executes tests inside a Firecracker MicroVM for isolation.
    """
    
    def __init__(self, project_dir: Path, kernel_path: Path, rootfs_path: Path):
        self.project_dir = project_dir
        self.constitution_path = project_dir / "project.toml"
        self.constitution = self._load_constitution()
        self.base_tests_path = Path(__file__).parent.parent / "rules/base_tests.toml"
        self.base_tests = self._load_base_tests()
        logger.info(f"DEBUG: Loaded tests: {self.base_tests}")

        self.kernel_path = kernel_path
        self.rootfs_path = rootfs_path

        if not self.kernel_path.exists():
            raise FileNotFoundError(f"Kernel image not found at {self.kernel_path}. Please download it.")
        if not self.rootfs_path.exists():
            raise FileNotFoundError(f"Rootfs image not found at {self.rootfs_path}. Please create it.")



    def _load_constitution(self) -> Dict:
        if not self.constitution_path.exists():
            raise FileNotFoundError(f"Constitution not found at {self.constitution_path}")
        with open(self.constitution_path, "rb") as f:
            return tomllib.load(f)

    def _load_base_tests(self) -> Dict:
        if not self.base_tests_path.exists():
            return {}
        with open(self.base_tests_path, "rb") as f:
            return tomllib.load(f)

    async def run_tribunal(self, code_path: Path) -> Tuple[Dict[str, Any], Dict]: # Modified signature to return metrics
        """
        Ejecuta la batería de tests destructivos deterministas dentro de un MicroVM.
        Retorna (results, metrics)
        """
        results = {
            "status": "PASSED",
            "violations": [],
            "warnings": []
        }
        metrics_data = {} # Initialize metrics

        vm_id = f"tribunal-vm-{uuid.uuid4().hex}"
        microvm = MicroVMLauncher(vm_id, self.kernel_path, self.rootfs_path)

        # 1. Prepare the test script for the MicroVM
        code_content = read_prefixed(code_path)
        
        # Extract the first markdown code block, if any
        import re
        code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", code_content, re.DOTALL)
        actual_code = code_blocks[0] if code_blocks else code_content
        
        vm_test_script_lines = [
            "#!/bin/sh",
            "set -e", # Exit immediately if a command exits with a non-zero status.
            "chmod +x /mnt/generated_code.rs", # Make it executable if needed for rust test
            "",
            "# --- Running Destructive Tests ---"
        ]

        # Add base tests from base_tests.toml
        tests = self.base_tests.get("tests", {})
        for test_name, test_cfg in tests.items():
            cmd_list = test_cfg.get("command", [])
            if not cmd_list:
                continue
            
            # For PoC, assume commands are simple and can be executed directly in busybox sh
            quoted_cmd = " ".join([f"'{arg}'" for arg in cmd_list]) # Basic quoting
            vm_test_script_lines.append(f"echo \"Running test: {test_name}\"")
            vm_test_script_lines.append(f"{quoted_cmd} > /tmp/test_output_{test_name}.txt 2>&1 || echo \"TEST_FAILED:{test_name}\" >> /tmp/test_results.txt")
            vm_test_script_lines.append(f"cat /tmp/test_output_{test_name}.txt") # Print output to serial console

        vm_test_script_lines.append("")
        vm_test_script_lines.append("# --- Running Static Analysis ---")

        # 2. Invariantes estáticas (PoC - run inside VM for full isolation)
        if self.constitution.get("invariants", {}).get("no_unsafe_blocks", False):
            vm_test_script_lines.append("echo \"Checking for unsafe blocks...\"")
            vm_test_script_lines.append("if grep -q 'unsafe' /mnt/generated_code.rs; then")
            vm_test_script_lines.append("    echo \"STATIC_ANALYSIS_FAILED:unsafe_block_found\" >> /tmp/test_results.txt")
            vm_test_script_lines.append("fi")
        
        vm_test_script_content = "\n".join(vm_test_script_lines)

        try:
            # 2. Execute the combined script inside the MicroVM
            # Pass actual_code as an extra file to the command image
            extra_files = {Path("generated_code.rs"): actual_code}
            exit_code, stdout, stderr, metrics_data = await microvm.run_command(vm_test_script_content, timeout=60, extra_files=extra_files) # Await and get metrics

            # 3. Parse output from MicroVM
            # Look for "TEST_FAILED" and "STATIC_ANALYSIS_FAILED" in stdout
            if "TEST_FAILED" in stdout or "STATIC_ANALYSIS_FAILED" in stdout:
                results["status"] = "FAILED"
                # Basic parsing, more robust parsing needed for actual implementation
                for line in stdout.splitlines():
                    if "TEST_FAILED:" in line:
                        test_name = line.split("TEST_FAILED:")[1].strip()
                        results["violations"].append({
                            "type": "destructive_test_failure_vm",
                            "test_name": test_name,
                            "output": stdout # For PoC, include full output
                        })
                    elif "STATIC_ANALYSIS_FAILED:" in line:
                        rule_name = line.split("STATIC_ANALYSIS_FAILED:")[1].strip()
                        results["violations"].append({
                            "type": "static_analysis_vm",
                            "rule": rule_name,
                            "output": stdout
                        })
            
            if exit_code != 0 and results["status"] != "FAILED": # VM exited with error but no explicit test failure
                 results["status"] = "FAILED"
                 results["violations"].append({"type": "vm_exit_error", "exit_code": exit_code, "stderr": stderr, "stdout": stdout})

        except Exception as e:
            logger.error(f"Error during MicroVM test execution: {e}")
            results["status"] = "FAILED"
            results["violations"].append({"type": "microvm_execution_error", "error": str(e)})
        finally:
            microvm.stop() # Ensure VM is stopped and cleaned up
            if microvm.command_image_path and microvm.command_image_path.exists():
                subprocess.run(["sudo", "rm", str(microvm.command_image_path)], check=False)
                microvm.command_image_path = None # Clean up after potential failed run

        return results, metrics_data # Return metrics data

    def auto_fix(self, code_path: Path, violations: List[Dict]):
        """
        Intenta correcciones deterministas simples usando IPC con prefijo.
        This still runs on the host for simplicity.
        """
        code = read_prefixed(code_path)
        new_code = code.replace("unsafe {", "/* unsafe forbidden */ {") 
        write_prefixed(code_path, new_code)
        logger.info(f"Auto-fixed code in {code_path}")