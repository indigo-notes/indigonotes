from supaConfig import supa
from hashlib import sha256

class Encrypter:
    def __init__(self):
        self.encrypter = sha256
    def encrypt(self, string: str) -> str:
        buffer = string.encode()
        enc = self.encrypter(buffer)
        return enc.hexdigest()

encryption = Encrypter()

def check_psw(psw: str):
    if len(psw) < 6:
        return "Password must be at least of 6 characters of length"
    elif not any(char in {"!", "_", "?", "$", "&", "@"} for char in psw):
        return "Password must contain at least one among: '!', '_', '?', '$', '&', '@'"
    elif not any(char in {str(i) for i in range(10)} for char in psw):
        return "Password must contain at least one number"
    elif psw == psw.lower():
        return "Password must contain at least one capital letter"
    else:
        return ""

def sign_up_user(username: str, password: str, confirm_psw: str, email: str):
    """Sign up a user"""
    response = supa.from_("users").select("*").eq("username", encryption.encrypt(username)).execute()
    response1 = supa.from_("users").select("*").eq("email", encryption.encrypt(email)).execute()
    if len(response.data) > 0:
        return "The username is already registered"
    elif len(response1.data) > 0:
        return "The email is already registered"
    elif check_psw(password):
        return check_psw(password)
    elif password != confirm_psw:
        return "The two provided passwords should match!"
    else:
        supa.table("users").insert({"username": encryption.encrypt(username), "password": encryption.encrypt(password), "email": encryption.encrypt(email)}).execute()
        return "User successfully registered! You're now welcome to go to the main application and sign in"

