from board.board_info import BoardConfig
from message.message_info import BoardStatus, SentMsg
from mqtt.mqtt_as import MQTTClient, config

class MqttConfig:
    SUB_TOPIC = 'onehome_ctrl'    	#订阅的主题
    PUB_TOPIC = 'onehome_info'    	#发布的主题
    TICK_TOPIC = 'tick'				#保持连接主题
    
    SSID = 'Mi 10'
    WIFI_PW = '00000000'
    SERVER = '124.221.158.155'
    PORT = 1883
    
    boardStatusStr = BoardStatus(BoardConfig.BOARD_ID, BoardConfig.ON_LINE).toJson()
    msgStr = SentMsg(SentMsg.LINE_STATUS, boardStatusStr).toJson()
    WILL = (PUB_TOPIC, msgStr, False, 1)
    
    QUEUE_LEN = 1
    
    MQTTClient.DEBUG = True

class MqttService:
        
    def buildClient(reconnect_callback):
        # 连接配置
        config['ssid'] = MqttConfig.SSID
        config['wifi_pw'] = MqttConfig.WIFI_PW
        config['server'] = MqttConfig.SERVER
        config['port'] = MqttConfig.PORT
        config['will'] = MqttConfig.WILL
        config["queue_len"] = MqttConfig.QUEUE_LEN
        
        client = MQTTClient(config, callback_reconnect_ok=reconnect_callback)
        
        return client

