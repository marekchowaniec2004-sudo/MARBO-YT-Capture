import json, os, shutil, uuid, webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP = "MARBO AI Cover"
VER = "2.0"
COLAB = "https://colab.research.google.com/github/marekchowaniec2004-sudo/MARBO-YT-Capture/blob/main/windows-ai-cover/MARBO_AI_Cover_Colab.ipynb"
CFG = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MARBO-AI-Cover" / "cloud.json"

PRESETS = {
    "Romantyczna orkiestra": "romantic orchestral arrangement, warm piano, lush strings, acoustic guitar, brushed drums, preserve original melody and song structure",
    "Fortepian i smyczki": "intimate piano and strings, cinematic, emotional, preserve original melody and song structure",
    "Akustyczny": "warm acoustic cover, acoustic guitars, soft piano, natural drums, preserve original melody and song structure",
    "Pop": "modern polished pop arrangement, punchy drums, warm bass, guitars and synths, preserve original melody and song structure",
    "Rock": "energetic rock arrangement, live drums, electric guitars, bass, preserve original melody and song structure",
    "Disco / dance": "upbeat disco dance arrangement, four on the floor drums, funky bass, rhythmic guitars, preserve original melody and song structure",
    "Włoskie lata 60.": "romantic Italian 1960s film soundtrack, acoustic guitar, piano, orchestral strings, brushed drums, warm vintage analog sound, preserve original melody and song structure",
    "Własny opis": "",
}

def layout(root):
    b = root / "MARBO AI Cover"
    d = {"base": b, "queue": b/"Queue", "status": b/"Status", "output": b/"Output", "done": b/"Done"}
    for p in d.values(): p.mkdir(parents=True, exist_ok=True)
    return d

def load_cfg():
    try: return json.loads(CFG.read_text(encoding="utf-8"))
    except: return {}

def save_cfg(path):
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps({"drive": path}, ensure_ascii=False), encoding="utf-8")

