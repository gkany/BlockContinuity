# -*- coding:utf-8 -*-

import os
import re
import json
import logging
import requests
import datetime as dt
from time import sleep
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler
from PythonMiddleware.notify import Notify
from PythonMiddleware.graphene import Graphene
from PythonMiddlewarebase.operationids import operations

class SubFormatter(logging.Formatter):
    converter=dt.datetime.fromtimestamp
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s,%03d" % (t, record.msecs)
        return s

class Logging(object):
    def __init__(self, log_dir='./logs', log_name='server', console=True):
        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(logging.DEBUG)
        formatter = SubFormatter(fmt='%(asctime)s [%(name)s] [%(funcName)s:%(lineno)s] [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S.%f')

        # file handler
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = log_dir + '/' + log_name
        fh = TimedRotatingFileHandler(filename=log_file, when="H", interval=1, backupCount=3*24)
        fh.suffix = "%Y-%m-%d_%H-%M.log"
        fh.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}.log$")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        # console handler
        if console:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

    def getLogger(self):
        return self.logger

headers = {"content-type": "application/json"}

nodeaddress = "wss://api.cocosbcx.net" #mainnet

token = "xxx"
alert_address = "https://oapi.dingtalk.com/robot/send?access_token="+token

logger = Logging().getLogger()

global_last_block_num = -1

def send_message(messages, label=['faucet']):
    try:
        body_relay = {
            "jsonrpc": "2.0",
            "msgtype": "text",
            "text": {
                "content": str(label) + str(messages)
            },
            "id":1
        }
        response = json.loads(requests.post(alert_address, data = json.dumps(body_relay), headers = headers).text)
        logger.debug('request response: {}'.format(response))
    except Exception as e:
        logger.error("task error: '{}'".format(repr(e)))


def listen_block():
    def on_block_callback(recv_block_id):
        global global_last_block_num
        info = gph.info()
        # logger.debug('info: {}'.format(info))
        head_block_id = info['head_block_id']
        head_block_number = info['head_block_number']
        # logger.debug('head_block_num {}, recv_block_id: {}, head_block_id {}'.format(head_block_number, recv_block_id, head_block_id))
        if recv_block_id == head_block_id:
            if head_block_number != global_last_block_num+1:
                if global_last_block_num > 0:
                    logger.info('head_block_num {}, recv_block_id: {}, head_block_id {}'.format(head_block_number, recv_block_id, head_block_id))
                    logger.warn('current block num: {}, last block num: {}'.format(head_block_number, global_last_block_num))
                    #send message
            global_last_block_num = head_block_number
        else:
            try:
                logger.info('head_block_num {}, recv_block_id: {}, head_block_id {}'.format(head_block_number, recv_block_id, head_block_id))
                block = gph.rpc.get_block(global_last_block_num+1)
                global_last_block_num = global_last_block_num+1
                logger.warn('>> get_block {}, recv_block_id: {}, head_block_id: {}, get block response： {}'.format(
                    global_last_block_num, recv_block_id, head_block_id, block['block_id']))
            except Exception as e:
                logger.error('get_block exception. block {}, error {}'.format(global_last_block_num+1, repr(e)))

    gph = Graphene(node=nodeaddress)
    from PythonMiddleware.instance import set_shared_graphene_instance
    set_shared_graphene_instance(gph)
    notify = Notify(
        on_block = on_block_callback,
        graphene_instance = gph
    )
    notify.listen()

def main():
    listen_block()

if __name__ == '__main__':
    main()
