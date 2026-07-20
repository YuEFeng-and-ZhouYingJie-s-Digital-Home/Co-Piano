#!/usr/bin/expect -f
# gpu_run.sh — 类似 gpu.sh 但 timeout 长,适合慢命令
# Usage: gpu_run.sh "command" [timeout_sec]
set timeout [lindex $argv 1]
if {$timeout eq ""} { set timeout 300 }
set cmd [lindex $argv 0]

spawn ssh -p 29955 -o StrictHostKeyChecking=no -o ConnectTimeout=8 root@connect.bjb2.seetacloud.com "$cmd"
expect "password:"
send "vEOra3BpuGhC\r"
expect eof
