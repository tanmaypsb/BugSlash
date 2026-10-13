import json, re, shutil, subprocess, tempfile, xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from analyzer_models.go_analyzer import GoAnalyzer
from analyzer_models.rust_analyzer import RustAnalyzer
from models.go_source_fixes import GoFixError, remove_safe_unused
from models.finding_identity import finding_identity

class FindingNotFoundError(ValueError): pass
class FixVerificationError(RuntimeError): pass

class FixEngine:
    TIMEOUT=90
    SAFE_CPP_FIXES="readability-braces-around-statements"
    ANALYZER_CHECKS="clang-analyzer-*,bugprone-*,performance-*,readability-*"

    def fix_file(self,file_path): return self._fix(file_path)
    def fix_finding(self,file_path,selected):
        src=self._validate_path(file_path); lang=self._language(src)
        if selected.get("language","").lower() not in self._aliases(lang): raise ValueError("Finding language does not match the uploaded source.")
        if selected.get("analyzer","").lower()!=self._analyzer(lang): raise ValueError("Finding analyzer is not supported.")
        with self._workspace(src,lang) as (path,cwd):
            before=self._analyze_language(lang,path,cwd); match=self._match(before,selected)
            if match is None: raise FindingNotFoundError("The selected finding no longer matches this source.")
            result=self._pipeline(src,path,cwd,lang,before,selected.get("category") if lang=="python" else None)
            result["selected_finding"]=self._public(match,src.name)
            result["selected_resolved"]=not self._selected_remains(result["remaining_findings"],selected,src,result["fixed_code"],lang)
            result["scope_note"]="Safe fixes for the selected rule are applied where available across the file; all findings are re-analyzed. This fixer may address multiple instances of the same rule."
            if not result["selected_resolved"] and result["fixed"]: result["status"],result["verification_status"]="VERIFICATION_INCOMPLETE","INCOMPLETE"
            return result
    def _fix(self,filename):
        src=self._validate_path(filename); lang=self._language(src)
        with self._workspace(src,lang) as (path,cwd):
            return self._pipeline(src,path,cwd,lang,self._analyze_language(lang,path,cwd))
    @classmethod
    def _analyze(cls, source):
        src = Path(source)
        lang = cls._language(src)
        with cls._workspace(src, lang) as (path, cwd):
            return cls()._analyze_language(lang, path, cwd)

    @classmethod
    def _resolved_findings(cls, before, after, before_lines, after_lines, language=None):
        resolved, _introduced = cls._finding_differences(
            before, after, before_lines, after_lines, language
        )
        return len(resolved), sorted({str(item.get("code") or "") for item in resolved})

    @staticmethod
    def _fingerprint(item, lines, language=None):
        return finding_identity(item, lines, language)

    @classmethod
    def _finding_differences(cls, before, after, before_lines, after_lines, language=None):
        after_counts = Counter(cls._fingerprint(item, after_lines, language) for item in after)
        resolved = []
        for item in before:
            fingerprint = cls._fingerprint(item, before_lines, language)
            if after_counts[fingerprint]:
                after_counts[fingerprint] -= 1
            else:
                resolved.append(item)

        before_counts = Counter(cls._fingerprint(item, before_lines, language) for item in before)
        introduced = []
        for item in after:
            fingerprint = cls._fingerprint(item, after_lines, language)
            if before_counts[fingerprint]:
                before_counts[fingerprint] -= 1
            else:
                introduced.append(item)
        return resolved, introduced

    @classmethod
    def _selected_finding_remains(cls, findings, selected, before_lines, after_lines, language=None):
        expected = {
            "code": selected.get("category"),
            "message": selected.get("message"),
            "location": {"row": selected.get("line"), "column": selected.get("column", 1)},
        }
        signature = cls._fingerprint(expected, before_lines, language)
        return any(cls._fingerprint(item, after_lines, language) == signature for item in findings)

    def _pipeline(self,src,path,cwd,lang,before,selected_code=None):
        original=src.read_text(encoding="utf-8")
        try:
            self._apply(lang,path,cwd,selected_code)
            self._verify(lang,path,cwd)
            after=self._analyze_language(lang,path,cwd)
        except FixVerificationError as err:
            return self._result(src.name,None,before,before,"FIX_FAILED","FAILED","Configured verification failed: "+str(err)[:250],path.read_text(encoding="utf-8")!=original)
        except SyntaxError as err:
            return self._result(src.name,None,before,before,"FIX_FAILED","FAILED","Syntax verification failed: "+str(err)[:250],path.read_text(encoding="utf-8")!=original)
        except (OSError,subprocess.SubprocessError,RuntimeError,ValueError) as err:
            code=path.read_text(encoding="utf-8") if path.exists() else original
            return self._result(src.name,code,before,before,"VERIFICATION_INCOMPLETE","INCOMPLETE","Fix or verification could not complete: "+str(err)[:250],code!=original)
        code=path.read_text(encoding="utf-8")
        resolved_items,introduced_items=self._finding_differences(before,after,original.splitlines(),code.splitlines(),lang)
        resolved=len(resolved_items)
        introduced=len(introduced_items)
        if code==original: status,verify=("REVIEW_REQUIRED","REVIEW_REQUIRED") if after else ("NO_CHANGES","NOT_NEEDED"); msg="No safe automatic fix is available for remaining findings." if after else "The source is already clean."
        elif introduced>0: status,verify,msg="FIX_FAILED","FAILED","The change introduced new analyzer findings; the modified source is withheld."
        elif not after: status,verify,msg="FIX_VERIFIED","VERIFIED",self._label(lang)+" checks passed."
        elif resolved>0: status,verify,msg="PARTIALLY_FIXED","PARTIAL","Safe changes passed verification; findings remain."
        else: status,verify,msg="REVIEW_REQUIRED","REVIEW_REQUIRED","Configured checks passed, but no analyzer findings were resolved safely. Manual review is required."
        return self._result(src.name,None if status=="FIX_FAILED" else code,before,after,status,verify,msg,code!=original,resolved,introduced,resolved_items,introduced_items)
    def _apply(self,lang,path,cwd,selected_code=None):
        if lang=="python":
            args=["ruff","check",str(path),"--fix","--fix-only","--output-format","json"]
            if selected_code: args.extend(["--select",str(selected_code)])
            self._run(args,cwd,(0,1))
        elif lang in {"javascript","typescript"}: self._run([self._eslint(),str(path),"--config",str(self._backend()/"eslint.config.js"),"--fix","--fix-type","problem,layout","--format","json"],cwd,(0,1))
        elif lang=="cpp":
            self._run(["clang-tidy",str(path),"--checks="+self.SAFE_CPP_FIXES,"--fix","--","-std=c++17"],cwd)
            self._run(["clang-format","--style=LLVM","-i",str(path)],cwd)
        elif lang=="c":
            self._run(["clang-tidy",str(path),"--checks=readability-braces-around-statements","--fix","--","-x","c","-std=c11"],cwd)
            self._run(["clang-format","--style=LLVM","-i",str(path)],cwd)
        elif lang=="java": self._run(["clang-format","--style=Google","-i",str(path)],cwd)
        elif lang=="go":
            self._run(["gofmt","-w",str(path)],cwd)
            for _ in range(10):
                try:
                    self._run(["go","build","./..."],cwd)
                    break
                except RuntimeError as err:
                    try:
                        updated=remove_safe_unused(path.read_text(encoding="utf-8"),str(err))
                    except GoFixError as unsafe:
                        raise RuntimeError(f"Go compile check failed and no safe automatic fix applies: {unsafe}") from err
                    if updated == path.read_text(encoding="utf-8"):
                        raise RuntimeError("Go compile check reported unused declarations but the source did not change.") from err
                    path.write_text(updated,encoding="utf-8")
                    self._run(["gofmt","-w",str(path)],cwd)
            else:
                raise RuntimeError("Go compile checks did not converge after safe unused-declaration fixes.")
        elif lang=="rust":
            self._run(["cargo","clippy","--fix","--allow-no-vcs","--allow-dirty","--manifest-path",str(cwd/"Cargo.toml"),"--message-format=json"],cwd,(0,1))
            self._run(["rustfmt","--edition","2021",str(path)],cwd)
        else: raise ValueError("No fixer configured.")
    def _verify(self,lang,path,cwd):
        try:
            if lang=="python": compile(path.read_text(encoding="utf-8"),str(path),"exec")
            elif lang in {"javascript","typescript"}: self._run([self._eslint(),str(path),"--config",str(self._backend()/"eslint.config.js"),"--fix-dry-run","--fix-type","problem,layout","--format","json"],cwd,(0,1))
            elif lang in {"c","cpp"}: self._run(["clang-format","--style=LLVM","--dry-run","--Werror",str(path)],cwd)
            elif lang=="java": self._run(["clang-format","--style=Google","--dry-run","--Werror",str(path)],cwd)
            elif lang=="go":
                self._run(["go","build","./..."],cwd)
                self._run(["gofmt","-d",str(path)],cwd,expect_empty=True)
            elif lang=="rust": self._run(["rustfmt","--edition","2021","--check",str(path)],cwd)
        except (SyntaxError,RuntimeError,subprocess.SubprocessError) as err:
            raise FixVerificationError(str(err)) from err
    def _analyze_language(self,lang,path,cwd):
        if lang=="python":
            r=self._run(["ruff","check",str(path),"--output-format","json"],cwd,(0,1)); return [self._finding(x.get("code"),x.get("message"),x.get("location",{}).get("row"),x.get("location",{}).get("column"),path.name) for x in json.loads(r.stdout or "[]")]
        if lang in {"javascript","typescript"}:
            r=self._run([self._eslint(),str(path),"--config",str(self._backend()/"eslint.config.js"),"--format","json"],cwd,(0,1)); return [self._finding(x.get("ruleId") or "unknown",x.get("message"),x.get("line"),x.get("column"),path.name) for f in json.loads(r.stdout or "[]") for x in f.get("messages",[])]
        if lang in {"c","cpp"}:
            args=["clang-tidy",str(path),"--checks="+self.ANALYZER_CHECKS,"--"]+(["-x","c","-std=c11"] if lang=="c" else ["-std=c++17"])
            r=self._run(args,cwd); hits=re.findall(r"[^\n]*?:(\d+):(\d+): (?:warning|error): (.*?) \[([^\]]+)\]",r.stdout+"\n"+r.stderr)
            return [self._finding(code,msg,int(row),int(col),path.name) for row,col,msg,code in hits]
        if lang=="java":
            self._run(["mvn","-q","clean","compile","spotbugs:spotbugs"],cwd); xml=cwd/"target"/"spotbugsXml.xml"
            if not xml.exists(): raise RuntimeError("SpotBugs did not produce results.")
            out=[]
            for b in ET.parse(xml).getroot().findall("BugInstance"):
                s=b.find(".//SourceLine"); out.append(self._finding(b.get("type"),b.findtext("LongMessage",b.findtext("ShortMessage","Java finding")),int(s.get("start","1")) if s is not None else 1,0,path.name))
            return out
        if lang=="go":
            findings=GoAnalyzer().analyze(str(path))
            return [self._finding(item.category,item.message,item.line,item.column,path.name) for item in findings]
        if lang=="rust":
            findings=RustAnalyzer().analyze(str(path))
            return [self._finding(item.category,item.message,item.line,item.column,path.name) for item in findings]
        raise ValueError("No analyzer configured.")
    @staticmethod
    def _run(args,cwd,expected=(0,),expect_empty=False):
        r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=FixEngine.TIMEOUT,check=False)
        if r.returncode not in expected: raise RuntimeError(r.stderr.strip() or r.stdout.strip() or f"{args[0]} exited {r.returncode}")
        if expect_empty and r.stdout.strip(): raise RuntimeError(f"{args[0]} found formatting differences.")
        return r
    @staticmethod
    def _workspace(src,lang):
        class Ctx:
            def __enter__(self):
                self.temp=tempfile.TemporaryDirectory(prefix="bugslash-fix-", dir=FixEngine._backend()); self.cwd=Path(self.temp.name); self.path=self.cwd/src.name; shutil.copyfile(src,self.path)
                if lang=="java":
                    shutil.copyfile(FixEngine._backend()/"pom.xml",self.cwd/"pom.xml"); d=self.cwd/"src"/"main"/"java"; d.mkdir(parents=True); self.path=d/src.name; shutil.copyfile(src,self.path)
                if lang=="go": (self.cwd/"go.mod").write_text("module bugslash.local/upload\n\ngo 1.20\n",encoding="utf-8")
                if lang=="rust":
                    rust_source=src.read_text(encoding="utf-8")
                    if re.search(r"\bfn\s+main\s*\(",rust_source):
                        rust_dir=self.cwd/"src"; rust_dir.mkdir()
                        self.path=rust_dir/"main.rs"; shutil.copyfile(src,self.path)
                        (self.cwd/"Cargo.toml").write_text('[package]\nname="bugslash_upload"\nversion="0.1.0"\nedition="2021"\n',encoding="utf-8")
                    else:
                        rust_dir=self.cwd/"src"; rust_dir.mkdir()
                        self.path=rust_dir/"lib.rs"; shutil.copyfile(src,self.path)
                        (self.cwd/"Cargo.toml").write_text('[package]\nname="bugslash_upload"\nversion="0.1.0"\nedition="2021"\n',encoding="utf-8")
                return self.path,self.cwd
            def __exit__(self,*a): self.temp.cleanup()
        return Ctx()
    @staticmethod
    def _backend(): return Path(__file__).resolve().parents[1]
    @classmethod
    def _eslint(cls):
        p=cls._backend()/"node_modules"/".bin"/"eslint"; return str(p) if p.exists() else "eslint"
    @staticmethod
    def _language(p):
        return {".py":"python",".js":"javascript",".jsx":"javascript",".ts":"typescript",".tsx":"typescript",".c":"c",".h":"c",".cpp":"cpp",".cc":"cpp",".cxx":"cpp",".hpp":"cpp",".java":"java",".go":"go",".rs":"rust"}.get(p.suffix.lower(),"")
    @staticmethod
    def _validate_path(filename):
        p=Path(filename).resolve()
        if not p.is_file(): raise FileNotFoundError("Source file not found.")
        if not FixEngine._language(p): raise ValueError("Unsupported source file type.")
        try: p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e: raise ValueError("Source must be UTF-8.") from e
        return p
    @staticmethod
    def _aliases(lang): return {"javascript","typescript"} if lang in {"javascript","typescript"} else {"cpp","c++"} if lang=="cpp" else {lang}
    @staticmethod
    def _analyzer(lang): return {"python":"ruff","javascript":"eslint","typescript":"eslint","c":"clang-tidy","cpp":"clang-tidy","java":"spotbugs","go":"staticcheck","rust":"clippy"}.get(lang,"")
    @staticmethod
    def _label(lang): return {"python":"Ruff","javascript":"ESLint","typescript":"ESLint","c":"clang-format","cpp":"clang-tidy/clang-format","java":"clang-format/SpotBugs","go":"go fix/gofmt/Staticcheck","rust":"Clippy/rustfmt"}[lang]
    @staticmethod
    def _finding(code,msg,row,col,name): return {"code":str(code or "unknown"),"message":str(msg or ""),"filename":name,"location":{"row":int(row or 1),"column":int(col or 1)}}
    @staticmethod
    def _public(x,name): return {"code":x.get("code"),"message":x.get("message",""),"filename":name,"location":x.get("location",{"row":1,"column":1})}
    @staticmethod
    def _public_finding(x): return FixEngine._public(x, Path(x.get("filename", "source.py")).name)
    @classmethod
    def _resolved(cls, before, after, before_lines, after_lines, language=None):
        resolved, _introduced = cls._finding_differences(
            before, after, before_lines, after_lines, language
        )
        return len(resolved)
    @classmethod
    def _match(cls,fs,s):
        return next((x for x in fs if str(x.get("code"))==str(s.get("category")) and x["location"]["row"]==s.get("line") and x["location"]["column"]==s.get("column") and x["message"]==s.get("message")),None)
    _match_selected = _match
    @classmethod
    def _selected_remains(cls, findings, selected, source, code, language=None):
        if not isinstance(code, str):
            return True
        before_lines = source.read_text(encoding="utf-8").splitlines()
        after_lines = code.splitlines()
        return cls._selected_finding_remains(
            findings, selected, before_lines, after_lines, language
        )
    @classmethod
    def _resolved_codes(cls,b,a):
        before=Counter(str(x.get("code") or "") for x in b)
        after=Counter(str(x.get("code") or "") for x in a)
        return sorted(code for code,count in (before-after).items() if code and count>0)
    @classmethod
    def _result(cls,name,code,b,a,status,verify,message,fixed,resolved=0,introduced=0,resolved_items=None,introduced_items=None):
        return {"success":status!="FIX_FAILED","status":status,"verification_status":verify,"message":message,"fixed":fixed,"original_count":len(b),"resolved_count":resolved,"remaining_count":len(a),"introduced_count":introduced,"resolved_codes":sorted({str(x.get("code") or "") for x in resolved_items}) if resolved_items is not None else cls._resolved_codes(b,a),"original_findings":[cls._public(x,name) for x in b],"resolved_findings":[cls._public(x,name) for x in (resolved_items or [])],"remaining_findings":[cls._public(x,name) for x in a],"introduced_findings":[cls._public(x,name) for x in (introduced_items or [])],"filename":name,"fixed_code":code}
