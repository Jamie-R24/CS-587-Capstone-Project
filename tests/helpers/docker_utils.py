#!/usr/bin/env python3
"""
Docker utility functions for system tests
Provides helpers for container management, command execution, and cleanup
"""

import subprocess
import time
import os
import docker
from pathlib import Path


class DockerHelper:
    """Helper class for Docker operations in system tests"""

    def __init__(self, project_root=None):
        # Auto-detect project root if not provided
        if project_root is None:
            # Find project root by looking for docker-compose.yml
            current = Path(__file__).resolve()
            while current != current.parent:
                if (current / 'docker-compose.yml').exists():
                    project_root = str(current)
                    break
                current = current.parent
            if project_root is None:
                raise RuntimeError("Could not find project root (docker-compose.yml)")
        
        self.project_root = project_root
        self.client = docker.from_env()
        self.compose_file = os.path.join(project_root, 'docker-compose.yml')

    def start_system(self, clean=True):
        """
        Start the complete system using docker-compose

        Args:
            clean: If True, clean data directories before starting

        Returns:
            True if successful, False otherwise
        """
        print(f"[DockerHelper] Starting system (clean={clean})...")
        
        if clean:
            self.clean_data_directories()

        # Start containers
        result = subprocess.run(
            ['docker-compose', 'up', '-d'],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"[DockerHelper] ERROR: Failed to start containers: {result.stderr}")
            return False

        print(f"[DockerHelper] Containers started, waiting for ready state...")
        
        # Wait for containers to be ready
        return self.wait_for_containers_ready()

    def stop_system(self, remove_volumes=True):
        """
        Stop all containers

        Args:
            remove_volumes: If True, remove volumes as well
        """
        print(f"[DockerHelper] Stopping system (remove_volumes={remove_volumes})...")
        
        cmd = ['docker-compose', 'down']
        if remove_volumes:
            cmd.append('-v')

        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[DockerHelper] System stopped successfully")
        else:
            print(f"[DockerHelper] WARNING: Error stopping system: {result.stderr}")

    def clean_data_directories(self):
        """Clean data directories before test run"""
        print(f"[DockerHelper] Cleaning data directories...")
        
        data_dir = os.path.join(self.project_root, 'data')

        # Directories to clean
        clean_paths = [
            os.path.join(data_dir, 'output'),
            os.path.join(data_dir, 'accumulated_data'),
            os.path.join(data_dir, 'test_sets'),
            os.path.join(data_dir, 'poisoning')
        ]

        for path in clean_paths:
            if os.path.exists(path):
                subprocess.run(['rm', '-rf', path], capture_output=True)
                os.makedirs(path, exist_ok=True)
                print(f"[DockerHelper]   Cleaned: {os.path.basename(path)}/")

    def wait_for_containers_ready(self, timeout=120):
        """
        Wait for all containers to be healthy and ready

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if all containers ready, False if timeout
        """
        start_time = time.time()
        containers = ['workstation', 'target', 'monitor']

        print(f"[DockerHelper] Waiting for containers to be ready (timeout={timeout}s)...")

        while time.time() - start_time < timeout:
            all_ready = True

            for container_name in containers:
                try:
                    container = self.client.containers.get(container_name)

                    # Check if container is running
                    if container.status != 'running':
                        all_ready = False
                        break

                    # For workstation, check health status
                    if container_name == 'workstation':
                        health = container.attrs.get('State', {}).get('Health', {})
                        status = health.get('Status', 'none')
                        if status not in ['healthy', 'none']:
                            all_ready = False
                            break

                except docker.errors.NotFound:
                    all_ready = False
                    break

            if all_ready:
                elapsed = time.time() - start_time
                print(f"[DockerHelper] ✓ All containers ready! ({elapsed:.1f}s)")
                return True

            time.sleep(2)

        print(f"[DockerHelper] ✗ TIMEOUT waiting for containers ({timeout}s)")
        return False

    def exec_in_container(self, container_name, command):
        """
        Execute command in container and return output

        Args:
            container_name: Name of container (workstation, target, monitor)
            command: Command to execute (list or string)

        Returns:
            dict with 'stdout', 'stderr', 'exit_code'
        """
        if isinstance(command, str):
            command = ['bash', '-c', command]

        result = subprocess.run(
            ['docker', 'exec', container_name] + command,
            capture_output=True,
            text=True
        )

        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'exit_code': result.returncode
        }

    def get_container_logs(self, container_name, tail=100):
        """
        Get recent logs from container

        Args:
            container_name: Container to get logs from
            tail: Number of recent lines to retrieve

        Returns:
            String with log output
        """
        result = subprocess.run(
            ['docker', 'logs', '--tail', str(tail), container_name],
            capture_output=True,
            text=True
        )

        return result.stdout

    def file_exists_in_container(self, container_name, file_path):
        """
        Check if file exists in container

        Args:
            container_name: Container to check
            file_path: Path to file in container

        Returns:
            True if file exists, False otherwise
        """
        result = self.exec_in_container(
            container_name,
            f'test -f {file_path} && echo "exists" || echo "not_found"'
        )

        return 'exists' in result['stdout']

    def read_file_from_container(self, container_name, file_path):
        """
        Read file contents from container

        Args:
            container_name: Container to read from
            file_path: Path to file in container

        Returns:
            File contents as string, or None if file doesn't exist
        """
        result = self.exec_in_container(container_name, f'cat {file_path}')

        if result['exit_code'] == 0:
            return result['stdout']
        else:
            return None

    def count_files_in_directory(self, container_name, directory, pattern='*'):
        """
        Count files matching pattern in directory

        Args:
            container_name: Container to check
            directory: Directory path in container
            pattern: File pattern (e.g., '*.json')

        Returns:
            Number of matching files
        """
        result = self.exec_in_container(
            container_name,
            f'ls {directory}/{pattern} 2>/dev/null | wc -l'
        )

        try:
            return int(result['stdout'].strip())
        except ValueError:
            return 0

    def get_file_line_count(self, container_name, file_path):
        """
        Get number of lines in file

        Args:
            container_name: Container to check
            file_path: Path to file

        Returns:
            Number of lines, or 0 if file doesn't exist
        """
        result = self.exec_in_container(
            container_name,
            f'wc -l < {file_path} 2>/dev/null || echo "0"'
        )

        try:
            return int(result['stdout'].strip())
        except ValueError:
            return 0

    def restart_container(self, container_name):
        """
        Restart specific container

        Args:
            container_name: Container to restart

        Returns:
            True if successful
        """
        print(f"[DockerHelper] Restarting container: {container_name}...")
        
        try:
            container = self.client.containers.get(container_name)
            container.restart()
            time.sleep(5)  # Wait for restart
            print(f"[DockerHelper] ✓ Container {container_name} restarted")
            return True
        except Exception as e:
            print(f"[DockerHelper] ✗ Failed to restart {container_name}: {e}")
            return False

    def get_container_status(self):
        """
        Get status of all containers

        Returns:
            dict mapping container name to status
        """
        status = {}
        containers = ['workstation', 'target', 'monitor']

        for container_name in containers:
            try:
                container = self.client.containers.get(container_name)
                status[container_name] = {
                    'running': container.status == 'running',
                    'status': container.status,
                    'health': container.attrs.get('State', {}).get('Health', {}).get('Status', 'none')
                }
            except docker.errors.NotFound:
                status[container_name] = {
                    'running': False,
                    'status': 'not_found',
                    'health': 'none'
                }

        return status

    def print_container_status(self):
        """Print status of all containers for debugging"""
        print("\n[DockerHelper] Container Status:")
        status = self.get_container_status()
        
        for container_name, info in status.items():
            running_symbol = "✓" if info['running'] else "✗"
            print(f"  {running_symbol} {container_name}: {info['status']} (health: {info['health']})")
        print()
