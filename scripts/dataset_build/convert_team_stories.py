import re, json, sys
from pathlib import Path
RAW = Path(sys.argv[1]).read_text()
OUTDIR = Path(sys.argv[2]); OUTDIR.mkdir(parents=True, exist_ok=True)
AUTHORS = {"vishnu":"Vishnu Vardhan","nithya":"Dodla Nithya Sai","beena":"Beena Reddy","sreekar":"Sreekar Reddy"}
CLS = {"money":"financial_manipulation","data":"data_exfiltration","code":"code_tool_manipulation","approval":"instruction_override","safety":"physical_safety_harm"}
VEC = {"email":"tool_output_manipulation","web page":"document_poisoning","document":"document_poisoning","tool result":"tool_output_manipulation","memory note":"memory_injection","another agent":"cross_agent_injection"}
MEM = {"planner","hr_agent","ops_agent","dev_agent"}

def field(block, name, end):
    m = re.search(re.escape(name)+r"\s*(.*?)\s*(?="+end+")", block, re.S)
    return m.group(1).strip() if m else ""

def parse_action(txt):
    m = re.search(r"([a-z_]+)\s*->\s*([a-z_]+)\(([^)]*)\)", txt) or re.search(r"->\s*([a-z_]+)\(([^)]*)\)", txt)
    if not m: return None
    if m.lastindex==3: src,tool,args=m.group(1),m.group(2),m.group(3)
    else: src,tool,args="action_agent",m.group(1),m.group(2)
    call={}
    for part in re.split(r",(?![^\[\]]*\])", args):
        if "=" in part:
            k,v=part.split("=",1); call[k.strip()]=v.strip().strip('"')
    return {"role":"assistant","source":src,"target":f"{tool}_tool","content":f"Calling {tool}.","tool_name":tool,"tool_call":call}

def step_to_hop(line):
    line=line.strip().lstrip("0123456789. ").strip()
    if not line: return None
    low=line.lower()
    m=re.match(r"([a-z_]+)\s*->\s*([a-z_]+):\s*(.*)",line)
    if "-> memory" in low or re.search(r"stores? ",low) and "memory" in low:
        src=re.match(r"([a-z_]+)",line); return {"role":"memory_write","source":src.group(1) if src else "planner","target":"shared_memory","content":line}
    if "reads memory" in low or "read memory" in low or "memory key" in low or "reads the stored" in low:
        src=re.match(r"([a-z_]+)",line); return {"role":"memory_read","source":src.group(1) if src else "planner","target":"shared_memory","content":line,"tool_name":"read_memory"}
    if m:
        src,tgt,body=m.groups()
        # tool output if the sender is returning content (contains quotes/returns) -> treat agent->planner carrying data as tool output when it quotes
        if any(k in body.lower() for k in ['ticket','returns','result','"',"'",'says','note from','reply','field','pricing','window','forecast','page','document','email','thread']) and tgt in ("planner",):
            return {"role":"tool","source":src,"target":tgt,"content":body,"tool_name":"read"}
        return {"role":"assistant","source":src,"target":tgt,"content":body}
    if any(k in low for k in ["returns","result:","page returns","document returns","document body","tool result"]):
        src=re.match(r"([a-z_]+)",line); return {"role":"tool","source":src.group(1) if src else "web_agent","target":"planner","content":line,"tool_name":"read"}
    if any(k in low for k in ["fetches","reads","calls","searches","locate","check "]):
        src=re.match(r"([a-z_]+)",line); return {"role":"tool","source":src.group(1) if src else "web_agent","target":"planner","content":line,"tool_name":"read"}
    src=re.match(r"([a-z_]+)",line)
    return {"role":"tool","source":src.group(1) if src else "web_agent","target":"planner","content":line,"tool_name":"read"}

