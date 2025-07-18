#!/usr/local/bin/python3.13
"""launcher"""
import os
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

TOPO_ENV = "CLAB_TOPO"
NODE_FILTER_ENV = "NODE_FILTER"
WORKDIR_ENV = "WORKDIR"
HOST_ARCH_ENV = "HOST_ARCH"


class Launcher:
    def __init__(self) -> None:
        """Dumb class to handling starting/stopping clab"""
        self.shutdown = False
        self.exit_code = 0

        self.workdir = os.getenv(WORKDIR_ENV, "/launcher")

        self.topo = os.getenv(TOPO_ENV, "topo.amd64.yaml")
        if "x86_64" in self.topo:
            # uname may be x86_64, which for us means amd64
            self.topo = self.topo.replace("x86_64", "amd64")

        if os.getenv(HOST_ARCH_ENV, "") == "arm64":
            self.topo = os.getenv(TOPO_ENV, "topo.arm64.yaml")

        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_forcefully)

        self.start()

    def exit_gracefully(self, signum: Any, frame: Any) -> None:
        """
        Exit clab/container gracefully when SIGINT received

        Args:
            signum: singum from the singal handler, unused here
            frame: frame from the signal handler, unused here

        Returns:
            N/A

        Raises:
            N/A

        """
        _ = frame

        print(f"received exit signal {signum}; exiting")
        self.shutdown = True

    def exit_forcefully(self, signum: Any, frame: Any) -> None:
        """
        Exit clab/container violently when SIGTERM received

        Args:
            signum: singum from the singal handler, unused here
            frame: frame from the signal handler, unused here

        Returns:
            N/A

        Raises:
            N/A

        """
        _ = frame

        print(f"received exit signal {signum}; exiting")
        self.shutdown = True

        sys.exit(1)

    def _start(self, reconfigure: bool = False) -> None:
        launch_command = ["containerlab", "-t", self.topo, "deploy"]
        if reconfigure is True:
            launch_command.append("--reconfigure")

        _filter = os.getenv(NODE_FILTER_ENV, "")
        if _filter:
            launch_command.extend(["--node-filter", _filter])

        print(f"starting with command {launch_command}")

        proc = subprocess.Popen(
            launch_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.workdir,
        )

        reconfigure = False

        while True:
            if self.shutdown:
                break

            if proc.poll():
                break

            line = proc.stderr.readline()

            if not line:
                time.sleep(0.1)
                continue

            if "--reconfigure" in line:
                reconfigure = True

            print(line)

        if reconfigure:
            print("restarting with reconfigure flag...")
            self._start(reconfigure=True)
        else:
            print("failed launching...")
            print("stopping container...")
            self.shutdown = True
            self.exit_code = 1

    def start(self) -> None:
        """
        Start clab

        Args:
            N/A

        Returns:
            N/A

        Raises:
            N/A

        """
        print(f"copying topos to workdir '{self.workdir}'...")

        for item in Path("topos").iterdir():
            if item.is_file():
                shutil.copy(item, self.workdir)

        print(f"copying wait.sh to workdir {self.workdir}...")
        shutil.copy(Path("wait.sh"), self.workdir)

        print(f"copying configs directory to workdir {self.workdir}...")
        shutil.copytree(Path("configs"), f"{self.workdir}/configs")

        print("starting clab...")

        executor = ThreadPoolExecutor(max_workers=2)
        executor.submit(self._start, reconfigure=False)
        executor.submit(self.run)

    def run(self) -> None:
        """
        Run while the container has not received SIGINT or SIGTERM

        Once `self.shutdown` is set to True we'll stop sleeping and shut down clab

        Args:
            N/A

        Returns:
            N/A

        Raises:
            N/A

        """
        while self.shutdown is False:
            time.sleep(1)

        self.stop()

        sys.exit(self.exit_code)

    def stop(self) -> None:
        """
        Stop clab

        Args:
            N/A

        Returns:
            N/A

        Raises:
            N/A

        """
        print("stopping clab...")

        destroy_command = ["containerlab", "-t", self.topo, "destroy", "--cleanup"]

        print(f"stopping with command {destroy_command}")

        proc = subprocess.run(
            destroy_command,
            capture_output=True,
            cwd=self.workdir,
            check=True,
        )

        if proc.returncode != 0:
            print("failed stopping containerlab...")
            print(f"stdout: {proc.stdout!r}")
            print(f"stderr: {proc.stderr!r}")
        else:
            print("clab stopped successfully")


if __name__ == "__main__":
    Launcher()
