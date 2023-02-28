"""
ebbe a classba kerülnek azok a paraméterek, amik az endpointhívások alatt megegyeznek
"""


class HttpHeaders:
    global_base_url: str = "http://000.00.00.00:0000/"
    global_token: str = ""
    global_headers: dict = {"Content-Type": "application/json",
                            "Accept": "application/json"
                            }

    def __init__(self):
        self.base_url: str = None
        self.token: str = ""
        self.headers: dict = None

    @classmethod
    def set_global_token(cls, new_token: str, update_headers=True) -> None:
        """
        Set in all endpointcall in the header's authorisation value: Bearer token to the new_token parameter

        Arguments:
            new_token: the value of the new token
            update_headers: if false, it only update the token parameter,
                but doesnt update the token value in the headers
        """
        HttpHeaders.global_token = new_token
        if update_headers:
            cls.global_headers.update({"Authorization": f'Bearer {cls.global_token}'})

    @classmethod
    def reset_global_headers(cls) -> dict:
        cls.global_headers = {"Content-Type": "application/json",
                                      "Accept": "application/json",
                                      "Authorization": f'Bearer {cls.global_token}'
                                      }

        return cls.global_headers

    @classmethod
    def set_global_headers(cls, new_headers: dict) -> None:
        """update the current headers in all endpointcall to the given new_header parameter"""

        cls.global_headers = new_headers

    def set_token(self, new_token: str, update_headers=True) -> None:
        """
        Set in all endpointcall in the header's authorisation value: Bearer token to the new_token parameter

        Arguments:
            new_token: the value of the new token
            update_headers: if false, it only update the token parameter,
                but doesnt update the token value in the headers.
                if true, add an Authorization Bearer node into the headers with the token
        """
        self.token = new_token
        if update_headers:
            self.headers.update({"Authorization": f'Bearer {self.token}'})

    def reset_headers(self) -> dict:
        HttpHeaders.headers = {"Content-Type": "application/json",
                               "Accept": "application/json"
                               }

        return self.headers

    def set_headers(self, new_headers: dict) -> None:
        """update the current headers in all endpointcall to the given new_header parameter"""

        self.headers = new_headers

    def get_base_url(self):
        if self.base_url is not None:
            return self.base_url
        else:
            return self.global_base_url

    def get_headers(self):
        if self.headers is not None:
            return self.headers
        else:
            return self.global_headers
