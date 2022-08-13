"""
ebbe a classba kerülnek azok a paraméterek, amik az endpointhívások alatt megegyeznek
"""
import json

base_url: str = "http://172.29.15.15:8090/"
token: str = ""
headers: json = {"Content-Type": "application/json",
                 "Accept": "application/json",
                 "Authorization": "Bearer " + token
                 }


def get_token():
    return token


def set_base_url(new_base_url: str):
    global base_url
    base_url = new_base_url


def set_token(new_token: str, update_headers=True):
    '''
    Set in all endpointcall in the header's authorisation value: Bearer token to the new_token parameter
    :param new_token: the value of the new token
    :param update_headers: if false, it only update the token parameter,
    but doesnt update the token value in the headers
    :return:
    '''
    global token
    global headers
    token = new_token
    if update_headers:
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "Authorization": "Bearer " + token
                   }


def get_headers():
    return headers


def reset_headers():
    global headers
    headers = {"Content-Type": "application/json",
               "Accept": "application/json",
               "Authorization": "Bearer " + token
               }

    return headers


def set_headers(new_headers: json):
    '''update the current headers in all endpointcall to the given new_header parameter'''
    global headers
    headers = new_headers
