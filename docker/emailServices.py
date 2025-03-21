import smtplib
from userAuth import supa, encryption
import uuid
from courier.client import Courier
from courier import ContentMessage, ElementalContentSugar, UserRecipient, Routing

g = open("/run/secrets/courier_key")
courier_key = g.read()
g.close()

server = Courier(authorization_token=courier_key)

def send_welcome_email(email_address: str, username: str):
    server.send(
      message=ContentMessage(
        to=UserRecipient(
        email=email_address,
        data={
            "name": username,
        }
        ),
        content=ElementalContentSugar(
        title="Welcome to IndigoNotes, {name}!",
        body="Hello {name}, we are really excited to have you on [**IndigoNotes**](https://indigonotes.com)!\n\nWe hope you will enjoy your journey with us and, if you want to know more about us, you can [schedule a call](https://calendly.com/astraberte9) with our founder, Clelia Bertelli\nHoping for the best,\nIndigoNotes Team\n\nFind us on: [LinkedIn](https://www.linkedin.com/company/indigonotes) | [BlueSky](https://bsky.app/profile/indigonotes.bsky.social) | [GitHub](https://github.com/indigo-notes) | [YouTube](https://www.youtube.com/@indigo-notes)",
        ),
        routing=Routing(method="all", channels=["gmail"]),
    )
    )

def send_recover_password(email_address: str, username: str):
    random_psw = str(uuid.uuid4())
    response = supa.from_("users").select("*").eq("email", encryption.encrypt(email_address)).execute()
    if len(response.data) == 0:
        return "The email address is not registered"
    elif len(response.data) > 0 and response.data[0]["username"] != encryption.encrypt(username):
        return "The username you provided does not match with the one associated to the email"
    else:
        supa.table("users").update({"password": encryption.encrypt(random_psw)}).eq("email", encryption.encrypt(email_address)).execute()
        text = f"Hey {username}, here is your temporary password:\n\n{random_psw}\n\nUse it to sign in to IndigoNotes and then make sure to change it!\n\nSincerely,\nIndigoNotes Team"
        server.send(
            message=ContentMessage(
                to=UserRecipient(
                    email=email_address,
                    data={
                        "name": username,
                    }
                ),
                content=ElementalContentSugar(
                    title="Password Recovery Email for {name} - IndigoNotes",
                    body=f"{text}\n\nFind us on: [LinkedIn](https://www.linkedin.com/company/indigonotes) | [BlueSky](https://bsky.app/profile/indigonotes.bsky.social) | [GitHub](https://github.com/indigo-notes) | [YouTube](https://www.youtube.com/@indigo-notes)",
                ),
                routing=Routing(method="all", channels=["gmail"]),
            )
        )
        return "Password recovery email sent"