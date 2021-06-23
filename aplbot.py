import html, json, re, requests

from chatbot import *

with open("config.json", "r") as f:
  config = json.load(f)
  
ws = {
  " ": ["spaces", "space"],
  "\t": ["tabs", "tab"]
}

def RLE(x):
  r = []
  for k in x:
    if r and k == r[-1][1]:
      r[-1][0] += 1
    else:
      r.append([1, k])
  return r

def detect_shape(lines):
  return f"{len(lines)} {max(map(len, lines))}⍴' '"

def preparse(line):
  if line[0] == "⋄": line = line[1:]
  output = ""
  string = False
  for char in line:
    if not string and char == "⍝":
      return output
    output += char
    if char == "'":
      string ^= True
  return output

def handler(room):
  def _inner(activity):
    if "e" in activity:
      for x in activity["e"]:
        if x["event_type"] == 1 and x["room_id"] == room:
          codes = []
          if x["content"].startswith("<pre class='full'>") and x["content"].endswith("</pre>"):
            for line in map(str.strip, x["content"][18:-6].split("\n")):
              print(line)
              if line.startswith("⎕&larr;"):
                codes.append(preparse(line))
              if line.startswith("⋄"):
                codes.append(preparse(line[1:]))
          else:
            for block in re.findall(r"<code>((⎕&larr;|⋄).*?)</code>", x["content"]):
              if block[0] == "⎕&larr;" or block[0] == "⋄": continue
              codes.append(preparse(html.unescape(block[0])))
          if not codes:
            continue
          code = html.unescape("⋄".join(codes))
          print("--- EXECUTING ---")
          print(code)
          print("-----------------")
          try:
            response = requests.post("https://tryapl.org/Exec", headers = {
              "Content-Type": "application/json; charset=utf-8"
            }, data = json.dumps(["", 0, "", code]))
            if response.status_code != 200:
              rooms[room].sendMessage(f":{x['message_id']} status code {response.status_code}; if this persists and TryAPL is functioning, please contact a developer")
            else:
              if x["user_id"] == 296403: return
              reply = ":" + str(x["message_id"]) + " "
              ping = "    @" + x["user_name"].replace(" ", "")
              lines = response.json()[3]
              if len(lines) == 0:
                ret = reply + "Response looks like a 0-by-0 matrix."
              elif all(line == "" for line in lines):
                ret = reply + "Response looks like a " + str(len(lines)) + "-by-0 matrix."
              elif "".join(map(str.strip, lines)) == "":
                ret = reply + "Response looks like a " + str(len(lines)) + "-by-" + str(max(map(len, lines))) + " matrix of whitespace characters."
              elif len(lines) == 1 and lines[0].startswith("\bhelp\b"):
                url = lines[0][6:]
                ret = reply + "[" + "://".join(url.split("://")[1:]).replace("%20", " ") + "](" + url + ")"
              elif len(lines) == 1:
                line = lines[0]
                if (line[-1] != "\\" or line[0] != "`" and "``" not in line) and line[0] not in ws:
                  if line[-1] == "\\":
                    ret = reply + "``" + line + "``"
                  else:
                    ret = reply + "`" + line.replace("`", "\\`") + "`"
                  if len(ret) > 500:
                    ret = ping + "\n    " + line
                else:
                  ret = ping + "\n    " + line
              else:
                trailing = 0
                for line in lines[::-1]:
                  if line.strip() == "":
                    trailing += 1
                  else:
                    break
                ret = ping + f" ({trailing} trailing line{'s' * (trailing != 1)})" * (trailing > 0) + "\n" + "\n".join("    " + line for line in lines) + "\n    ␄" * (trailing > 0)
              rooms[room].sendMessage(ret)
          except:
            rooms[room].sendMessage(f":{x['message_id']} bot error (not TryAPL or your code's issue) running this code; if this persists, please contact a developer")
            raise
  return _inner

chatbot = Chatbot()
chatbot.login()

rooms = {
  k: chatbot.joinRoom(k, handler(k)) for k in config["rooms"]
}