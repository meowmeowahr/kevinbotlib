import psutil
from pydantic.dataclasses import dataclass


@dataclass
class CPUInfo:
    """CPU Information Type"""

    cores_logical: int
    """Logical cores"""
    cores_physical: int
    """Physical cores"""
    frequency_current: float
    """Current running CPU frequency"""
    frequency_min: float
    """Minimum operational CPU frequency"""
    frequency_max: float
    """Maximum operational CPU frequency"""
    usage_percent_per_core: list[float]
    """Percent CPU usage per core"""
    total_usage_percent: float
    """Total CPU usage percentage"""


@dataclass
class MemoryInfo:
    """Memory Information Type"""

    total: int
    """Total memory amount (bytes)"""
    available: int
    """Total memory available (bytes)"""
    used: int
    """Total memory used (bytes)"""
    free: int
    """Total memory free (bytes)"""
    percent: float
    """Total memory used (percent)"""


@dataclass
class DiskInfo:
    """Disk Information Type"""

    device: str
    """Device path"""
    mountpoint: str
    """Disk mountpoint"""
    fstype: str
    """Disk filesystem type"""
    total: int
    """Total disk bytes"""
    used: int
    """Total disk space used (bytes)"""
    free: int
    """Total disk space free (bytes)"""
    percent: float
    """Total disk used (percent)"""


class SystemPerformanceData:
    """System information API"""

    @staticmethod
    def cpu() -> CPUInfo:
        """
        Gets CPU information

        Returns:
            CPU Information
        """
        cpu_freq = psutil.cpu_freq()

        logical = psutil.cpu_count(logical=True)
        if not logical:
            logical = 0

        physical = psutil.cpu_count(logical=False)
        if not physical:
            physical = 0

        return CPUInfo(
            cores_logical=logical,
            cores_physical=physical,
            frequency_current=cpu_freq.current if cpu_freq else 0.0,
            frequency_min=cpu_freq.min if cpu_freq else 0.0,
            frequency_max=cpu_freq.max if cpu_freq else 0.0,
            usage_percent_per_core=psutil.cpu_percent(percpu=True),
            total_usage_percent=psutil.cpu_percent(percpu=False),
        )

    @staticmethod
    def memory() -> MemoryInfo:
        """
        Gets memory information

        Returns:
            Memory information
        """
        mem = psutil.virtual_memory()
        return MemoryInfo(
            total=mem.total,
            available=mem.available,
            used=mem.used,
            free=mem.free,
            percent=mem.percent,
        )

    @staticmethod
    def disks() -> list[DiskInfo]:
        """
        Gets system disk(s) information

        Returns:
            Disk information
        """
        disks = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks.append(
                    DiskInfo(
                        device=part.device,
                        mountpoint=part.mountpoint,
                        fstype=part.fstype,
                        total=usage.total,
                        used=usage.used,
                        free=usage.free,
                        percent=usage.percent,
                    )
                )
            except PermissionError:
                continue
        return disks

    @staticmethod
    def primary_disk() -> DiskInfo:
        """
        Gets system primary disk information

        Returns:
            Primary disk information
        """
        for disk in SystemPerformanceData.disks():
            if disk.mountpoint == "/":
                return disk
        if not SystemPerformanceData.disks():
            raise
        return SystemPerformanceData.disks()[0]
