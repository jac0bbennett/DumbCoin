from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from datetime import datetime
from time import time
from base64 import b64encode, b64decode
from utils import AESCipher
from color import Color
import os, hashlib, json, socket, ast, pickle, getpass, sys

color = Color()

BUFFER_SIZE = 2048


class Wallet:
    def __init__(self, name, phrase):
        self.name = name
        self.phrase = phrase
        self.key = ''
        self.lastnode = []

        self.cmds = {
            'help': {'desc': 'Display help', 'func': self.help},
            'public': {'desc': 'Display public key', 'func': self.getPublicKey},
            'address': {'desc': 'Display wallet address', 'func': self.getAddress},
            'balance': {'desc': 'Display wallet balance', 'func': self.getBalance},
            'send': {'desc': 'Send transaction to address "send [amt] [to address]"', 'func': self.sendTx},
            'get': {'desc': 'Get transaction info "get [txhash]"', 'func': self.getTx},
            'last': {'desc': 'Get hash and value of last 20 transactions', 'func': self.getLast},
            'exit': {'desc': 'Exit wallet', 'func': None}
            }

    def sendNode(self, msg):
        if not os.path.isfile('walletconf.json'):
            print(color.E('\nMissing walletconf.json file!\n'))
        with open('walletconf.json', 'r') as config:
            conf = json.load(config)
        print('\nAttempting connection to node...\n')
        TCP_IP = conf["node"]["ip"]
        TCP_PORT = conf["node"]['port']
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((TCP_IP, TCP_PORT))
            s.send(bytes(str(msg), encoding='UTF-8'))
            data = s.recv(BUFFER_SIZE)
            if data:
                data = ast.literal_eval(data.decode('utf-8'))
                if 'error' in data:
                    print(color.E('\n'+data['error']+'\n'))
                if 'success' in data:
                    print(color.I('\n'+data['success']+'\n'))
                return data
        except ConnectionRefusedError:
            print(color.E('\nNode in config is unavailable!\n'))

    def getKey(self, cmd=False):
        if os.path.isfile('wallets/'+self.name+'.privkey'):
            with open('wallets/'+self.name+'.privkey', 'r', encoding='utf-8') as key:
                encKey = key.read()
                enc = AESCipher(self.phrase)
                try:
                    self.key = enc.decrypt(encKey)
                except UnicodeDecodeError:
                    print(color.E('\nIncorrect passphrase for wallet!\n'))
        else:
            self.key = False
            print(color.E('\nWallet not found!\n'))

    def getPublicKey(self, cmd=False):
        if self.key:
            rsakey = RSA.importKey(self.key)
            pub = rsakey.publickey().exportKey().decode('utf-8')
            if cmd:
                print(pub)
            return pub
        else:
            print(color.E('\nNo wallet key initiated!\n'))

    def getAddress(self, cmd=False):
        if self.key:
            rsakey = RSA.importKey(self.key)
            pub = rsakey.publickey().exportKey().decode('utf-8')
            adr = hashlib.sha256(bytes(pub, encoding='utf-8')).hexdigest()
            if cmd:
                print(adr)
            return adr
        else:
            print(color.E('\nNo wallet key initiated!\n'))

    def getBalance(self, cmd=False):
        msg = {"balance": self.getAddress()}
        check = self.sendNode(msg)
        if check:
            print('Balance:')
            print(check['balance'])
        else:
            print(color.E('\nCould not get balance from node!\n'))

    def sendTx(self, params, cmd=False):
        if len(params) < 2:
            print(color.E('\nTx missing parameters'))
        else:
            # amt, to
            amt = float(params[0])
            to = params[1]
            if len(to) == 64:
                tx = self.genTx(amt, to)
                self.sendNode(tx)
            else:
                print(color.E('\nAddress is not correct length!'))


    def genTx(self, amt, to, cmd=False):
        if self.key:
            rsakey = RSA.importKey(self.key)
            signer = PKCS1_v1_5.new(rsakey)
            digest = SHA256.new()
            tx = {
                    "from": self.getAddress(),
                    "time": time(),
                    "to": to,
                    "value": amt
                }
            data = tx['from'] + '->' + tx['to'] + ':' + str(tx['value']) + ':' + str(tx['time'])
            txhash = hashlib.sha256(bytes(data, encoding='utf-8')).hexdigest()
            digest.update(bytes(str(txhash), encoding='utf-8'))
            sign = signer.sign(digest)
            sign = b64encode(sign).decode('utf-8')
            msg = { "hash": txhash,
                    "tx": tx,
                    "public_key": self.getPublicKey(),
                    "signature": sign
                 }
            return msg
        else:
            print(color.E('\nNo wallet key initiated!\n'))
            return 0

    def getTx(self, params, cmd=False):
        if len(params) < 1:
            print(color.E('\nCommand missing parameters'))
        else:
            hash = params[0]
            if len(params) > 1:
                incSig = int(params[1])
            else:
                incSig = 0
            if incSig != 0:
                incSig = 1
            msg = {'getTx': hash, 'incSig': incSig}
            tx = self.sendNode(msg)
            info = tx['txInfo']
            print('Transaction:\n')
            print(info['from'] + ' ' + str(info['value']) + '-> ' + info['to'] + '\n')
            print('Time: ' + str(info['time']) + '\n')
            if 'public_key' in info:
                print('Public Key: ' + info['public_key'] + '\n')
            if 'signature' in info:
                print('Signature: ' + info['signature'] + '\n')

    def getLast(self, cmd=False):
        msg = {'recent': self.getAddress()}
        txs = self.sendNode(msg)
        if txs:
            print('Latest Transactions:\n')
            txs = txs['txs']
            for t in sorted(txs):
                print(txs[t]['hash'])
                if txs[t]['value'][0] == '-':
                    print(color.E(txs[t]['value']+'\n'))
                else:
                    print(color.I(txs[t]['value']+'\n'))

    def help(self, cmd=False):
        print('Commands:')
        for cmd, val in self.cmds.items():
            print(cmd.ljust(15) + val['desc'])

