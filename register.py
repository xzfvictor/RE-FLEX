"""
pbkdf2==1.3
pyaes==1.6.1
requests==2.28.1
"""


import uuid
import pyaes
from pbkdf2 import PBKDF2
import requests
import secrets
from urllib.parse import unquote, urlparse, parse_qs, urlencode
import base64
import hashlib
import hmac
import gzip
import json

from attestation import create_attestation_key, serialize_and_encode_keys

try:
    with open('userdata/useragent', 'r') as u:
        ua = u.read()
except:
    print("Please set the user agent")
    exit()

#APP_NAME = "com.amazon.rabbit"
#APP_VERSION = "303338310"
#DEVICE_NAME = "Le X522"
#MANUFACTURER = "LeMobile"
#OS_VERSION = "LeEco/Le2_NA/le_s2_na:6.0.1/IFXNAOP5801910272S/61:user/release-keys"

USER_AGENT = "AmazonWebView/Amazon Flex/0.0/iOS/15.7.8/iPhone"
APP_NAME = "Amazon Flex"
APP_VERSION = "0.0"
DEVICE_NAME = "iPhone"
MANUFACTURER = "APPLE"
OS_VERSION = "15.8"


DEVICE_TYPE = "A3NWHXTQ4EBCZS"
device_serial = "4347E00084E34635B3E0488E8331B18E"
device_id = secrets.token_hex(8)
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode()

device_type = "#" + DEVICE_TYPE
client_id = (device_serial.encode() + device_type.encode()).hex()
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b'=')
oauth_params = {
    "openid.oa2.response_type": "code",
    "openid.oa2.code_challenge_method": "S256",
    "openid.oa2.code_challenge": code_challenge,
    "openid.return_to": "https://www.amazon.com/ap/maplanding",
    "openid.assoc_handle": "amzn_device_na",
    "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
    "pageId": "amzn_device_na",
    "accountStatusPolicy": "P1",
    "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    "openid.mode": "checkid_setup",
    "openid.ns.oa2": "http://www.amazon.com/ap/ext/oauth/2",
    "openid.oa2.client_id": f"device:{client_id}",
    "openid.ns.pape": "http://specs.openid.net/extensions/pape/1.0",
    "openid.ns": "http://specs.openid.net/auth/2.0",
    "openid.pape.max_auth_age": "0",
    "openid.oa2.scope": "device_auth_access",
    "forceCaptcha": "true",
    "use_global_authentication": "false"
}
challenge_link = f"https://www.amazon.com/ap/signin?{urlencode(oauth_params)}"

def create_and_save_attestation_keys():
    private_key, public_key = create_attestation_key()
    private_key_str, public_key_str = serialize_and_encode_keys(private_key, public_key)

    with open("userdata/device_tokens.py", "w") as f:
        f.write(f'privateAttestationKey="{private_key_str}"\n')
        f.write(f'publicAttestationKey="{public_key_str}"\n')
        f.write(f'deviceId="{device_id}"\n')
        f.write(f'deviceSerial="{device_serial}"\n')

