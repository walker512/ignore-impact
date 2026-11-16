#!/usr/bin/env python3
"""Read-only Git ignore experiments. Python stdlib + Git; no third-party code."""
import argparse, json, os, secrets, stat, subprocess, tempfile
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

MAX_FILES = 20000
MAX_RULE_BYTES = 262144

def git(root, *args, data=None):
    env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    p = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath='+os.devnull, '-c', 'core.excludesFile='+os.devnull, '-C', str(root), *args], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30)
    if p.returncode not in (0,1):
        raise ValueError(p.stderr.decode('utf-8', 'replace').strip())
    return p.stdout

def rule_text(path):
    if path.is_symlink(): raise ValueError('Symlink ignore files are unsupported: '+str(path.name))
    if not stat.S_ISREG(path.stat().st_mode): raise ValueError('Ignore input must be a regular file')
    with path.open('rb') as handle: raw = handle.read(MAX_RULE_BYTES+1)
    if len(raw)>MAX_RULE_BYTES: raise ValueError('Ignore file exceeds 256 KiB')
    return raw.decode('utf-8')

class Snapshot:
    def __init__(self, repository):
        root = Path(repository).resolve()
        top = git(root, 'rev-parse', '--show-toplevel').decode().strip()
        if not top or Path(top).resolve()!=root: raise ValueError('Select the repository root, not a subfolder.')
        self.files=[]; self.rules={}; self.tracked=set()
        raw=git(root,'ls-files','-z','--stage')
        for entry in raw.decode('utf-8').split('\0'):
            if not entry: continue
            metadata, name = entry.split('\t', 1)
            if metadata.startswith('160000 '): raise ValueError('Submodules are not supported. Scan them separately.')
            self.tracked.add(name)
        def scan_error(error):
            raise ValueError('Unable to read a directory; no partial snapshot is produced: '+str(error))
        for base, dirs, names in os.walk(root, followlinks=False, onerror=scan_error):
            rel=Path(base).relative_to(root)
            if rel != Path('.') and '.git' in dirs+names:
                raise ValueError('Nested repositories/submodules are not supported. Scan them separately.')
            dirs[:]=[d for d in dirs if d!='.git']
            links=[d for d in dirs if (Path(base)/d).is_symlink()]
            dirs[:]=[d for d in dirs if d not in links]
            for name in names+links:
                if name=='.git': continue
                path=Path(base)/name
                relative=path.relative_to(root).as_posix()
                # UTF-8 paths only; fail rather than silently changing a filename.
                relative.encode('utf-8')
                self.files.append(relative)
                if len(self.files)>MAX_FILES: raise ValueError('More than 20,000 files. No partial result is produced.')
                if name=='.gitignore': self.rules[relative]=rule_text(path)
        self.files.sort()
        self.original=self.rules.get('.gitignore','')
        self.version=git(root,'--version').decode().strip()
        self.baseline=self.evaluate(self.original)

    def evaluate(self, candidate):
        if not isinstance(candidate,str) or len(candidate.encode())>MAX_RULE_BYTES or '\0' in candidate:
            raise ValueError('Candidate must be UTF-8 text, at most 256 KiB, without NUL.')
        with tempfile.TemporaryDirectory(prefix='ignore-impact-') as folder:
            target=Path(folder)
            git(target,'init','-q','--template=')
            for name in self.files:
                dest=target/name; dest.parent.mkdir(parents=True,exist_ok=True); dest.touch()
            for name,text in self.rules.items(): (target/name).write_bytes(text.encode('utf-8'))
            (target/'.gitignore').write_bytes(candidate.encode('utf-8'))
            raw=git(target,'check-ignore','--no-index','--verbose','--non-matching','-z','--stdin',data=('\0'.join(self.files)+'\0').encode()) if self.files else b''
        bits=raw.decode('utf-8').split('\0')
        result={}
        for i in range(0,len(bits)-1,4):
            source,line,pattern,name=bits[i:i+4]
            matched=bool(pattern) and not pattern.startswith('!')
            tracked=name in self.tracked
            result[name]={'path':name,'tracked':tracked,'ruleIgnored':matched,'ignored':matched and not tracked,'source':source,'line':line,'pattern':pattern}
        if len(result)!=len(self.files): raise ValueError('Git returned an incomplete result.')
        return result

    def compare(self, candidate, contract):
        if not isinstance(contract,dict) or set(contract)-{'ignore','include'}: raise ValueError('Contract must contain only ignore/include lists.')
        for key in ('ignore','include'):
            vals=contract.get(key,[])
            if not isinstance(vals,list) or any(not isinstance(x,str) for x in vals) or len(vals)>MAX_FILES: raise ValueError('Contract values must be lists of exact relative file paths.')
        after=self.evaluate(candidate)
        rows=[]
        for name,before in self.baseline.items():
            now=after[name]; change='newly ignored' if now['ignored'] and not before['ignored'] else 'newly exposed' if before['ignored'] and not now['ignored'] else 'unchanged'
            rows.append({'path':name,'before':before,'after':now,'change':change})
        checks=[]
        for kind in ('ignore','include'):
            for name in contract.get(kind,[]):
                item=after.get(name)
                ok=item is not None and item['ignored']==(kind=='ignore')
                checks.append({'path':name,'expect':kind,'pass':ok,'reason':'path absent from snapshot' if item is None else 'tracked files cannot be ignored' if item['tracked'] and kind=='ignore' else 'matched' if ok else 'unexpected verdict'})
        return {'version':1,'mode':'portable repository rules only','git':self.version,'files':len(rows),'changes':sum(r['change']!='unchanged' for r in rows),'checks':checks,'rows':rows}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,body,mime='application/json'):
        b=body.encode(); self.send_response(status); self.send_header('Content-Type',mime+'; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(b)
    def authorized(self): return self.headers.get('Host')==self.server.host
    def do_GET(self):
        if not self.authorized(): return self.reply(403,'{}')
        if self.path=='/api/init': return self.reply(200,json.dumps({'rules':self.server.snapshot.original,'token':self.server.token,'files':len(self.server.snapshot.files)}))
        mapping={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
        if self.path not in mapping:return self.reply(404,'{}')
        filename,mime=mapping[self.path]; self.reply(200,(Path(__file__).parent/filename).read_text(),mime)
    def do_POST(self):
        if not self.authorized() or self.headers.get('X-Token')!=self.server.token or self.headers.get('Origin')!='http://'+self.server.host: return self.reply(403,'{}')
        if self.path!='/api/compare':return self.reply(404,'{}')
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<2000000: raise ValueError('Request size invalid')
            data=json.loads(self.rfile.read(n)); report=self.server.snapshot.compare(data['rules'],data.get('contract',{})); self.reply(200,json.dumps(report))
        except (ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as exc:self.reply(400,json.dumps({'error':str(exc)}))

def main():
    parser=argparse.ArgumentParser(description='Read-only .gitignore what-if and exact-path contracts. Portable repository rules only.')
    parser.add_argument('repo'); parser.add_argument('--candidate',type=Path); parser.add_argument('--contract',type=Path); parser.add_argument('--port',type=int,default=8766); parser.add_argument('--json',action='store_true',help='Print report instead of serving UI (filenames and patterns included)')
    args=parser.parse_args()
    try:
        snapshot=Snapshot(args.repo)
        if args.json:
            report=snapshot.compare(rule_text(args.candidate) if args.candidate else snapshot.original,json.loads(args.contract.read_text()) if args.contract else {})
            print(json.dumps(report,indent=2)); return 1 if any(not c['pass'] for c in report['checks']) else 0
        server=HTTPServer(('127.0.0.1',args.port),Handler); server.host='127.0.0.1:'+str(server.server_port); server.token=secrets.token_urlsafe(32); server.snapshot=snapshot
        print('Open http://'+server.host+' (Ctrl+C to stop). Snapshot fixed at startup; repository is never edited.',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
        return 0
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
        print('Error: '+str(exc),file=__import__('sys').stderr); return 2
if __name__=='__main__':raise SystemExit(main())
