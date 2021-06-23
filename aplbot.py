import html, json, re, requests

from chatbot import *

with open("config.json", "r") as f:
  config = json.load(f)
  
def md_escape(line):
  if line == "\\":
    return "``\\``"
  elif line.endswith("\\"):
    s = ""
    while line.endswith("\\"):
      s += "\\"
      line = line[:-1]
    return md_escape(line) + s
  elif line == "":
    return ""
  else:
    return "`" + line.replace("`", "\\`") + "`"

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
                codes.append(line[7:])
              if line.startswith("⋄"):
                codes.append(line[1:])
          else:
            for block in re.findall(r"<code>(⎕&larr;|⋄)(.+?)</code>", x["content"]):
              codes.append(html.unescape(block[1]))
          if not codes:
            continue
          code = html.unescape("⋄".join(codes))
          try:
            response = requests.post("https://tryapl.org/Exec", headers = {
              "Content-Type": "application/json; charset=utf-8"
            }, data = json.dumps(["", 0, "", code]))
            if response.status_code != 200:
              rooms[room].sendMessage(f":{x['message_id']} status code {response.status_code}; if this persists and TryAPL is functioning, please contact a developer")
            else:
              lines = response.json()[3]
              if len(lines) == 0:
                rooms[room].sendMessage(f":{x['message_id']} `<empty response>`")
              elif len(lines) == 1:
                rooms[room].sendMessage(f":{x['message_id']} {md_escape(lines[0])}")
              else:
                rooms[room].sendMessage("".join("    " + line + "\n" for line in lines) + "    \n    @" + x["user_name"])
          except:
            rooms[room].sendMessage(f":{x['message_id']} unexpected bot error running this code; if this persists, please contact a developer")
            raise
  return _inner

chatbot = Chatbot()
chatbot.login()

rooms = {
  k: chatbot.joinRoom(k, handler(k)) for k in config["rooms"]
}