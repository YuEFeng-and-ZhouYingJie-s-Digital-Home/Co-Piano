#!/usr/bin/expect -f
# gpu.sh — 在 4090 机器上跑单条命令,自动输入密码,带超时
# Usage: gpu.sh "command" [timeout_sec]
#   timeout_sec 默认 30
set timeout [lindex $argv 1]
if {$timeout eq ""} { set timeout 30 }
set cmd [lindex $argv 0]

spawn ssh -p 29955 -o StrictHostKeyChecking=no -o ConnectTimeout=8 root@connect.bjb2.seetacloud.com "$cmd"
expect "password:"
send "vEOra3BpuGhC\r"
expect eof
