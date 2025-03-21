from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from userAuth import sign_up_user, supa, check_psw, encryption
import uuid
from gradio import Request
from rsaEncrypt import encrypt_note, decrypt_note
from emailServices import send_welcome_email, send_recover_password
import gradio as gr
import requests as rq
import pandas as pd
from pdfitdown.pdfconversion import convert_markdown_to_pdf
import os

g = open("/run/secrets/indigonotes_key")
indigonotes_api_key = g.read()
g.close()

app = FastAPI()

theme = gr.Theme(primary_hue=gr.themes.colors.indigo, secondary_hue=gr.themes.colors.purple, radius_size="md", font=["Arial", "sans-serif"])

class Credentials(BaseModel):
    username: str
    password: str
    confirm_password: str
    email: str

class UserInfo(BaseModel):
    username: str
    password: str

class RegistrationResponse(BaseModel):
    message: str

req = Request()

def authenticate_user(username: str, password: str) -> bool:
    """Authenticates the user through username and password"""
    response = supa.from_("users").select("*").eq("username", encryption.encrypt(username)).eq("password", encryption.encrypt(password)).execute()
    data = response.data
    if len(data) == 0:
        return False
    else:
        visit_id = str(uuid.uuid4())
        supa.table("visits").insert({"visit_id": visit_id}).execute()
        req.username = encryption.encrypt(username)
        req.session_hash = encryption.encrypt(str(visit_id))
        return True

def verify_api_key(x_api_key: str):
    if x_api_key == indigonotes_api_key:
        return x_api_key
    else:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/")
async def hello_world():
    return RegistrationResponse(message="Hello World")

@app.post("/signup")
async def register(creds: Credentials, x_api_key: str = Depends(verify_api_key)) -> RegistrationResponse:
    r = sign_up_user(creds.username, creds.password, creds.confirm_password, creds.email)
    return RegistrationResponse(message=r)

def sign_up(username: str, password: str, confirm_password: str, email_address: str):
    headers = {
        "x_api_key": indigonotes_api_key,
    }
    res = rq.post("http://0.0.0.0:80/signup",json=Credentials(username=username, password=password, confirm_password=confirm_password, email=email_address).model_dump(), params=headers)
    if res.json()["message"] == "User successfully registered! You're now welcome to go to the main application and sign in":
        send_welcome_email(email_address, username)
    return res.json()["message"]

    
def upload_note_to_supa(note: str):
    response = supa.from_("notes").select("*").eq("user", req.username).execute()
    data = response.data
    if len(data) == 100:
        return "You reached the maximum number of available notes, please delete some of them"
    elif 0 < len(data) < 100:
        note_id = max([len(data), data[-1]["number"]])+1
        supa.table("notes").insert({"note": encrypt_note(note), "user": req.username, "number": note_id}).execute()
        return f"Successfully updated the note! Your note has ID: {note_id}"
    else:
        note_id = len(data)+1
        supa.table("notes").insert({"note": encrypt_note(note), "user": req.username, "number": note_id}).execute()
        return f"Successfully updated the note! Your note has ID: {note_id}"

def change_password(old_password: str, new_password: str, confirm_new_password: str):
    if old_password == new_password:
        return "Old and new passwords cannot be the same"
    elif new_password != confirm_new_password:
        return "The new password and the confirmation password do not match"
    elif check_psw(new_password):
        return check_psw(new_password)
    else:
        response = supa.from_("users").select("*").eq("username", req.username).eq("password", encryption.encrypt(old_password)).execute()
        if len(response.data) == 0:
            return "The old password does not match with the one registered for this username"
        else:
            supa.table("users").update({"password": encryption.encrypt(new_password)}).eq("username", req.username).execute()
            return "Password updated with success!"

def get_notes_number():
    response = supa.from_("notes").select("*").eq("user", req.username).execute()
    data = response.data
    df = pd.DataFrame(
        {
            "Usage": ["Notes"],
            "Percentage": [len(data)]
        }
    )
    return df, f"You've used **{len(data)}%** of your available notes"