class Main(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} {VER} — Google Colab")
        self.geometry("1080x720")
        self.minsize(950,650)
        self.configure(bg="#11151b")
        self.drive = tk.StringVar(value=load_cfg().get("drive",""))
        self.audio = tk.StringVar()
        self.preset = tk.StringVar(value="Romantyczna orkiestra")
        self.strength = tk.DoubleVar(value=.68)
        self.strength_txt = tk.StringVar(value=".68")
        self.fmt = tk.StringVar(value="mp3")
        self.variants = tk.IntVar(value=2)
        self.info = tk.StringVar(value="Wybierz folder „Mój dysk” Google Drive.")
        self.outputs = []
        self.ui()
        self.after(4000, self.auto_refresh)

    def ui(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except:pass
        s.configure("TFrame",background="#11151b"); s.configure("Card.TFrame",background="#1b222c")
        s.configure("TLabel",background="#11151b",foreground="white",font=("Segoe UI",10))
        s.configure("Card.TLabel",background="#1b222c",foreground="white",font=("Segoe UI",10))
        s.configure("TButton",font=("Segoe UI",10),padding=8)
        s.configure("Accent.TButton",font=("Segoe UI Semibold",11),padding=11)

        r=ttk.Frame(self,padding=16); r.pack(fill="both",expand=True)
        ttk.Label(r,text="MARBO AI Cover — Google Colab",font=("Segoe UI Semibold",22)).pack(anchor="w")
        ttk.Label(r,text="MP3/WAV → Dysk Google → ACE-Step 1.5 na GPU Colab → gotowy cover").pack(anchor="w",pady=(2,12))
        body=ttk.Frame(r); body.pack(fill="both",expand=True); body.columnconfigure(0,weight=3); body.columnconfigure(1,weight=2); body.rowconfigure(0,weight=1)
        l=ttk.Frame(body,style="Card.TFrame",padding=14); l.grid(row=0,column=0,sticky="nsew",padx=(0,7))
        q=ttk.Frame(body,style="Card.TFrame",padding=14); q.grid(row=0,column=1,sticky="nsew",padx=(7,0))

        ttk.Label(l,text="1. Folder „Mój dysk” Google Drive",style="Card.TLabel",font=("Segoe UI Semibold",12)).pack(anchor="w")
        x=ttk.Frame(l,style="Card.TFrame"); x.pack(fill="x",pady=7)
        ttk.Entry(x,textvariable=self.drive).pack(side="left",fill="x",expand=True)
        ttk.Button(x,text="Wybierz",command=self.choose_drive).pack(side="left",padx=(7,0))

        ttk.Label(l,text="2. Plik źródłowy",style="Card.TLabel",font=("Segoe UI Semibold",12)).pack(anchor="w",pady=(8,0))
        x=ttk.Frame(l,style="Card.TFrame"); x.pack(fill="x",pady=7)
        ttk.Entry(x,textvariable=self.audio).pack(side="left",fill="x",expand=True)
        ttk.Button(x,text="Wybierz MP3 / WAV",command=self.choose_audio).pack(side="left",padx=(7,0))

        ttk.Label(l,text="3. Opis aranżacji",style="Card.TLabel",font=("Segoe UI Semibold",12)).pack(anchor="w",pady=(8,0))
        cb=ttk.Combobox(l,textvariable=self.preset,values=list(PRESETS),state="readonly"); cb.pack(fill="x",pady=(7,5)); cb.bind("<<ComboboxSelected>>",self.apply_preset)
        self.prompt=tk.Text(l,height=8,bg="#0d1117",fg="white",insertbackground="white",relief="flat",font=("Segoe UI",11),wrap="word")
        self.prompt.pack(fill="x"); self.prompt.insert("1.0",PRESETS[self.preset.get()])

        f=ttk.Frame(l,style="Card.TFrame"); f.pack(fill="x",pady=10); f.columnconfigure(1,weight=1)
        ttk.Label(f,text="Podobieństwo:",style="Card.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Scale(f,from_=.1,to=1,variable=self.strength,command=lambda _:self.strength_txt.set(f"{self.strength.get():.2f}")).grid(row=0,column=1,sticky="ew",padx=8)
        ttk.Label(f,textvariable=self.strength_txt,style="Card.TLabel").grid(row=0,column=2)
        ttk.Label(f,text="Format:",style="Card.TLabel").grid(row=1,column=0,sticky="w",pady=(8,0))
        ttk.Combobox(f,textvariable=self.fmt,values=["mp3","wav"],state="readonly",width=7).grid(row=1,column=1,sticky="w",padx=8,pady=(8,0))
        ttk.Label(f,text="Wersje:",style="Card.TLabel").grid(row=2,column=0,sticky="w",pady=(8,0))
        ttk.Spinbox(f,from_=1,to=4,textvariable=self.variants,width=6).grid(row=2,column=1,sticky="w",padx=8,pady=(8,0))
        ttk.Button(l,text="WYŚLIJ DO COLAB — GENERUJ COVER AI",style="Accent.TButton",command=self.send).pack(fill="x",pady=(5,0))

        ttk.Label(q,text="Google Colab",style="Card.TLabel",font=("Segoe UI Semibold",12)).pack(anchor="w")
        ttk.Button(q,text="Otwórz notebook Colab",command=lambda:webbrowser.open(COLAB)).pack(fill="x",pady=(8,5))
        ttk.Button(q,text="Sprawdź Google Drive",command=self.check_drive).pack(fill="x",pady=5)
        ttk.Button(q,text="Otwórz folder roboczy",command=self.open_base).pack(fill="x",pady=5)
        ttk.Separator(q).pack(fill="x",pady=12)
        ttk.Label(q,text="Status zadań",style="Card.TLabel",font=("Segoe UI Semibold",12)).pack(anchor="w")
        self.jobs=tk.Listbox(q,bg="#0d1117",fg="white",relief="flat",height=10); self.jobs.pack(fill="x",pady=7)
        ttk.Button(q,text="Odśwież",command=self.refresh).pack(fill="x")
        ttk.Label(q,text="Gotowe pliki",style="Card.TLabel",font=("Segoe UI Semibold",12)).pack(anchor="w",pady=(12,0))
        self.out=tk.Listbox(q,bg="#0d1117",fg="white",relief="flat",height=9); self.out.pack(fill="both",expand=True,pady=7)
        z=ttk.Frame(q,style="Card.TFrame"); z.pack(fill="x")
        ttk.Button(z,text="Odtwórz",command=self.play).pack(side="left",fill="x",expand=True,padx=(0,3))
        ttk.Button(z,text="Output",command=self.open_output).pack(side="left",fill="x",expand=True,padx=(3,0))
        ttk.Label(r,textvariable=self.info).pack(anchor="w",pady=(10,0))

    def root(self,quiet=False):
        p=Path(self.drive.get().strip())
        if not p.exists():
            if not quiet: messagebox.showwarning("Google Drive","Wybierz lokalny folder „Mój dysk” z programu Google Drive na komputer.")
            return None
        save_cfg(str(p)); return p

    def choose_drive(self):
        p=filedialog.askdirectory(title="Wybierz folder „Mój dysk” Google Drive")
        if p:self.drive.set(p); save_cfg(p); self.check_drive()

    def choose_audio(self):
        p=filedialog.askopenfilename(filetypes=[("Audio","*.mp3 *.wav *.flac *.m4a *.aac *.ogg"),("Wszystkie","*.*")])
        if p:self.audio.set(p)

    def apply_preset(self,_=None):
        v=PRESETS[self.preset.get()]
        if v:self.prompt.delete("1.0","end"); self.prompt.insert("1.0",v)

    def check_drive(self):
        p=self.root()
        if p:
            d=layout(p); self.info.set("Google Drive gotowy: "+str(d["base"]))
            messagebox.showinfo("Gotowe","Foldery kolejki są gotowe.\nTeraz otwórz notebook Colab i uruchom wszystkie komórki.")

    def send(self):
        root=self.root()
        src=Path(self.audio.get().strip())
        prompt=self.prompt.get("1.0","end").strip()
        if not root:return
        if not src.exists():messagebox.showwarning("Plik","Wybierz plik audio.");return
        if not prompt:messagebox.showwarning("Opis","Wpisz opis aranżacji.");return
        d=layout(root)
        jid=datetime.now().strftime("%Y%m%d_%H%M%S")+"_"+uuid.uuid4().hex[:6]
        name=f"{jid}__{src.name}"
        target=d["queue"]/name
        tmp=target.with_suffix(target.suffix+".uploading")
        shutil.copy2(src,tmp); tmp.replace(target)
        try:n=max(1,min(4,int(self.variants.get())))
        except:n=1
        job={"job_id":jid,"created_at":datetime.now().isoformat(timespec="seconds"),"source_name":name,"source_size":target.stat().st_size,
             "original_name":src.name,"prompt":prompt,"task_type":"cover","audio_cover_strength":round(self.strength.get(),3),
             "audio_format":self.fmt.get(),"batch_size":n,"model":"acestep-v15-turbo","inference_steps":8}
        jp=d["queue"]/f"{jid}.json"; t=jp.with_suffix(".json.uploading"); t.write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding="utf-8"); t.replace(jp)
        self.info.set("Zadanie wysłane: "+jid); self.refresh()
        messagebox.showinfo("Wysłano","Zadanie jest w kolejce. Uruchomiony Colab odbierze je po synchronizacji Dysku Google.")

    def refresh(self):
        p=self.root(True)
        if not p:return
        d=layout(p); self.jobs.delete(0,"end")
        rows={}
        for f in d["queue"].glob("*.json"):
            try:a=json.loads(f.read_text(encoding="utf-8")); rows[a["job_id"]]=("OCZEKUJE",a)
            except:pass
        for f in d["status"].glob("*.json"):
            try:
                a=json.loads(f.read_text(encoding="utf-8")); st={"processing":"GENEROWANIE","completed":"GOTOWE","failed":"BŁĄD"}.get(a.get("status"),a.get("status",""))
                rows[a["job_id"]]=(st,a)
            except:pass
        for _,(st,a) in sorted(rows.items(),reverse=True)[:20]: self.jobs.insert("end",f"{st:12}  {a.get('original_name','')}")
        self.outputs=sorted([f for f in d["output"].iterdir() if f.is_file()],key=lambda x:x.stat().st_mtime,reverse=True)
        self.out.delete(0,"end")
        for f in self.outputs[:50]:self.out.insert("end",f.name)

    def auto_refresh(self):
        self.refresh(); self.after(4000,self.auto_refresh)

    def open_base(self):
        p=self.root()
        if p:os.startfile(str(layout(p)["base"]))

    def open_output(self):
        p=self.root()
        if p:os.startfile(str(layout(p)["output"]))

    def play(self):
        s=self.out.curselection()
        if s and s[0]<len(self.outputs):os.startfile(str(self.outputs[s[0]]))

if __name__=="__main__": Main().mainloop()
