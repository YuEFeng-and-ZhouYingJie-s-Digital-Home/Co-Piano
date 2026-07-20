#!/usr/bin/expect -f
# gpu_probe.sh - 通过 SSH 探测 4090 服务器环境
set timeout 20
set host "root@connect.bjb2.seetacloud.com"
set port 29955
set pwd "vEOra3BpuGhC"
set cmd [lindex $argv 0]

spawn ssh -p $port -o StrictHostKeyChecking=no $host "$cmd"
expect "password:"
send "$pwd\r"
expect eof