def display_notes():
    response = supa.from_("notes").select("*").eq("user", req.username).execute()
    data = response.data
    if len(data) > 0:
        notes = [decrypt_note(d["note"]) for d in data]
        numbers = [d["number"] for d in data]
        times = [d["created_at"] for d in data]
        fin_notes = [f"**Note {numbers[i]}, created at: {times[i]}**\n\n{notes[i]}" for i in range(len(times))]
        return "\n\n--------------\n\n".join(fin_notes)
    else:
        return "## No notes yet"
    
def download_notes():
    response = supa.from_("notes").select("*").eq("user", req.username).execute()
    data = response.data
    if len(data) > 0:
        notes = [decrypt_note(d["note"]) for d in data]
        numbers = [d["number"] for d in data]
        times = [d["created_at"] for d in data]
        fin_notes = [f"**Note {numbers[i]}, created at: {times[i]}**\n\n{notes[i]}" for i in range(len(times))]
        fl_name = str(uuid.uuid4())+".md"
        with open(fl_name, "w") as f:
            f.write("\n\n---\n\n".join(fin_notes))
        f.close()
        pdf_path = convert_markdown_to_pdf(fl_name, fl_name.replace(".md", ".pdf"))
        with open(pdf_path, "rb") as pdf:
            supa.storage.from_("notes").upload(pdf_path, pdf, file_options={"cache-control": 600, "content-type": "application/pdf"})
        pdf.close()
        os.remove(fl_name)
        os.remove(pdf_path)
        res_sign = supa.storage.from_("notes").create_signed_url(pdf_path, expires_in=600, options={"download": True})
        signed_url = res_sign["signedURL"]
        return f"Download your notes in PDF format from [this link]({signed_url}). The link is valid only for **10 minutes**. Please, if you want to keep your notes private, you should not share this link with anyone"
    else:
        return "## No notes yet"


def delete_notes(notes_to_delete: str):
    to_delete = notes_to_delete.split(",")
    try:
        to_delete = [int(td) for td in to_delete]
    except ValueError:
        return "You must only provide comma-separated numbers reporting the IDs of the notes you want to delete, as in this example: 3,4,5"
    else:
        for tf in to_delete:
            supa.table("notes").delete().eq("number", tf).eq("user", req.username).execute()
        return "Notes deleted successfully"

with gr.Blocks(theme=theme, title="Write Your Notes") as demo:
    with gr.Sidebar(label="Side Menu", open=False):
        gr.Button("Visit Our Website", link="https://indigonotes.com")
    with gr.Row():
        input_text = gr.TextArea(label="Your note", info="Write your note here (max. 1000 characters)", max_length=1000)
        @gr.render(inputs=input_text)
        def render_markdown(text):
            if len(text) == 0:
                gr.Markdown("## No Input Provided")
            else:
                gr.Markdown(text)
    with gr.Row():
        with gr.Column():
            upload_status = gr.Textbox(label="Note Upload Status", placeholder="Note not uploaded yet")
            submit_button = gr.Button(value="Upload Note").click(fn=upload_note_to_supa, inputs=[input_text], outputs=[upload_status])
    demo.load()

with gr.Blocks(theme=theme, title="See Your Notes") as dm:
    with gr.Sidebar(label="Side Menu", open=False):
        gr.Button("Visit Our Website", link="https://indigonotes.com")
    with gr.Row():
        with gr.Column():
            displayed_notes = gr.Markdown(label="Your Notes")
            display_notes_button = gr.Button(value="Display Your Notes").click(fn=display_notes, inputs=None, outputs=[displayed_notes])
    dm.load()

with gr.Blocks(theme=theme, title="Download Your Notes") as downif:
    with gr.Sidebar(label="Side Menu", open=False):
        gr.Button("Visit Our Website", link="https://indigonotes.com")
    with gr.Row():
        with gr.Column():
            downloaded_notes = gr.Markdown(label="Download URL")
            download_notes_button = gr.Button(value="Generate Download URL").click(fn=download_notes, inputs=None, outputs=[downloaded_notes])
    downif.load()

