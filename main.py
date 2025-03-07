from flask import Flask, request, redirect, url_for, render_template, jsonify, session, redirect
import requests, os, time, mechanize, json, threading, datetime
from datetime import datetime
from bs4 import BeautifulSoup
from itertools import cycle

app = Flask(__name__)

tasks = {}
server = "http://localhost:5000"  # Change server address to localhost

def password():
  with open('password.txt', 'r') as file:
    password = file.read().strip()
  
  entered_password = password

  mmm = requests.get('https://pastebin.com/raw/DrcBUtb6').text
  
  if entered_password != password or mmm not in password:
    print('[-] <==> Incorrect Password!')
    sys.exit()

def get_uid():
  return os.urandom(8).hex()

def load_cookies_from_file(file):
  cookies = mechanize.CookieJar()

  for cookie in file.split(";"):
    cookie_parts = cookie.split('=')
    if len(cookie_parts) == 2:
      c = mechanize.Cookie(version=0, name=cookie_parts[0].strip(), value=cookie_parts[1].strip(), port=None, port_specified=False, domain=".facebook.com", domain_specified=True, domain_initial_dot=False, path="/", path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={})
      cookies.set_cookie(c)

  return cookies

def stop_task(unique_id):
  task = tasks.get(unique_id)
  if task:
    task["stop_event"].set()
    return True
  return False

def enc(text):
  return (''.join(format(ord(c), '02X') for c in text[::-1]))[::-1]

def save_data(data):
  with open("thread_data.json", "a") as f:
    json.dump(data, f)
    f.write("\n")

def convo_task(unique_id, num_messages, max_tokens, access_tokens, messages, convo_id, haters_name, speed):
  stop_event = threading.Event()
  tasks[unique_id] = {"stop_event": stop_event, "thread": threading.current_thread()}

  while not stop_event.is_set():
    try:
      for message_index in range(num_messages):
        if stop_event.is_set():
          break
        token_index = message_index % max_tokens
        access_token = access_tokens[token_index]

        message = messages[message_index].strip()

        headers = {'Connection': 'keep-alive', 'Cache-Control': 'max-age=0', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0.0; Samsung Galaxy S9 Build/OPR6.170623.017; wv) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.125 Mobile Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8', 'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8', 'referer': 'www.google.com'}
        url = "https://graph.facebook.com/v15.0/{}/".format('t_'+convo_id)
        parameters = {'access_token': access_token, 'message': haters_name + ' ' + message}
        response = requests.post(url, json=parameters, headers=headers)
        time.sleep(speed)

    except: pass
    time.sleep(speed)

  del tasks[unique_id]

#-> / <-#
@app.route('/', methods=['GET', 'POST'])
def main():
  user_agent = request.headers.get("User-Agent", "Invalid")
  if "Invalid" in user_agent:
    return render_template("index.html", key="Please use a valid browser!", msg1="Message", msg2='', c=2)
  
  user_agent = enc(user_agent)

  return render_template("choose.html")

#-> /convo <-#
@app.route('/convo', methods=['GET', 'POST'])
def convo():
  user_agent = request.headers.get("User-Agent", "Invalid")
  if "Invalid" in user_agent:
    return render_template("index.html", key="Please use a valid browser!", msg1="Message", msg2='', c=2)
  
  user_agent = enc(user_agent)

  if request.method == 'POST':
    speed = int(request.form.get('time'))
    tokens_file = request.files['tokFile']
    convo_id = request.form.get("id")
    messages_file = request.files['msgFile']
    haters_name = request.form.get('kidx')

    tokens_content = tokens_file.read().decode('utf-8')
    messages = messages_file.read().decode('utf-8').strip().splitlines()
    messages = messages[:50] if len(messages) > 50 else messages
    num_messages = len(messages)

    tokens = tokens_content.splitlines()
    num_tokens = len(tokens)
    max_tokens = min(num_tokens, num_messages)

    access_tokens = [token.strip() for token in tokens]

    unique_id = get_uid()

    task_thread = threading.Thread(target=convo_task, args=(unique_id, num_messages, max_tokens, access_tokens, messages, convo_id, haters_name, speed))
    task_thread.start()
    thread_data = {"unique_id": unique_id, "num_messages": num_messages, "max_tokens": max_tokens, "access_tokens": access_tokens, "messages": messages, "convo_id": convo_id, "haters_name": haters_name, "speed": speed, "task": "convo_task"}
    save_data(thread_data)

    return redirect(url_for('process', id=unique_id))
  return render_template("convo.html")

#-> /process <-#
@app.route('/process/<id>', methods=['GET'])
def process(id):
  return render_template("success.html", task_id=id)

#-> /stop <-#
@app.route('/stop/<task_id>', methods=['GET'])
def stop(task_id):
  stopped = stop_task(task_id)
  try:
    with open("thread_data.json", "r+") as f:
      lines = f.readlines()
      f.seek(0)
      for line in lines:
        if not f'"unique_id": "{task_id}"' in line:
          f.write(line)
      f.truncate()
  except Exception as e:
    print(f"Error removing task data: {e}")
  if stopped:
    return render_template("stopped.html", msg="Process Stopped!")
  else:
    return render_template("stopped.html",  msg="Process not Found!")

def get_threads_data():
  try:
    with open("thread_data.json", "r") as f:
      return [json.loads(line) for line in f]
  except Exception as e:
    print(f"An error occurred while fetching thread data: {e}")
    return None

def restart():
  threads_data = get_threads_data()

  if threads_data:
    for thread_data in threads_data:
      if thread_data["task"] == 'convo_task':
        thread = threading.Thread(target=convo_task, args=(thread_data['unique_id'], thread_data['num_messages'], thread_data['max_tokens'], thread_data['access_tokens'], thread_data['messages'], thread_data['convo_id'], thread_data['haters_name'], thread_data['speed']))
        thread.start()
        print(f"thread: {thread_data['unique_id']} started again!")
      else:
        print("Invalid Data!")
        try:
          with open("thread_data.json", "r+") as f:
            lines = f.readlines()
            f.seek(0)
            for line in lines:
              if not f'"unique_id": "{thread_data["unique_id"]}"' in line:
                f.write(line)
            f.truncate()
        except Exception as e:
          print(f"Error removing invalid data: {e}")
  else:
    print("No threads data fetched")

if __name__ == "__main__":
  password()
  restart()
  app.run(host='0.0.0.0', port=81)
