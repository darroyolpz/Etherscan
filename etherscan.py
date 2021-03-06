# https://etherscan.io/apis
import time, dateparser, json, sys, os, requests
from discord_webhook import DiscordWebhook
from datetime import datetime
import pandas as pd

# API key
api_key = os.environ.get('ETHERSCAN_API')

# Discord Webhook
url_wb = os.environ.get('DISCORD_WH')

# Get token address
#path = "/home/pi/OpenAlpha/alts.xlsx"
path = 'alts.xlsx'
df = pd.read_excel(path)

# Get exchanges
#ex_path = "/home/pi/OpenAlpha/exchanges.xlsx"
ex_path = 'exchanges.xlsx'
df_ex = pd.read_excel(ex_path)
exchanges = df_ex['Address'].values

# Hash db
#hash_path = "/home/pi/OpenAlpha/hash.xlsx"
hash_path = 'hash.xlsx'
df_hash = pd.read_excel(hash_path)
updated_list = []

# Get eth balance from address
def eth_balance(address):
    url = "https://api.etherscan.io/api?module=account&action=balance&address=" + address + "&tag=latest&apikey=" + api_key
    response = requests.get(url).text
    value = json.loads(response)
    eth_value = float(value['result'])/1e18
    print(eth_value)

# Get transactions
def get_trans(address):
    url = "https://api.etherscan.io/api?module=account&action=txlist&address=" + address + "&startblock=0&endblock=9999999999&sort=desc&apikey=" + api_key
    response = requests.get(url).text
    value = json.loads(response)['result']
    #print(value)
    transactions_number = len(value)
    print('Number of transactions:', transactions_number, '\n')

    # Rate Limiter
    with rate_limiter:
        for val in value:
            block = val['blockNumber']
            t_hash = val['hash']
            sender = val['from']
            recipient = val['to']
            qty = val['value']
            timeStamp = val['timeStamp']
            print('Hash:', t_hash)
            print('Quantity:', qty)
            print('Block:', block, '\n')

def hash_info(t_hash):
    url = "https://api.etherscan.io/api?module=account&action=txlistinternal&txhash=" + t_hash + "&apikey=" + api_key
    response = requests.get(url).text
    value = json.loads(response)
    print(value)

# Main function
def contract_info(token, contract, pag=300):
    url = "https://api.etherscan.io/api?module=account&action=tokentx&contractaddress=" + contract + "&page=1&offset=" + str(pag) + "&sort=desc&apikey=" + api_key
    response = requests.get(url).text
    value = json.loads(response)['result']

    # Transactions limit
    actual_price = price(token)
    usd_limit = 1e6 
    qty_limit = usd_limit/actual_price
    print(token, 'at', actual_price, '| Qty limit:', qty_limit)
    transactions_number = len(value)
    #print('Number of transactions:', transactions_number, '\n')

    for val in value:
        tokenSymbol = val['tokenSymbol']
        block = val['blockNumber']
        timeStamp = val['timeStamp']
        t_hash = val['hash']
        site = 'https://etherscan.io/tx/' + t_hash
        sender = val['from']
        recipient = val['to']
        qty = float(val['value'])/1e18
        qty_usd = qty*actual_price/1e6 # In millions

        # Check limits and hashes
        if (qty > qty_limit) & (t_hash not in df_hash.values):
            # Update hash list
            updated_list.append(t_hash)
            
            # Check deposits and withdrawals
            if (recipient in exchanges) & (recipient not in exchanges):
                ex_name = df_ex.loc[df_ex['Address'] == recipient, 'Exchange'].values[0]
                msg = f":shit: **Mimi** | **{token}** | **{qty_usd:.2f}M deposit from {ex_name}** | Oh shit...:small_red_triangle_down:\n{site}"
                discord(msg)
            elif (sender in exchanges) & (sender not in exchanges):
                ex_name = df_ex.loc[df_ex['Address'] == sender, 'Exchange'].values[0]
                msg = f":dove: **Mimi** | **{token}** | **{qty_usd:.2f}M withdrawal from {ex_name}** | Number go :up:\n{site}"
                discord(msg)       

def price(token):
    url = 'https://api.binance.com/api/v3/ticker/price?symbol=' + token + 'USDT'
    response = requests.get(url).text
    value = json.loads(response)
    actual_price = float(value['price'])
    return actual_price

def discord(msg):
    webhook = DiscordWebhook(url=url_wb, content=msg)
    response = webhook.execute()

# Execute
tokens, contracts = df['Token'], df['Contract']

for token, contract in zip(tokens, contracts):
    contract_info(token, contract, 100)
 
# Update hash
cols = ['Hash']
df_update = df_hash.append(pd.DataFrame(updated_list, columns=cols), ignore_index = True)
df_update.to_excel(hash_path, index = False)