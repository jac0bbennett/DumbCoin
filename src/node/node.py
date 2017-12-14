import socket, threading, ast, os, json, sqlite3, hashlib, sys
from datetime import datetime
from color import Color
from base64 import b64encode, b64decode
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from time import time

color = Color()

fallbackNode = (None,)
tcpport = 5005

with open('nodeconf.json', 'r') as config:
    conf = json.load(config)
    fallbackNode = (conf['defaultnode']['ip'], conf['defaultnode']['port'])
    tcpport = conf['settings']['port']


print(color.M('\n'+"""
______                 _     _____       _
|  _  \               | |   /  __ \     (_)
| | | |_   _ _ __ ___ | |__ | /  \/ ___  _ _ __
| | | | | | | '_ ` _ \| '_ \| |    / _ \| | '_ \\
| |/ /| |_| | | | | | | |_) | \__/\ (_) | | | | |
|___/  \__,_|_| |_| |_|_.__/ \____/\___/|_|_| |_|


        """
        +"""                              Node v1.0.0
                     Updated: December 13th, 2017
                           Developed by Jwb.Cloud\n
        """))


class Node:
    def __init__(self, port):
        self.TCP_IP = '0.0.0.0'
        self.TCP_PORT = port
        self.BUFFER_SIZE = 2048

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((self.TCP_IP, self.TCP_PORT))
        self.s.listen(5)

        self.height = self.dbQuery('tx', 'SELECT COUNT(*) FROM tx')['COUNT(*)']
        self.targetheight = 0

        self.dbQuery('nodes', '')

    def acceptCons(self):
        conn, addr = self.s.accept()
        start = threading.Thread(target=self.receive, kwargs={'conn': conn, 'addr': addr[0]})
        start.daemon = True
        start.start()

    def retSuccess(self, conn, msg):
        msg = {'success': msg}
        conn.send(bytes(str(msg), encoding='utf-8'))
        conn.close()

    def retError(self, conn, error):
        msg = {'error': error}
        conn.send(bytes(str(msg), encoding='utf-8'))
        conn.close()

    def receive(self, conn, addr=''):
        data = conn.recv(self.BUFFER_SIZE)
        if data:
            data = data.decode('utf-8')
            print("received data:", data)
            try:
                data = ast.literal_eval(data)
            except ValueError:
                conn.close()
                return
            if 'declare_node' in data and data['declare_node'] != 0:
                self.addNode((addr, data['declare_node']))
                q = self.dbQuery('nodes', 'SELECT * FROM nodes', qt='all')
                count = 0
                addrs = {'nodes': []}
                for i in reversed(q):
                    if count < 10:
                        count += 1
                        if addr == i['ip'] and data['declare_node'] == i['port']:
                            pass
                        else:
                            addrs['nodes'].append((i['ip'], i['port']))
                    else:
                        break
                conn.send(bytes(str(addrs), encoding='utf-8'))
            elif 'sync' in data:
                starttx = data['sync']
                txs = self.dbQuery('tx', 'SELECT * FROM tx WHERE time>? ORDER BY time ASC', (data['sync'],), qt='all')
                count = self.dbQuery('tx', 'SELECT COUNT(*) FROM tx WHERE time>? ORDER BY time ASC', (data['sync'],))['COUNT(*)']
                respaddr = (addr, data['port'])
                for t in txs:
                    tx = {"from": t['sender'], "time": t['time'], "to": t['receiver'], "value": t['value']}
                    msg = {"hash": t['hash'], "tx": tx, "public_key": t['public_key'], "signature": t['signature']}
                    self.sendBroadcast(msg, respaddr)
            elif 'check_height' in data and data['check_height'] != 0:
                msg = {'height': self.height}
                conn.send(bytes(str(msg), encoding='utf-8'))
            elif 'balance' in data and data['balance'] != 0:
                q = self.dbQuery('balances', 'SELECT * FROM balances WHERE address=?', (data['balance'],))
                if q:
                    msg = {'balance': q['balance']}
                else:
                    msg = {'balance': 0}
                conn.send(bytes(str(msg), encoding='utf-8'))
            elif 'tx' in data:
                txhash = data['tx']['from'] + '->' + data['tx']['to'] + ':' + str(data['tx']['value']) + ':' + str(data['tx']['time'])
                txhash = hashlib.sha256(bytes(txhash, encoding='utf-8')).hexdigest()
                datahash = data['hash']
                lasttx = self.dbQuery('tx', 'SELECT * FROM tx WHERE sender=? ORDER BY time DESC', (data['tx']['from'],))
                if txhash != datahash:
                    self.retError(conn, 'Tx Hash could not be verified!')
                    return 0
                elif ((data['tx']['time'] > (time() + 90)) or (data['tx']['time'] < (time() - 90))) and self.targetheight == self.height:
                    self.retError(conn, 'Tx Time appears to be incorrect!')
                    return 0
                elif data['tx']['from'] == data['tx']['to']:
                    self.retError(conn, 'You cannot send funds to self!')
                    return 0
                rsakey = RSA.importKey(data['public_key'])
                signer = PKCS1_v1_5.new(rsakey)
                digest = SHA256.new()
                digest.update(bytes(str(txhash), encoding='utf-8'))
                checksig = signer.verify(digest, b64decode(data['signature']))
                if not checksig:
                    self.retError(conn, 'Tx Signature could not be verified!')
                    return 0
                elif hashlib.sha256(bytes(data['public_key'], encoding='utf-8')).hexdigest() != data['tx']['from']:
                    self.retError(conn, 'Tx Public_key does not match Address!')
                    return 0
                else:
                    n = self.dbQuery('tx', 'SELECT * FROM tx WHERE hash=?', (data['hash'],))
                    c = self.dbQuery('balances', 'SELECT * FROM balances WHERE address=?', (data['tx']['from'],))
                    r = self.dbQuery('balances', 'SELECT * FROM balances WHERE address=?', (data['tx']['to'],))
                    lasttx = self.dbQuery('tx', 'SELECT * FROM tx WHERE sender=? ORDER BY time DESC', (data['tx']['from'],))
                    if c and (c['balance'] < data['tx']['value']):
                        if lasttx['tx']['time'] > data['tx']['time']:
                            addback = lasttx['tx']['value'] + c['balance']
                            self.dbQuery('tx', 'DELETE FROM tx WHERE hash=?', (lasttx['hash'],))
                            self.dbQuery('balances', "UPDATE balances SET balance=? WHERE address=?", (addback,data['tx']['from']))
                    elif not c or (c['balance'] < data['tx']['value']):
                        self.retError(conn, 'Insufficient funds!')
                        return 0
                    if n:
                        self.retError(conn, 'Tx with that hash has already been submitted!')
                        return 0
                    elif not n:
                        self.dbQuery('tx', "INSERT INTO tx VALUES (?,?,?,?,?,?,?)",
                            (data['hash'], data['tx']['from'], data['tx']['to'], data['tx']['value'], data['tx']['time'], data['public_key'], data['signature']))
                        newSendBal = c['balance'] - data['tx']['value']
                        self.dbQuery('balances', "UPDATE balances SET balance=? WHERE address=?", (newSendBal,data['tx']['from']))
                        if r:
                            newRecBal = r['balance'] + data['tx']['value']
                            self.dbQuery('balances', "UPDATE balances SET balance=? WHERE address=?", (newRecBal,data['tx']['to']))
                        else:
                            self.dbQuery('balances', "INSERT INTO balances VALUES (?,?)", (data['tx']['to'],data['tx']['value']))
                    self.height += 1
                    self.targetheight += 1
                    self.retSuccess(conn, 'Transaction sent!')
                    self.broadcast(data)
            conn.close()
            return data

    def checkHeight(self, tries=0):
        msg = {'check_height': 1}
        addr = self.getANode()
        check = self.sendBroadcast(msg, addr)
        if check:
            if check['height'] > self.height:
                self.targetheight = check['height']
                lasttx = self.dbQuery('tx', 'SELECT * FROM tx ORDER BY time DESC')
                msg = {'sync': lasttx['time'], 'port': self.TCP_PORT}
                self.sendBroadcast(msg, addr, recv=False)
        elif tries < self.dbQuery('nodes', 'SELECT COUNT(*) FROM nodes')['COUNT(*)']:
            tries += 1
            self.checkHeight(tries)
        else:
            print('Error! Could not get network height!')

    def getANode(self):
        q = self.dbQuery('nodes', "SELECT * FROM nodes ORDER BY RANDOM() LIMIT 1;")
        return (q['ip'], q['port'])

    def broadcast(self, msg, addr=None):
        start = threading.Thread(target=self.sendBroadcast, kwargs={'msg': msg, 'addr': addr})
        start.daemon = True
        start.start()

    def sendBroadcast(self, msg, addr=None, recv=True):
        try:
            if addr:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.connect((addr[0], addr[1]))
                conn.send(bytes(str(msg), encoding='UTF-8'))
                if recv:
                    data = self.receive(conn)
                else:
                    data = ''
                conn.close()
                self.addNode(addr)
                return data
            else:
                q = self.dbQuery('nodes', 'SELECT * FROM nodes', qt='all')
                for i in q:
                    addr = (i['ip'], i['port'])
                    self.broadcast(msg, addr)
        except ConnectionRefusedError:
            if not addr:
                addr = ('node', 0)
            print('Error connecting to ' + addr[0] + ':' + str(addr[1]))
            #self.removeNode(addr) #Adjust banning system
            return 0

    # addr consists of ip and port
    def declareTo(self, addr):
        msg = {"declare_node": self.TCP_PORT}
        declare = self.sendBroadcast(msg, addr)
        if declare != 0 and 'nodes' in declare:
            if start.dbQuery('nodes', 'SELECT COUNT(*) FROM nodes')['COUNT(*)'] < 2:
                for n in declare['nodes']:
                    self.addNode(n)
                self.addNode(addr)
        else:
            print(color.E('\nCould not connect to network!\n'))
            sys.exit(0)


    def addNode(self, addr):
        n = self.dbQuery('nodes', 'SELECT * FROM nodes WHERE ip=? AND port=?', (addr[0], addr[1]))
        if not n:
            self.dbQuery('nodes', "INSERT INTO nodes VALUES (?,?)", (addr[0], addr[1]))

    def removeNode(self, addr):
        self.dbQuery('nodes', 'DELETE FROM nodes WHERE ip=? AND port=?', (addr[0], addr[1]))

    def dbQuery(self, db, q, val='', qt='one'):
        selDb = sqlite3.connect(db+'.db')
        selDb.row_factory = sqlite3.Row
        n = selDb.cursor()
        if db == 'nodes':
            n.execute('''CREATE TABLE IF NOT EXISTS nodes
                         (ip text, port int)''')
            selDb.commit()
        elif db == 'tx':
            n.execute('''CREATE TABLE IF NOT EXISTS tx
                         (hash text unique, sender text, receiver text, value float, time float, public_key text, signature text)''')
            selDb.commit()
        elif db == 'balances':
            n.execute('''CREATE TABLE IF NOT EXISTS balances
                         (address text unique, balance float)''')
            selDb.commit()
        n.execute(q, val)
        selDb.commit()
        if qt == 'one':
            v = n.fetchone()
        elif qt == 'all':
            v = n.fetchall()
        else:
            v = n
        selDb.close()
        return v

    def genesisTx(self):
        if self.height == 0:
            self.dbQuery('tx', 'INSERT INTO tx VALUES (?,?,?,?,?,?,?)', ('0', '0', '4712f91a0a7642d5a6d05f8ab439cc3c3a9bc88477b935fff94e7725fe9e30c7', 10000000, 0, '0', '0'))
            self.dbQuery('balances', 'INSERT INTO balances VALUES (?,?)', ('4712f91a0a7642d5a6d05f8ab439cc3c3a9bc88477b935fff94e7725fe9e30c7', 100000000))

start = Node(tcpport)
if start.dbQuery('nodes', 'SELECT COUNT(*) FROM nodes')['COUNT(*)'] == 0:
    start.declareTo(fallbackNode)
if start.height == 0:
    start.genesisTx()
connect = start.checkHeight()
if connect:
    print(color.I('\nConnected to network!\n'))

while True:
    start.acceptCons()
