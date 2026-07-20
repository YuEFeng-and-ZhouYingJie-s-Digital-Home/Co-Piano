#!/usr/bin/expect -f
# ssh_run.sh — 在 4090 机器上跑单条命令,自动输入密码
# Usage: ssh_run.sh "command1; command2; ..."
set timeout 60
set host "root@connect.bjb2.seetacloud.com"
set port 29955
set pwd "vEOra3BpuGhC"
set cmd [lindex $argv 0]

spawn ssh -p $port -o StrictHostKeyChecking=no $host
expect "password:"
send "$pwd\r"
expect "\$ "
send "$cmd\r"
expect "\$ "
send "exit\r"
expect eof
