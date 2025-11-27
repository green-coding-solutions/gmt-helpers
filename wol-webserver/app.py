from flask import Flask
import subprocess

local_network_submask='192.168.178.255'
machine_mac_address='33:aa:2b:1a:db:dd'

app = Flask(__name__)

@app.route('/')
def hello():
    try:
        subprocess.run(['wakeonlan', '-i', local_network_submask, '-p', '1234', machine_mac_address], check=False)
    except:
        pass
    return ""

if __name__ == "__main__":
    app.run()
