import html, json, re, requests

from chatbot import *

with open("config.json", "r") as f:
  config = json.load(f)

ws = {
  " ": ["spaces", "space"],
  "\t": ["tabs", "tab"]
}

hooks = {}

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

def response_for(x):
  if x["content"] in [")about", "<code>)about</code>", "<pre class='full'>)about</pre>"]:
    return f":{x['message_id']}" + r" To run APL code, write code blocks starting with `⎕←` or `⋄` or write a multi-line code block and prepend `⎕←` or `⋄` to lines you wish to run. All matching groups / lines will be joined by `⋄` and run via TryAPL, and the output will be posted here. To format a codeblock, write `\`code\``, or for a multi-line code block, use Shift+Enter to type multiple lines and press Ctrl-K, press the 'fixed font' button, or prepend four spaces to each line."
  codes = []
  if x["content"].startswith("<pre class='full'>") and x["content"].endswith("</pre>"):
    lines = list(map(str.strip, x["content"][18:-6].split("\n")))
    if lines[0].startswith("⎕&larr;") or lines[0].startswith("⋄"):
      for line in lines:
        if line.startswith("⎕&larr;"):
          codes.append(preparse(line))
        if line.startswith("⋄"):
          codes.append(preparse(line[1:]))
  else:
    if x["content"].startswith("⎕&larr;") or x["content"].startswith("⋄"):
      item = "⋄ " if x["content"].startswith("⋄") else "⎕←"
      return rf":{x['message_id']} Did you forget to add backticks around your code (`\`{item}code\``)? You can edit your message and I will edit my reply."
    if "`⎕&larr" in x["content"]:
      return rf":{x['message_id']} Did you forget a closing backtick (`\`⎕←code\``)? You can edit your message and I will edit my reply."
    if "`⋄" in x["content"]:
      return rf":{x['message_id']} Did you forget a closing backtick (`\`⋄code\``)? You can edit your message and I will edit my reply."
    for block in re.findall(r"<code>((⎕&larr;|⋄).*?)</code>", x["content"]):
      if block[0] == "⎕&larr;" or block[0] == "⋄": continue
      codes.append(preparse(html.unescape(block[0])))
  if not codes:
    return
  code = html.unescape("⋄".join(codes))
  try:
    response = requests.post("https://tryapl.org/Exec", headers = {
      "Content-Type": "application/json; charset=utf-8"
    }, data = json.dumps(["", 0, "", code]))
    if response.status_code != 200:
      return f":{x['message_id']} status code {response.status_code}; if this persists and TryAPL is functioning, please contact a developer"
    else:
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
      return ret
  except:
    return f":{x['message_id']} bot error (not TryAPL or your code's issue) running this code; if this persists, please contact a developer"
    raise

def handler(room):
  def _inner(activity):
    if "e" in activity:
      for x in activity["e"]:
        if x["event_type"] == 1 and x["room_id"] == room:
          if x["user_id"] in [296403, 319249]: return
          response = response_for(x)
          if response:
            hooks[x["message_id"]] = rooms[room].sendMessage(response)
        elif x["event_type"] == 2 and x["room_id"] == room:
          if x["user_id"] in [296403, 319249]: return
          response = response_for(x)
          if response:
            if x["message_id"] in hooks:
              rooms[room].editMessage(response, hooks[x["message_id"]])
            else:
              hooks[x["message_id"]] = rooms[room].sendMessage(response)
        elif x["event_type"] == 10 and x["room_id"] == room:
            if x["user_id"] in [296403, 319249]: return
            if x["message_id"] in hooks:
                rooms[room].deleteMessage(hooks[x["message_id"]])
  return _inner

chatbot = Chatbot()
chatbot.login()

rooms = {
  k: chatbot.joinRoom(k, handler(k)) for k in config["rooms"]
}
