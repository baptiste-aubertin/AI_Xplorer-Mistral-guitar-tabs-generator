from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tabs_MIDI.read_tabs_app import Tabs
from tabs_MIDI.midi_generator import Track
import requests
import os
import time


LLM_ENDPOINT_ADRESS = 'http://195.242.24.65:80'
PROMPT = """Give me the guitar tab following this one in the key of {key} and in the style of {style}:\n{tablature}"""

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def make_llm_endpoint_request(message:str, temperature:float, top_p:float):
    api_request_data = {
    'prompt': message,
    'max_tokens': 300,  # Adjust these parameters as needed
    'temperature': temperature,
    'top_p': top_p,
    }
    # return requests.post(LLM_ENDPOINT_ADRESS+'/generate', json=api_request_data, timeout=10).json()["text"][0]
    return """e|--------------|--------------|--------------|--------------|
B|-----6--------|--6-----------|--------------|--------------|
G|-----6--------|--6-----------|--3-----------|-----3--------|
D|--------------|--6-----------|--4-----------|-----4--------|
A|-----4--------|--4-----------|--4-----------|-----4--------|
E|--------------|--------------|--2-----------|-----2--------|
"""
def format_prompt(tablature:str, style:str, key:str):
    return PROMPT.format(tablature=tablature, style=style, key=key)

def convert_to_midi(tablature:str, tempo):
    t = Tabs(tablature.split("\n"))
    t.preprocess()
    t.displayTabs()
    t.convertNotes()

    f_name = f"tab_{time.time()}.mid"
    f_local_path = f"./static/midis/{f_name}"
    outputTrack = Track(int(tempo))
    outputTrack.midiGenerator(t.a, path=f_local_path)
    
    command = f"timidity {f_local_path}"
    os.system(command)
    return f"http://localhost:3000/static/midis/{f_name}"
    

class ChatMessage(BaseModel):
    message: str
    temperature: float
    top_p: float
    style: str
    key: str
    tempo: int

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(chat_message: ChatMessage):
    message = chat_message.message
    temperature = chat_message.temperature
    top_p = chat_message.top_p
    tempo = chat_message.tempo
    print(chat_message.dict())
    prompt = format_prompt(tablature=message, style=chat_message.style, key=chat_message.key)
    tablature = make_llm_endpoint_request(prompt, temperature, top_p)
    midi_url = convert_to_midi(tablature, tempo)
    
    response = {
        "tablature": tablature.replace("\n", "<br>"),
        "midi_url": midi_url
    }
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
