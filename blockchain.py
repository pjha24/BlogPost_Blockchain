import hashlib
POST = "post"
COMMENT = "comment"

def post(block, username, title, content):
  return Block(POST, username, title, content, prev=block)

def comment(block, username, title, content):
  return Block(COMMENT, username, title, content, prev=block)

def viewAll(block):
  if block is None:
    return []
  result = viewAll(block.P)
  if block.T[0] == POST:
    result.append(f"(Title: {block.T[2]}, Author: {block.T[1]})")
  return result


def viewUser(block, username):
  if block is None:
    return []
  result = viewUser(block.P, username)
  if block.T[0] == POST and block.T[1] == username:
    result.append(f"(Title: {block.T[2]}, Content: {block.T[3]})")
  return result


def viewComments(block, post):
  content = ""
  result = []
  while block is not None:
    if block.T[0] == COMMENT and block.T[2] == post:
      result = [(f"(Author: {block.T[1]}, Comment: {block.T[3]})")] + result
    if block.T[0] == POST and block.T[2] == post:
      content = block.T[3]
    block = block.P
  return [f"(Post: {post}, Content {content}"] + result


def debug(block):
  if block is None:
    return []
  result = debug(block.P)
  result.append("(" + block.H + f"|{block.T[0]}|{block.T[1]}|{block.T[2]}|{block.T[3]}|" + str(block.N) + ")")
  return result

def construct(block_text, prev):
  block = Block()
  vals = block_text.split("~")
  block.P = prev
  block.H = vals[0]
  block.N = vals[1]
  block.T = (vals[2],vals[3],vals[4],vals[5])
  return block

class Block:
  def __init__(self, operation=None, username=None, title=None, content=None, prev=None):
    if operation is not None:
      self.init(operation, username, title, content)

  def init(self, operation, username, title, content, prev=None):
    self.P = prev
    self.H = prev.getHash() if prev is not None else "0"*64
    self.T = (operation, username, title, content)
    self.N = 0
    self.mine()
  
  def getHash(self):
    info = self.H + f"{self.T[0]}{self.T[1]}{self.T[2]}{self.T[3]}" + str(self.N)
    return hashlib.sha256(info.encode()).hexdigest()
  
  def mine(self):
    hashVal = self.getHash()
    while hashVal[0] != '0' and hashVal[0] != '1':
      self.N += 1
      hashVal = self.getHash()
  
  def toString(self):
    return f"{self.H}~{self.N}~{self.T[0]}~{self.T[1]}~{self.T[2]}~{self.T[3]}"

  
    