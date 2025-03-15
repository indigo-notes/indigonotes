import smtplib
from userAuth import supa, encryption
import uuid

g = open("/run/secrets/smtp_psw")
smtp_psw = g.read()
g.close()
server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login("team.indigonotes@gmail.com", smtp_psw)


def send_welcome_email(email_address: str, username: str):
    text = f"Subject: Welcome to IndigoNotes!\n\nHey {username}, so glad to see you here!\n\nHope you have a nice experience with IndigoNotes\n\nSincerely,\nIndigoNotes Team"
    server.sendmail("team.indigonotes@gmail.com", email_address, text)

def send_recover_password(email_address: str, username: str):
    random_psw = str(uuid.uuid4())
    response = supa.from_("users").select("*").eq("email", encryption.encrypt(email_address)).execute()
    if len(response.data) == 0:
        return "The email address is not registered"
    elif len(response.data) > 0 and response.data[0]["username"] != encryption.encrypt(username):
        return "The username you provided does not match with the one associated to the email"
    else:
        supa.table("users").update({"password": encryption.encrypt(random_psw)}).eq("email", encryption.encrypt(email_address)).execute()
        text = f"Subject: Password Recovery Email\n\nHey {username}, here is your temporary password:\n\n{random_psw}\n\nUse it to sign in to IndigoNotes and then make sure to change it!\n\nSincerely,\nIndigoNotes Team"
        server.sendmail("team.indigonotes@gmail.com", email_address, text)
        return "Recovery email sent"
