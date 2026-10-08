#!/bin/sh
#规避方法解决系统异常卡死并不能自动重启
echo "enable 1 interval 15" >/proc/watchdog_cmd
insmod /lib/modules/kwdog.ko
#watchdog_start()
#{
	
#	echo 1 >/proc/watchdog_kick
#}
#while true; do watchdog_start; sleep 5; done 