def register_account(maplanding_url):
    parsed_query = parse_qs(urlparse(maplanding_url).query)
    authorization_code = unquote(parsed_query['openid.oa2.authorization_code'][0])
    device_type = "#" + DEVICE_TYPE
    client_id = (device_serial.encode() + device_type.encode()).hex()
    amazon_reg_data = {
        "auth_data": {
            "user_id_password": {
            "password": "",
            "user_id": ""
        },
        "cookies": {
            "domain": ".amazon.com.au",
            "website_cookies": []
        },
        "registration_data": {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "device_model": DEVICE_NAME,
            "device_serial": device_serial,
            "device_type": DEVICE_TYPE,
            "domain": "Device",
            "os_version": OS_VERSION,
            "software_version": "1"
        },
        "requested_extensions": [
            "device_info",
            "customer_info"
        ],
        "requested_token_type": [
            "bearer",
            "mac_dms",
            "store_authentication_cookie",
            "website_cookies"
        ],
        "user_context_map": {
            "frc": "AKE2WPDpa+NutUanJxSSPV1Yk0bhyJFrNTb6ScB0MWINZIv3KXv44I5BwjAX3sMYq1ayta19QkhlKYWi6RLkWraqa93OxN/Ls2UbYXANfbOrmSKWPFJTJTiyAHi2fQNC1g4lLBK+vJD99BJWJ3dgp0+vT3yiVhEbnt0Vtn0yKzv8FXO1iV7j7Zqd39btEBqxTXpEsQS0oMQwi9ifh/V//+LSWmhPgwFxU87cWVIr+P3QXHgcfMAQgUhewt1Rua86UD3XZh0XeCK2Va4M6nA6YGFt9ZhGwEOsDrnIrLJFmIppDoOJIUrBJ14UGSFAhNpllt526nhBk0kT0JVuThFvKBS/tvUWhlrrh/d1Cdoi1y/hT3BLuQ5bu2nK66/jh981sUAUlYpMqlOi"
        }
    }

    url = 'https://api.amazon.com/auth/register'
    reg_headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept-Charset": "utf-8",
        "x-amzn-identity-auth-domain": "api.amazon.com.au",
        "Connection": "keep-alive",
        "Accept": "/",
        "Accept-Language": "en-US"
    }
    res = requests.post(url, json=amazon_reg_data, headers=reg_headers, verify=True)
    if res.status_code != 200:
        print("login failed")
        return({"result": "failure"})
    

    res = res.json()
    #print(res)
    tokens = res['response']['success']['tokens']['bearer']
    x_amz_access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']
    amz_account_id = res['response']['success']['extensions']['customer_info']['user_id']
    data = {
        "result":"success",
        "access_token": x_amz_access_token,
        "refresh_token": refresh_token,
        "amz_account_id": amz_account_id
    }
    #print(data)
    #with open('userdata/register_data', 'w') as d:
        #print(reg_access_token, '\n', amz_account_id, '\n', data, '\n', res, file=d)
    return(data["refresh_token"])

def generate_frc(device_id):
    cookies = json.dumps({
        "ApplicationName": APP_NAME,
        "ApplicationVersion": APP_VERSION,
        "DeviceLanguage": "en",
        "DeviceName": DEVICE_NAME,
        "DeviceOSVersion": OS_VERSION,
        "IpAddress": requests.get('https://api.ipify.org').text,
        "ScreenHeightPixels": "1920",
        "ScreenWidthPixels": "1280",
        "TimeZone": "00:00",
    })
    compressed = gzip.compress(cookies.encode())
    key = PBKDF2(device_id, b"AES/CBC/PKCS7Padding").read(32)
    iv = secrets.token_bytes(16)
    encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(key, iv=iv))
    ciphertext = encrypter.feed(compressed)
    ciphertext += encrypter.feed()
    hmac_ = hmac.new(PBKDF2(device_id, b"HmacSHA256").read(32), iv + ciphertext, hashlib.sha256).digest()
    return base64.b64encode(b"\0" + hmac_[:8] + iv + ciphertext).decode()

def get_flex_auth_token(refresh_token: str) -> str:
    url = 'https://api.amazon.com/auth/token'
    data = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "source_token_type": "refresh_token",
        "source_token": refresh_token,
        "requested_token_type": "access_token",
    }
    headers = {
        "User-Agent": USER_AGENT,
        "x-amzn-identity-auth-domain": "api.amazon.com.au",
    }
    res = requests.post(url, json=data, headers=headers)
    if res.status_code == 400:
        try:
            msg = res.json()
            if msg["error_description"] == "The request has an invalid parameter : source_token":
                print("Error: Device was deregistered")
            else:
                print(f"Error refreshing token. Code 400, Message: {msg}")
        except:
            print(f"Error refreshing token. Code 400, Message: {res.text}")
        exit()
    elif res.status_code != 200:
        print(f"Error refreshing token. Code {res.status_code}, Message: {res.text}")
        exit()
    try:
        res_json = res.json()
        if 'access_token' in res_json:
            x_amz_access_token = res_json['access_token']
        else:
            print(f"Error refreshing token. Code {res.status_code}, Message: {res.text}")
            exit()
    except Exception:
        print(f"Error refreshing token. Code {res.status_code}, Message: {res.text}")
        exit()
    return x_amz_access_token


def refresh(refresh_token):
    token = get_flex_auth_token(refresh_token)
    with open("userdata/access_token", "w") as t:
        print(token, end='', file=t)
    return token