blocks=re.split(r"\n(?=(?:vishnu|nithya|beena|sreekar)_[0-9])",RAW)
per={}
for b in blocks:
    m=re.match(r"((vishnu|nithya|beena|sreekar)_([0-9]))",b)
    if not m: continue
    sid,member=m.group(1),m.group(2)
    topic=field(b,"TOPIC:",r"ROUTE:").lower().strip()
    route=field(b,"ROUTE:",r"USER REQUEST:").lower().strip()
    goal=field(b,"USER REQUEST:",r"AGENTS/TOOLS:")
    steps_raw=field(b,"STEPS:",r"FINAL ACTION:")
    action_raw=field(b,"FINAL ACTION:",r"TWIN TYPE:")
    twin_kind=field(b,"TWIN TYPE:",r"TWIN CHANGE:").lower().strip()
    twin_change=re.search(r"TWIN CHANGE:\s*(.*)",b,re.S).group(1).strip().split("\n")[0]
    steps=[s for s in (step_to_hop(l) for l in steps_raw.split("\n")) if s]
    action=parse_action(action_raw)
    msgs=[{"role":"user","source":"user","target":"planner","content":goal}]+steps+([action] if action else [])
    # label last action malicious, planted untrusted hops unlabeled
    for h in msgs: h.setdefault("tool_call",None); h.setdefault("tool_name",None)
    attack={"id":sid,"author":AUTHORS[member],"is_attack":True,"attack_class":CLS[topic],"attack_vector":VEC.get(route,"document_poisoning"),
            "notes":b.split("\n")[0][:200],"messages":copy.deepcopy(msgs)} if (copy:=__import__("copy")) else None
    # twin
    tmsgs=copy.deepcopy(msgs)
    tmsgs[0]["content"]=goal  # default
    # apply authorized/designated goal edits: pull a new goal sentence if present
    gm=re.search(r'user request becomes:\s*"?(.*?)"?\.?$',twin_change,re.I)
    if twin_kind in ("authorized","designated") and gm: tmsgs[0]["content"]=gm.group(1)
    # resisted/normal: apply the written TWIN CHANGE to the final action args
    if twin_kind in ("resisted","normal") and tmsgs and tmsgs[-1]["role"]=="assistant" and tmsgs[-1]["tool_call"] is not None:
        tc=tmsgs[-1]["tool_call"]
        for k,v in re.findall(r'(\w+)=("[^"]+"|[\w.@:/+\-]+)',twin_change):
            if k in tc: tc[k]=v.strip('"')
        mu=re.search(r'uploads to\s+(\S+)',twin_change)
        if mu:
            for k in ("dest","url","destination"):
                if k in tc: tc[k]=mu.group(1).rstrip('.')
        if "shares only with" in twin_change.lower():
            for k in ("users","to"): tc.pop(k,None)
            tc["users"]=[re.search(r'with\s+(\S+@\S+)',twin_change).group(1).rstrip('.,')]
        md=re.search(r'default account\s+(\S+)',twin_change)
        if md:
            for k in ("payout_to","destination","account"):
                if k in tc: tc[k]=md.group(1).rstrip('.')
        mc=re.search(r'command is\s*"([^"]+)"',twin_change)
        if mc and "cmd" in tc: tc["cmd"]=mc.group(1)
        if "no role" in twin_change.lower() or "with no role" in twin_change.lower():
            for k in ("grant_role","role"): tc.pop(k,None)
    # designated: the story says the user-named file contains the value, so the agent reads that file before acting
    fm=re.search(r'([\w-]+\.(?:csv|docx|txt|md|pdf|xlsx|json))',twin_change)
    if twin_kind=="designated" and fm and tmsgs[-1]["role"]=="assistant" and tmsgs[-1].get("tool_call") is not None:
        fname=fm.group(1); agent=tmsgs[-1]["source"]
        said=re.search(r'that file ([^;]*)$',twin_change)
        vals=", ".join(str(v) if not isinstance(v,list) else ", ".join(v) for v in tmsgs[-1]["tool_call"].values())
        read={"role":"assistant","source":agent,"target":"read_file_tool","content":"Calling read_file.","tool_name":"read_file","tool_call":{"name":fname}}
        out={"role":"tool","source":"read_file_tool","target":agent,"content":f"{fname}: {said.group(1).strip() if said else ''} ({vals})","tool_name":"read_file","tool_call":None}
        tmsgs=tmsgs[:-1]+[read,out]+tmsgs[-1:]
    twin={"id":sid+"_twin","author":AUTHORS[member],"is_attack":False,"benign_kind":twin_kind if twin_kind in ("authorized","resisted","designated","normal") else "resisted",
          "notes":"TWIN: "+twin_change[:180],"messages":tmsgs}
    per.setdefault(member,[]).extend([attack,twin])

for member,rows in per.items():
    (OUTDIR/f"{member}.json").write_text(json.dumps(rows,indent=1,ensure_ascii=False))
    print(member,len(rows),"sessions")
