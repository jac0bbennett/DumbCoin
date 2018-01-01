# DumbCoin

![alt text](https://github.com/jac0bbennett/DumbCoin/blob/master/src/wallet/logo.png "Logo")

DumbCoin is a revolutionary new blockchain-less cryptocurrency made by a kid with little experience in the field.

### Specs:
* Instant transactions
* Zero fee
* SqliteDB ledger allowing for easy data access by apps
* 100% instamined
* Susceptible to double spending


## How to Use
1. Download and unzip the [wallet](https://www.dropbox.com/s/788nwndlughhqso/DC-wallet_windows_1.0.0.zip?dl=1).
2. In the `walletconf.json` you will put in the node you would like to connect to. It is defaulted to live node ran by us.
3. To create a new dumbcoin wallet, run the `DC-wallet.exe` and type `[new]`. Then enter the name for the wallet as well as a passphrase to secure it.
4. To check your balance type `balance` and it will be retrieved from the node.
5. To send a transaction type `send` followed by the value and address you would like to send to. (Ie. `send 10 4712f91a0a7642d5a6d05f8ab439cc3c3a9bc88477b935fff94e7725fe9e30c7`). The wallet will generate the transaction and a node will relay it to the rest of the network.
6. Backup the your `.privkey` file in the wallets folder that it creates. This is an encrypted private key to access your wallet.

## How to run a node
1. Download the `DC-node` executable for either [linux](https://www.dropbox.com/s/ygi352nbh7edvbo/DC-node_linux_1.0.0.zip?dl=1) or [windows](https://www.dropbox.com/s/vkmsypbudj9rkin/DC-node_windows_1.0.0.zip?dl=1).
2. In the `nodeconf.json` you can set the port to run on. Port `5005` is recommended.
3. Also in the config file, make sure you have a default node set so it can initially connect to the network.
4. To start the node on windows, double click the exe and make sure there isn't an error. The window must remain open for it to run on windows.
5. On linux, change to the directory that the executable is located in and type `./DC-node` into the terminal. If there aren't any errors, cancel it and run `nohup ./DC-node &` to run it in the background.
6. Following the DumbCoin policy, there is no error logging.

## About
I started working on this in August 2017, but really only got the wallet and a minimal amount of node work done. I didn't make a goal to finish it until early December. I rewrote the node code, added some features, and compiled it using PyInstaller. It's a dumb coin but it works and I don't think there are many 17 year olds making their own cryptocurrency. This was done as a fun project and is not meant to be actually used. The code is poorly written and it probably isn't protected very well against double spending. If you'd like to try it out and get some free coins, you can use my links on [jacobbennett.us](https://jacobbennett.us) to contact me.