def walletPrompt(wallet):
    cmd = input('> ')
    print('\n')
    if cmd.split(' ')[0] == 'send' or cmd.split(' ')[0] == 'get':
        cmd = cmd.split(' ')
        params = cmd[1:]
        wallet.cmds[cmd[0]]['func'](params, cmd=True)
    elif cmd.split(' ')[0] == 'exit':
        sys.exit(0)
    else:
        try:
            wallet.cmds[cmd]['func'](cmd=True)
        except KeyError:
            print(color.E('Unknown command!'))
    print('\n')
    walletPrompt(wallet)


def openWallet():
    name = input('Wallet Name ("[new]" to create wallet): ')
    if name != '[new]':
        if not os.path.isfile('wallets/'+name+'.privkey'):
            print(color.E('\nWallet not found!\n'))
            openWallet()
        phrase = getpass.getpass('Passphrase: ')
        wallet = Wallet(name, phrase)
        wallet.getKey()
        if wallet.key:
            print(color.I('\nOpened wallet '+wallet.name +'\n'))
            print('\nType "help" to view commands\n')
            walletPrompt(wallet)
        else:
            openWallet()
    else:
        name = input('New wallet name: ')
        phrase = getpass.getpass('New passphrase for wallet: ')
        if not os.path.isfile('wallets/'+name+'.privkey'):
            newkey = RSA.generate(3072)
            privkey = newkey.exportKey().decode('utf-8')
            with open('wallets/'+name+'.privkey', 'a') as privf:
                enc = AESCipher(phrase)
                encKey = enc.encrypt(privkey)
                privf.write(str(encKey))
            print(color.I('Wallet created successfully!\n'))
            openWallet()
        else:
            print('Wallet with name "'+name+'" already exists!')
            openWallet()

if __name__ == "__main__":
    print(color.M('\n'+"""
    ______                 _     _____       _
    |  _  \               | |   /  __ \     (_)
    | | | |_   _ _ __ ___ | |__ | /  \/ ___  _ _ __
    | | | | | | | '_ ` _ \| '_ \| |    / _ \| | '_ \\
    | |/ /| |_| | | | | | | |_) | \__/\ (_) | | | | |
    |___/  \__,_|_| |_| |_|_.__/ \____/\___/|_|_| |_|


            """
            +"""                            Wallet v1.0.0
                         Updated: December 14th, 2017
                               Developed by Jwb.Cloud\n
            """))
    if not os.path.exists('wallets'):
        os.makedirs('wallets')
    openWallet()
