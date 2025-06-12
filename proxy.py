class Proxy:
    def __init__(self, proxy: dict):
        self.proxy = proxy
    
    @property
    def host(self) -> str:
        return self.proxy['address']
    
    @property
    def http_port(self) -> int:
        return self.proxy['http_port']
    
    @property
    def socks5_port(self) -> int:
        return self.proxy['socks5_port']
    
    @property
    def username(self) -> str:
        return self.proxy['username']
    
    @property
    def password(self) -> str:
        return self.proxy['password']