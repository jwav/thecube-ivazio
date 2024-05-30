import ctypes
import os

def check_capabilities():
    CAP_SYS_NICE = 24
    CAP_DAC_OVERRIDE = 1

    libc = ctypes.CDLL('libc.so.6', use_errno=True)

    class CapHeader(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32),
                    ("pid", ctypes.c_int)]

    class CapData(ctypes.Structure):
        _fields_ = [("effective", ctypes.c_uint32),
                    ("permitted", ctypes.c_uint32),
                    ("inheritable", ctypes.c_uint32)]

    header = CapHeader()
    data = (CapData * 2)()
    header.version = 0x19980330
    header.pid = 0

    if libc.capget(ctypes.byref(header), ctypes.byref(data)) != 0:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))

    cap_sys_nice = (data[0].effective & (1 << CAP_SYS_NICE)) != 0
    cap_dac_override = (data[0].effective & (1 << CAP_DAC_OVERRIDE)) != 0

    print(f"Effective UID: {os.geteuid()}")
    print(f"Has CAP_SYS_NICE? {cap_sys_nice}")
    print(f"Has CAP_DAC_OVERRIDE? {cap_dac_override}")

if __name__ == "__main__":
    check_capabilities()
    if not os.geteuid() == 0 and not (check_capabilities()):
        print("Need root or appropriate capabilities to run this script.")
        exit(1)
