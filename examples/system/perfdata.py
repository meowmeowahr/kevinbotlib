from kevinbotlib.system import SystemPerformanceData

cpu = SystemPerformanceData.cpu()
print("CPU")
print(cpu)

memory = SystemPerformanceData.memory()
print("\nMemory")
print(memory)

disks = SystemPerformanceData.disks()
print("\nAll Disks")
print(disks)

primary_disk = SystemPerformanceData.primary_disk()
print("\nPrimary Disk")
print(primary_disk)
