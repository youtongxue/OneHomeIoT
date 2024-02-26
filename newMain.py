import asyncio
import utime
from machine import Pin, PWM

from mqtt.mqtt_as import MQTTClient, config
from mqtt.mqtt_info import MqttService, MqttConfig
from message.message_info import RecMsg, SentMsg, BoardStatus
from board.board_info import BoardConfig, Device, DeviceAction, DeviceName, Board

# 必要
board = None
client = None

pwm_pin = None
# 设置PWM参数
frequency = 5000  # PWM频率，单位Hz
duty_cycle = 0  # PWM占空比，范围通常在0-1023之间


# 初始化ESP开发板，连接设备对象信息
async def _initBoard():
    global board, pwm_pin, frequency, duty_cycle
    
    board = Board(BoardConfig.BOARD_ID)
    
    # 初始化PWM
    pwm_pin = PWM(Pin(10, Pin.OUT))
    pwm_pin.freq(frequency)
    pwm_pin.duty(duty_cycle)
    
    # 转换为百分比，四舍五入到最接近的整数
    current_duty = pwm_pin.duty()
    duty_percent = (current_duty / 1023) * 100
    duty_percent_rounded = round(duty_percent)
        
    board.addDevice(Device(did="1", name=DeviceName.DESK_LAMP, data=str(duty_percent_rounded)))

    jsonData = board.toJson()
    print(f'Board info:\n{jsonData}\n')

async def my_callback():
    # 执行回调函数的逻辑
    print("Reconnect OK! Callback executed")
    
async def _initMqtt():
    global client
    
    connectStatus = True
    
    client = MqttService.buildClient(my_callback)
    print(f'Mqtt config:\n{config}\n')
    #await client.connect()
    
    while (connectStatus):
        try:
            # 一些可能引发异常的代码
            await client.connect()
            connectStatus = False
        except OSError as e:
            # 处理异常的代码
            print("连接异常:", e)

    # 订阅【控制命令】主题
    await client.subscribe(MqttConfig.SUB_TOPIC, 1) 
    # 发送ESP设备上线
    await pushOnlineMsg()
    # 发送传感器信息
    await pushBoardMsg()
    

# 接收消息异步回调函数
async def messages(client):
    async for topic, msg, retained in client.queue:
        # bytearray 可变的字节序列
        # print((topic, msg, retained))
        
        topicStr = topic.decode()
        msgStr = msg.decode()

        print(f'收到信息 topic:{topicStr} msg:{msgStr}')
        await parseData(client, topicStr, msgStr)
        

async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        
async def tickTask():
    tick = 0
    while True:
        print('tick', tick)
        await client.publish(MqttConfig.TICK_TOPIC, f'{BoardConfig.BOARD_ID} {tick}', qos = 1)
        tick += 1
        if tick == 11:
            tick = 1
        await asyncio.sleep(5)
    
# 响应操作
async def deviceAction(recMsg):
    global board, control_pin, pwm_pin, frequency, duty_cycle

    cmd = int(recMsg.cmd)
    print(f'响应指令:{cmd}')
    
    if cmd < 0 or cmd > 100:
        return
    # 将亮度等级转换为占空比
    duty = int(cmd / 100 * 1023)
    pwm_pin.duty(duty)
    # 引入短暂的延迟，以确保状态更新
    utime.sleep_ms(50)  # 例如延迟50毫秒
    
    await pushBoardMsg()  # 更新设备状态
    
        
# 解析Mqtt消息
async def parseData(client, topic, msg):
    global board
    
    # 保证Topic正确
    if topic == MqttConfig.SUB_TOPIC:
        
        recMsg = RecMsg()
        success = recMsg.fromJson(msg) # 解析数据

        if success:
            bid = recMsg.bid
            did = recMsg.did
            cmd = recMsg.cmd
            
            print(f'设备ID:{bid} 传感器ID:{did} 命令:{cmd}')
            # App上线，主动请求获取所有设备状态信息      
            if f'{bid} {did} {cmd}' == DeviceAction.APP_ON_LINE or f'{bid} {did} {cmd}' == DeviceAction.BOARD_INFO:
                # 发送ESP设备上线
                await pushOnlineMsg()
                # 发送传感器信息
                await pushBoardMsg()
                return
            
            # 其他控制信息，保证Board设备ID正确
            if bid == board.bid:
                # 保证Device的ID正确
                for device in board.devices:
                    if did == device.did:
                        await deviceAction(recMsg)
                        return
                print(f'无此挂载Device id:{did}')
        else:
            print("控制信息JSON解析错误")
            return

# 发送上线信息
async def pushOnlineMsg():
    global client

    boardStatusStr = BoardStatus(BoardConfig.BOARD_ID, BoardConfig.ON_LINE).toJson()
    msgStr = SentMsg(SentMsg.LINE_STATUS, boardStatusStr).toJson()
    await client.publish(MqttConfig.PUB_TOPIC, msgStr, qos = 1)

# 发送设备信息
async def pushBoardMsg():
    global client, board, control_pin
    
    # 转换为百分比，四舍五入到最接近的整数
    current_duty = pwm_pin.duty()
    duty_percent = (current_duty / 1023) * 100
    duty_percent_rounded = round(duty_percent)
    
    board.devices[0].data = str(duty_percent_rounded)
    
    msgStr = SentMsg(SentMsg.BOARD_INFO, board.toJson()).toJson()
    await client.publish(MqttConfig.PUB_TOPIC, msgStr, qos = 1)

    

async def main():
    global client
    
    await _initBoard()
    await _initMqtt()

    asyncio.create_task(up(client))
    # 读取消息
    asyncio.create_task(messages(client))
    # Tick主动保持连接
    asyncio.create_task(tickTask())
    # 业务逻辑
    #asyncio.create_task()
    
    while True:
        await asyncio.sleep(10000)
    
if __name__ == '__main__':    
    try:
        asyncio.run(main())
    finally:
        print('process done!')
        client.close()
