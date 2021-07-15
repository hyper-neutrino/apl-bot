import discord, json, re, requests, html

with open("../configurations/apl-discord.json", "r") as f:
  config = json.load(f)

def RLE(x):
  r = []
  for k in x:
    if r and k == r[-1][1]:
      r[-1][0] += 1
    else:
      r.append([1, k])
  return r

def scan_code(line):
  if "```````" in line:
    blocks = list(map(scan_code, line.split("```````")))
    result = []
    for block in blocks[:-1]:
      result.extend(blocks)
      result.append("`")
    if blocks:
      result.extend(blocks[-1])
    return result
  else:
    components = [x[0] for x in re.findall(r"((\\`|[^`])+|`+)", line)]
    codes = []
    while components:
      if components[0][0] == "`" and components[0] in components[1:]:
        index = components.index(components[0], 1)
        codes.append("".join(components[1:index]))
        components = components[index + 1:]
      else:
        components.pop(0)
    return codes

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

class DiscordClient(discord.Client):
  def __init__(self):
    discord.Client.__init__(self, activity = discord.Game("]about"))

  async def on_ready(self):
    print("APL Discord Bot has started.")
  
  async def on_message(self, message):
    if message.author == self.user: return
    if message.content in ["]about", "`]about`", "``]about``", "```]about```"]:
      await message.reply("To run APL code, write code blocks starting with `⎕←` or `⋄` or write a multi-line code block and prepend `⎕←` or `⋄` to lines you wish to run. All matching groups / lines will be joined by `⋄` and run via TryAPL, and the output will be posted here. To format a codeblock, write `` `code` `` or ```​`​`​`\ncode\n`​`​`​``` for a multi-line code block.\n\nTo invite this bot to your own server, use this link: <https://discord.com/api/oauth2/authorize?client_id=857642538370465792&permissions=3072&scope=bot>")
      return
    try:
      blocks = scan_code(message.content)
      codes = []
      for block in blocks:
        for line in block.split("\n"):
          line = line.strip()
          if line.startswith("⎕←") and line != "⎕←":
            codes.append(preparse(line))
          if line.startswith("⋄") and line != "⋄":
            codes.append(preparse(line[1:]))
      code = "⋄".join(codes)
      if not code: return
      print("--- EXECUTING ---")
      print(code)
      print("-----------------")
      response = requests.post("https://tryapl.org/Exec", headers = {
        "Content-Type": "application/json; charset=utf-8"
      }, data = json.dumps(["", 0, "", code]))
      if response.status_code != 200:
        await message.reply("Status code {response.status_code}; if this persists and TryAPL is functioning, please contact a developer.")
      else:
        lines = response.json()[3]
        if len(lines) == 0:
          ret = "Response looks like a 0-by-0 matrix."
        elif all(line == "" for line in lines):
          ret = "Response looks like a " + str(len(lines)) + "-by-0 matrix."
        elif "".join(map(str.strip, lines)) == "":
          ret = "Response looks like a " + str(len(lines)) + "-by-" + str(max(map(len, lines))) + " matrix of whitespace characters."
        elif len(lines) == 1 and lines[0].startswith("\bhelp\b"):
          url = lines[0][6:]
          ret = url
        else:
          for ir in [range(len(lines)), range(len(lines) - 1, -1, -1)]:
            for index in ir:
              if lines[index] == "":
                lines[index] = chr(8203)
              else:
                break
          output = []
          for c, x in RLE(lines):
            output.extend([x] * min(c, 5))
            if c > 5:
              rep = c - 5
              if rep == 1:
                output.append(x)
              else:
                output.append("<" + str(rep) + " more identical lines skipped>")
          output = "\n".join(output)
          while "```" in output:
            output = output.replace("```", "``" + chr(8203) + "`")
          ret = "Warning: the output contains zero-width spaces which may cause issues if you copy-paste. They have UTF-8 codepoint 8203 which you can filter out.\n" * (chr(8203) in output)
          ret += "```\n" + output + "\n```"
        await message.reply(ret)
    except:
      await message.reply("Bot error (not TryAPL or your code's issue) running this code; if this persists, please contact a developer.")
      raise

client = DiscordClient()
client.run(config["discord-token"])