with gr.Blocks(theme=theme, title="See Your Notes") as dm:
    with gr.Sidebar(label="Side Menu", open=False):
        gr.Button("Visit Our Website", link="https://indigonotes.com")
    with gr.Row():
        with gr.Column():
            displayed_notes = gr.Markdown(label="Your Notes")
            display_notes_button = gr.Button(value="Display Your Notes").click(fn=display_notes, inputs=None, outputs=[displayed_notes])
    dm.load()

with gr.Blocks(theme=theme, title="Delete Your Notes") as ddm:
    with gr.Sidebar(label="Side Menu", open=False):
        gr.Button("Visit Our Website", link="https://indigonotes.com")
    with gr.Row():
        with gr.Column():
            to_eliminate = gr.Textbox(label="Input here notes to be deleted, comma-separated", info="Here is an example: 3,4,5", placeholder="eg. 1,2,3")
            elimination_status = gr.Textbox(label="Notes elimination status", placeholder="No notes eliminated yet")
            display_notes_button = gr.Button(value="Eliminate Your Notes").click(fn=delete_notes, inputs=[to_eliminate], outputs=[elimination_status])
    ddm.load()

with gr.Blocks(theme=theme, title="Your Dashboard") as usrd:
    with gr.Sidebar(label="Side Menu", open=False):
        gr.Button("Visit Our Website", link="https://indigonotes.com")
    with gr.Row():
        with gr.Column():
            gr.HTML("<h3 align='center'>Change Password</h3>")
            old_password = gr.Textbox(label="Old password", type="password")
            new_password = gr.Textbox(label="New password", type="password")
            confirm_new_password = gr.Textbox(label="Confirm new password", type="password")
            password_change_st = gr.Textbox(label="Password Change Status", placeholder="Password not changed yet")
            change_psw_button = gr.Button("Change Password").click(fn=change_password, inputs=[old_password, new_password, confirm_new_password], outputs=[password_change_st])
    with gr.Row():
        df = pd.DataFrame(
            {
                "Usage": ["Notes"],
                "Percentage": [0]
            }
        )
        with gr.Column():
            gr.HTML("<h3 align='center'>Usage</h3>")
            gr.HTML("<br>")
            plot = gr.BarPlot(value=df, x="Usage", y="Percentage", y_lim=[0,100])
            notes_usage = gr.Markdown()
            gr.HTML("<br>")
            plot_button = gr.Button("See your usage stats").click(fn=get_notes_number, inputs=None, outputs=[plot, notes_usage])
    usrd.load()



tbi = gr.TabbedInterface([demo, dm, ddm, downif, usrd], ["Write Your Notes", "See Your Notes", "Delete Your Notes", "Download Your Notes", "Your Dashboard"], title="IndigoNotes", theme=theme)
io = gr.Interface(fn = sign_up, inputs=[gr.Textbox(label="Username"), gr.Textbox(label="Password", type="password"), gr.Textbox(label="Confirm Password", type="password"), gr.Textbox(label="Email Address", type="email")], outputs=[gr.Textbox(label="Operation Status")], theme=theme, title="Sign up - IndigoNotes")

psr = gr.Interface(title="Recover Password - IndigoNotes", fn=send_recover_password, inputs=[gr.Textbox(label="Email Address", type="email"), gr.Textbox(label="Username")], outputs=[gr.Textbox(label="Operation Status")], theme=theme)

gr.mount_gradio_app(app, io, "/register")
gr.mount_gradio_app(app, psr, "/password-recovery")
gr.mount_gradio_app(app, tbi, "/app", auth=authenticate_user, auth_message="Input your username and password. If you are not already registered, go to <a href='/register'><u>the registration page</u></a>.<br><u><a href='/password-recovery'>Forgot your password?</a></u>")

