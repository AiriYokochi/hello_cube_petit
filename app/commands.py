#!/usr/bin/env python

# Copyright (c) 2026 SoftBank Corp.
# 
# <<licensetext>>

RADICON_COMMANDS = [
    {
        "title": "前進",
        "command": "ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.2}, angular: {z: 0.0}}' -1",
        "desc": "ロボットを前に動かすよ"
    },
    {
        "title": "停止",
        "command": "ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.0}, angular: {z: 0.0}}' -1",
        "desc": "ロボットを止めるよ"
    },
    {
        "title": "右回転",
        "command": "ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.0}, angular: {z: -0.6}}' -1",
        "desc": "右にくるっと回るよ"
    },
]

TALK_COMMANDS = [
    {
        "title": "会話スタート",
        "command": "ros2 service call /enable_realtime_conversation std_srvs/srv/SetBool '{data: true}'",
        "desc": "お話モードをONにするよ"
    },
    {
        "title": "会話ストップ",
        "command": "ros2 service call /enable_realtime_conversation std_srvs/srv/SetBool '{data: false}'",
        "desc": "お話モードをOFFにするよ"
    },
    {
        "title": "状態確認",
        "command": "ros2 service call /get_realtime_conversation_status std_srvs/srv/Trigger '{}'",
        "desc": "会話が有効か確認するよ"
    },
]
