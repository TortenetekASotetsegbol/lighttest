"""
ebbe a classba kerülnek azok a paraméterek, amik az endpointhívások alatt megegyeznek
"""
import json


class Common:
    base_url: str = "http://000.00.00.00:0000/"
    token: str = ""
    headers: json = {"Content-Type": "application/json",
                     "Accept": "application/json"
                     }

    @staticmethod
    def set_token(new_token: str, update_headers=True) -> None:
        """
        Set in all endpointcall in the header's authorisation value: Bearer token to the new_token parameter

        Arguments:
            new_token: the value of the new token
            update_headers: if false, it only update the token parameter,
                but doesnt update the token value in the headers
        """
        Common.token = new_token
        if update_headers:
            Common.headers.update({"Authorization": f'Bearer {Common.token}'})

    @staticmethod
    def reset_headers() -> dict:
        Common.headers = {"Content-Type": "application/json",
                          "Accept": "application/json",
                          "Authorization": f'Bearer {Common.token}'
                          }

        return Common.headers

    @staticmethod
    def set_headers(new_headers: dict) -> None:
        """update the current headers in all endpointcall to the given new_header parameter"""

        Common.headers = new_headers
