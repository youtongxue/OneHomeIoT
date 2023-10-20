from mqtt_as import MQTTClient, config
import asyncio
import machine

# 定义 Light 状态
LIGHT_CLIENT_ID = '1'    		#连接ID
LIGHT_OFF_LINE = '0'
LIGHT_ON_LINE = '1'
LIGHT_TURN_OFF = '2'
LIGHT_TURN_ON = '3'

# 定义 App 状态
APP_ID = '0'
APP_OFF_LINE = '0'
APP_ON_LINE = '1'

SUB_TOPIC = 'onehome_ctrl'    	#订阅的主题
PUB_TOPIC = 'onehome_info'    	#发布的主题

# 定义针脚
pin_5 = None

# Local configuration
config['ssid'] = 'Mi 10'
config['wifi_pw'] = '00000000'
config['server'] = '124.221.158.155'
config["queue_len"] = 1
config['will'] = (PUB_TOPIC, f'{LIGHT_CLIENT_ID} {LIGHT_OFF_LINE}', False, 1)
MQTTClient.DEBUG = True

# 初始化 Pin
def initPin():
    global pin_5
    pin_5 = machine.Pin(5, machine.Pin.OUT)
    print("初始化Pin完成...")

# 开机
async def machinePowerOn(client):
    initPin()
    await client.subscribe(SUB_TOPIC, 1) # 订阅
    await client.publish(PUB_TOPIC, f'{LIGHT_CLIENT_ID} {LIGHT_ON_LINE}', qos = 1) # 上线
    # 发送状态
    status = LIGHT_TURN_ON if pin_5.value() == 1 else LIGHT_TURN_OFF           
    await client.publish(PUB_TOPIC, f'{LIGHT_CLIENT_ID} {status}', qos = 1)
    
# 开灯 | 关灯
def lightAction(action):
    global pin_5
    
    if action == LIGHT_TURN_OFF:
        print("关灯")
        pin_5.value(0)
    elif action == LIGHT_TURN_ON:
        print("开灯")
        pin_5.value(1)
        
# 解析接收数据，并响应
async def parseDataAndAction(client, topic, msg):
    if topic == SUB_TOPIC:
        # 解析数据
        data = msg.split()
        print(f'设备号: {data[0]} -> 操作: {data[1]}')
        
        if data[0] == APP_ID and data[1] == APP_ON_LINE:
            # 返回状态
            status = LIGHT_TURN_ON if pin_5.value() == 1 else LIGHT_TURN_OFF           
            await client.publish(PUB_TOPIC, f'{LIGHT_CLIENT_ID} {status}', qos = 1)
        if data[0] == LIGHT_CLIENT_ID:
            # 响应操作        
            lightAction(data[1])
            await client.publish(PUB_TOPIC, msg, qos = 1)

# 接收消息异步回调函数
async def messages(client):
    async for topic, msg, retained in client.queue:
        # bytearray 可变的字节序列
        # print((topic, msg, retained))
        
        topic_str = topic.decode()
        msg_str = msg.decode()

        print(f'收到信息: {(topic_str, msg_str, retained)}')
        await parseDataAndAction(client, topic_str, msg_str)
        

async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        # 开机
        await machinePowerOn(client)

async def main(client):
    await client.connect()
    for coroutine in (up, messages):
        asyncio.create_task(coroutine(client))
    n = 0
    while True:
        await asyncio.sleep(5)
        print('publish', n)
        await client.publish('tick', f'CLIENT_ID {}'.format(n), qos = 1)
        n += 1

if __name__ == '__main__':
    client = MQTTClient(config)
    try:
        asyncio.run(main(client))
    finally:
        client.close()

