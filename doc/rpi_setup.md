# Installing PREEMPT_RT realtime Linux on a Raspberry Pi 3

To control the bean ejectors in the optical coffee sorter, the Raspberry Pi 3 must be able to react fast enough. Its CPU speed is sufficient for that, but interrupt handling can introduce significant delays. A realtime patch for Linux offers a solution. We chose the most well-known one, PREEMPT_RT. Here is how to get it to run on the Raspberry Pi 3.

Note that the instructions below work only with the software versions referenced, following the [instructions by markusr](https://github.com/raspberrypi/linux/issues/2244#issuecomment-360495938). If you want to use other versions, make sure that the kernel version provided by the Pi Foundation and the PREEMPT_RT patch refer to the same version of Linux.


## 1. Steps on your computer

**(1)** Download and unpack the 2017-11-29 release image of [Raspbian Lite](https://www.raspberrypi.org/downloads/raspbian/) or Raspbian:

    wget https://downloads.raspberrypi.org/raspbian_lite/images/raspbian_lite-2017-12-01/2017-11-29-raspbian-stretch-lite.zip
    unzip 2017-11-29-raspbian-stretch-lite.zip
    
**(2)** Insert a microSD card and find out its device file:

    lsblk
    
**(3)** Copy your image file to the SD card, supplying your device file instead of `/dev/sdx` ([details](https://www.raspberrypi.org/documentation/installation/installing-images/linux.md)):

    sudo dd bs=4M if=2017-11-29-raspbian-stretch-lite.img of=/dev/sdx conv=fsync
    
**(4)** Create an empty file `/boot/ssh` to start the Raspberry Pi with SSH enabled ([background](https://www.raspberrypi.org/blog/a-security-update-for-raspbian-pixel/)):

    sudo mount /dev/sdb1 /media/username/boot
    touch /media/username/boot/ssh
    sudo umount /dev/sdb1


# 2. Steps on the Raspberry Pi 3


**(1)** Start the Raspberry Pi 3 and connect it with an Ethernet cable to your local network.

**(2)** Find out the Pi's IP address from the DHCP client list of your router ([details](https://www.raspberrypi.org/documentation/remote-access/ip-address.md)).

**(3)** Log in to the Raspberry Pi 3 with the default account (username `pi`, password `raspberry`), using the IP address it has in your case of course:

    ssh pi@192.168.0.100
    
**(4)** Change the SSH password of the Raspberry Pi, and note it down:

    passwd
    
**(5)** Install `vim-nox` to prevent issues with navigation keys creating characters in `vi`:

    sudo apt install vim-nox
    
**(6)** Download and extract the sources of the Linux kernel version 4.14.14 (195 MiB):

    wget https://github.com/raspberrypi/linux/archive/23816e63fcc5efa8400f248304db13d5df69792f.zip
    mv 23816e63fcc5efa8400f248304db13d5df69792f.zip linux-23816e63fcc5efa8400f248304db13d5df69792f.zip
    unzip linux-23816e63fcc5efa8400f248304db13d5df69792f.zip
    
**(7)** Download and apply the PREEMPT_RT realtime kernel patch version 4.14.12 (which still works with the kernel we downloaded):

    wget https://www.kernel.org/pub/linux/kernel/projects/rt/4.14/older/patch-4.14.12-rt10.patch.gz
    cd linux-23816e63fcc5efa8400f248304db13d5df69792f
    zcat ../patch-4.14.12-rt10.patch.gz | patch -p1
    cd ..

**(8)** Prepare compilation:

    export KERNEL=kernel7
    export ARCH=arm
    export CROSS_COMPILE=
    export CONCURRENCY_LEVEL=$(nproc)
    cd linux-23816e63fcc5efa8400f248304db13d5df69792f/
    make bcm2709_defconfig

**(9)** Download and apply the [RPi FQI patch](https://www.osadl.org/Single-View.111+M5c03315dc57.0.html), needed to prevent system freezes on the RPi with PREEMPT_RT kernels:

    cd ..
    wget https://raw.githubusercontent.com/fedberry/kernel/master/usb-dwc_otg-fix-system-lockup-when-interrupts-are-threaded.patch
    cd linux-23816e63fcc5efa8400f248304db13d5df69792f/
    patch -i ../usb-dwc_otg-fix-system-lockup-when-interrupts-are-threaded.patch -p1

We use a [rebased version](https://github.com/fedberry/kernel/blob/master/usb-dwc_otg-fix-system-lockup-when-interrupts-are-threaded.patch) of the [original patch](https://www.osadl.org/monitoring/patches/rbs3s/usb-dwc_otg-fix-system-lockup-when-interrupts-are-threaded.patch.html) for more recent kernel versions, but it is functional equivalent. You can also apply this patch to a wide range of other kernel versions, but then you should use `patch` with `--dry-run` first until you can make the patch apply all its pieces ("hunks"), with or without offsets.

**(10)** Configure the kernel to make it a realtime kernel:

    sudo apt-get install libncurses5-dev bc 
    make menuconfig

* Set "Kernel Features → Preemption Model" to  "Fully Preemptible Kernel (RT)".
* Set "Kernel Features → Timer frequency" to "1000 Hz".
* Save and exit `menuconfig`.

**(11)** Compile the kernel:

    make clean
    ./scripts/config --disable DEBUG_INFO
    make -j$(nproc) deb-pkg

Will take 1.5 - 2 hours on the Raspberry Pi 3.

**(12)** Install your brand new realtime kernel:

    sudo dpkg -i ../*rt10*.deb

Open up /boot/config.txt and add the following line to it: 

    kernel=vmlinuz-4.14.14-rt10-v7 

If you work with a different kernel version, the value to use behind "kernel=" is the filename that is printed by this command: `(cd /boot/ && ls -1 vmlinuz*rt10*)`.

**(13)** Reboot and make sure your realtime kernel is running:

    sudo reboot
    
    ssh pi@192.168.0.100
    uname -a
    
The output should start with `Linux raspberrypi 4.14.14-rt10-v7`, indicating it is a realtime kernel.

**(14)** Ensure your system is running stable with the realtime kernel, by running tests like the following for a few minutes (while letting the Raspberry Pi 3 do other tasks in parallel):

    cd ~
    git clone git://git.kernel.org/pub/scm/linux/kernel/git/clrkwllms/rt-tests.git
    cd rt-tests/
    make
    sudo ./cyclictest -m -t1 -p 80 -n -i 500 -l 100000
    sudo ./cyclictest -m -t4 -p 80 -n -i 500 -l 100000

For details about `cyclictest`, see:

* `cyclictest -h`
* [official documentation webpage](https://wiki.linuxfoundation.org/realtime/documentation/howto/tools/cyclictest)
* "[Latency of Raspberry Pi 3 on Standard and Real-Time Linux 4.9 Kernel](https://medium.com/@metebalci/-2d9c20704495)"


## 3. References

The following contains background reading material about realtime Linux, beyond what is an immediate source linked in the instructions above:

* [Real-time Linux explained, and contrasted with Xenomai and RTAI](http://linuxgizmos.com/real-time-linux-explained/)
* [bits and pieces: Raspberry Pi & RT Preempt](https://isojed.nl/blog/2017/10/25/raspberry-pi-rt-preempt/)
* [autostatic.com: RPi 3 and the Real Time Kernel](https://autostatic.com/2017/06/27/rpi-3-and-the-real-time-kernel/)
