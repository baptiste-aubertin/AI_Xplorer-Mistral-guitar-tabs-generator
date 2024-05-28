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

MODEL_NAME = "./model-tokens-startt-endt"
# MODEL_NAME = "./merge"
LLM_ENDPOINT_ADRESS = 'http://195.242.24.65:80'
PROMPT = """Give me the guitar tab following this one in the key of {key} and in the style of {style}:\n{tablature}"""

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def make_llm_endpoint_request(message:str, temperature:float, top_p:float):
    api_request_data = {
    'model': MODEL_NAME,
    'max_tokens': 256,  # Adjust these parameters as needed
    'temperature': 0.95,
    'top_p': 0.95,
    "messages": [
        {"role": "user", "content": message},
    ]
    }
    return requests.post(LLM_ENDPOINT_ADRESS+'/v1/chat/completions', json=api_request_data, timeout=10).json()["choices"][0]["message"]["content"]
    return """[startt]e|--8--8--6-----|--------------|--6--8--------|--6--8----------|
B|--------------|-----8--10-----|--10--10------|--8--8----------|
G|--------------|--------------|--------------|----------------|
D|--------------|--------------|--------------|----------------|
A|--------------|--------------|--------------|----------------|
E|--------------|--------------|--------------|----------------|
[endt] [control_543][startt]e|--8-----------|--------8-----|-----8--10-----|--------------|
B|--8-----------|--------8-----|-----8--10-----|--10--10-----|
G|--------------|--------------|---------------|--------------|
D|--------------|--------------|---------------|--------------|
A|--------------|--------------|---------------|--------------|
E|--------------|--------------|---------------|--------------|
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
    print("####################")
    print(tablature)
    tablature = postprocess_output(message, tablature)
    print("####################")
    print(tablature)
    print("####################")
    midi_url = convert_to_midi(tablature, tempo)
    response = {
        "tablature": tablature.replace("\n", "<br>"),
        "midi_url": midi_url
    }
    return response

import re
def extract_tabs(text):
    # Regex pattern to match text between [startt] and [endt] tags
    pattern = re.compile(r'\[startt\](.*?)\[endt\]', re.DOTALL)
    tabs = pattern.findall(text)
    return tabs

def postprocess_output(input:str, output: str) -> str:

    output = output.strip()
    inputs = input.split("\n")
    inputs = [x.split("|") for x in inputs]

    length_measures = len(inputs[0][1])

    output_corrected = input.split("\n")

    # tabs = extract_tabs(output)
    # print(tabs)

    # tab = tabs[0]
    tab = output.split("\n")
    tab = tab[:6]
    # remove empty elements
    tab = [x for x in tab if len(x) > 0]

    # check if the tab has the right number of line

    for j in range(6):
        if tab[j][0] != inputs[j][0]:
            print("D3")
            return output_corrected
        measures = tab[j].split("|")[:5]
        measures.append("")
        for k in range(1,len(measures)-1):
            if len(measures[k]) > 0:
                if len(measures[k]) < length_measures:
                    measures[k] = measures[k] + "-"*(length_measures-len(measures[k]))
                elif len(measures[k]) > length_measures:
                    measures[k] = measures[k][:length_measures]
        tab[j] = "|".join(measures)
        if tab[-1]!='|':
            tab += '|'
    # add the measures
    for j in range(6):
        output_corrected[j] += tab[j][2:]
    output_corrected_text = "\n".join(output_corrected)
    print("dddd")
    print(output_corrected_text)
    print("dddd")
    return output_corrected_text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
