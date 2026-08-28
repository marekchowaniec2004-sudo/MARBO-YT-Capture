import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "MARBO AI Cover"
VERSION = "1.0.0"
BASE_URL = "http://127.0.0.1:8001"
ACE_ZIP_URL = "https://github.com/ace-step/ACE-Step-1.5/archive/refs/heads/main.zip"

LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
APP_DIR = LOCAL_APPDATA / "MARBO-AI-Cover"
ENGINE_DIR = APP_DIR / "ACE-Step-1.5"
LOG_DIR = APP_DIR / "logs"
OUTPUT_DIR = Path.home() / "Documents" / "MARBO AI Cover" / "Output"
SERVER_LOG = LOG_DIR / "acestep-server.log"

PRESETS = {
    "Własny opis": "",
    "Romantyczna orkiestra": "romantic orchestral arrangement, warm piano, lush strings, acoustic guitar, brushed drums, expressive dynamics, preserve the original melody and song structure",
    "Fortepian i smyczki": "intimate piano and string ensemble arrangement, cinematic, emotional, elegant, preserve the original melody and structure",
    "Akustyczny": "warm acoustic cover, acoustic guitars, soft piano, natural drums, organic production, preserve the original melody and structure",
    "Pop": "modern polished pop arrangement, punchy drums, warm bass, bright guitars and synth layers, preserve the original melody and structure",
    "Rock": "energetic rock arrangement, live drums, electric guitars, bass guitar, dynamic chorus, preserve the original melody and structure",
    "Disco / dance": "upbeat disco dance arrangement, four on the floor drums, funky bass, rhythmic guitars, bright strings and synths, preserve the original melody and structure",
    "Włoskie lata 60.": "romantic Italian 1960s film soundtrack style, acoustic guitar, piano, orchestral strings, brushed drums, warm vintage analog character, preserve the original melody and structure",
}


def safe_mkdirs():
    for p in (APP_DIR, LOG_DIR, OUTPUT_DIR):
        p.mkdir(parents=True, exist_ok=True)


def find_uv():
    candidates = []
    found = shutil.which("uv")
    if found:
        candidates.append(Path(found))
    user = Path.home()
    candidates.extend([
        user / ".local" / "bin" / "uv.exe",
        LOCAL_APPDATA / "Programs" / "uv" / "uv.exe",
        LOCAL_APPDATA / "uv" / "uv.exe",
    ])
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def creation_flags():
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        safe_mkdirs()
        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1120x760")
        self.minsize(980, 680)
        self.configure(bg="#111318")
        self.server_process = None
        self.source_file = tk.StringVar()
        self.preset_var = tk.StringVar(value="Romantyczna orkiestra")
        self.strength_var = tk.DoubleVar(value=0.68)
        self.strength_text = tk.StringVar(value="0.68")
        self.format_var = tk.StringVar(value="mp3")
        self.variants_var = tk.IntVar(value=2)
        self.offload_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Gotowy.")
        self.engine_var = tk.StringVar(value="Silnik AI: sprawdzanie...")
        self.output_files = []
        self.busy = False
        self._build_ui()
        self.after(200, self.refresh_engine_status)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#111318")
        style.configure("Card.TFrame", background="#1b1f27")
        style.configure("TLabel", background="#111318", foreground="#f4f4f4", font=("Segoe UI", 10))
        style.configure("Card.TLabel", background="#1b1f27", foreground="#f4f4f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#111318", foreground="#ffffff", font=("Segoe UI Semibold", 22))
        style.configure("Sub.TLabel", background="#111318", foreground="#aeb5c2", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=10)
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("TCombobox", padding=5)
        style.configure("Horizontal.TProgressbar", thickness=12)

        root = ttk.Frame(self, padding=18)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="MARBO AI Cover", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Nowa aranżacja AI na podstawie MP3/WAV — lokalnie przez ACE-Step 1.5",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Card.TFrame", padding=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ttk.Frame(body, style="Card.TFrame", padding=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(left, text="1. Plik źródłowy", style="Card.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        file_row = ttk.Frame(left, style="Card.TFrame")
        file_row.pack(fill="x", pady=(8, 14))
        file_entry = ttk.Entry(file_row, textvariable=self.source_file)
        file_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(file_row, text="Wybierz MP3 / WAV", command=self.choose_file).pack(side="left", padx=(8, 0))

        ttk.Label(left, text="2. Styl / opis nowej aranżacji", style="Card.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        preset_row = ttk.Frame(left, style="Card.TFrame")
        preset_row.pack(fill="x", pady=(8, 6))
        ttk.Label(preset_row, text="Preset:", style="Card.TLabel").pack(side="left")
        preset = ttk.Combobox(preset_row, textvariable=self.preset_var, values=list(PRESETS.keys()), state="readonly", width=26)
        preset.pack(side="left", padx=(8, 0))
        preset.bind("<<ComboboxSelected>>", self.apply_preset)

        self.prompt = tk.Text(
            left,
            height=9,
            wrap="word",
            bg="#0e1117",
            fg="#f5f7fa",
            insertbackground="#ffffff",
            relief="flat",
            font=("Segoe UI", 11),
            padx=10,
            pady=10,
        )
        self.prompt.pack(fill="x", pady=(4, 12))
        self.prompt.insert("1.0", PRESETS[self.preset_var.get()])

        settings = ttk.Frame(left, style="Card.TFrame")
        settings.pack(fill="x", pady=(4, 8))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Podobieństwo do oryginału:", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        scale = ttk.Scale(settings, from_=0.10, to=1.0, variable=self.strength_var, command=self.on_strength)
        scale.grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Label(settings, textvariable=self.strength_text, style="Card.TLabel", width=5).grid(row=0, column=2)

        ttk.Label(settings, text="Format:", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 0))
        fmt = ttk.Combobox(settings, textvariable=self.format_var, values=["mp3", "wav"], state="readonly", width=8)
        fmt.grid(row=1, column=1, sticky="w", padx=10, pady=(10, 0))

        ttk.Label(settings, text="Liczba wersji:", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=(10, 0))
        spin = ttk.Spinbox(settings, from_=1, to=4, textvariable=self.variants_var, width=6)
        spin.grid(row=2, column=1, sticky="w", padx=10, pady=(10, 0))

        ttk.Checkbutton(
            settings,
            text="Tryb oszczędny GPU (część modelu może być przenoszona do RAM/CPU)",
            variable=self.offload_var,
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 0))

        note = (
            "Wskazówka: 0.55–0.75 zwykle daje wyraźnie nową aranżację przy zachowaniu charakteru utworu. "
            "Wynik zależy od nagrania i modelu AI."
        )
        ttk.Label(left, text=note, style="Card.TLabel", foreground="#aeb5c2", wraplength=610).pack(anchor="w", pady=(8, 14))

        self.generate_btn = ttk.Button(left, text="GENERUJ COVER AI", style="Accent.TButton", command=self.generate_cover)
        self.generate_btn.pack(fill="x", ipady=5)

        ttk.Label(right, text="Silnik AI", style="Card.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        ttk.Label(right, textvariable=self.engine_var, style="Card.TLabel", foreground="#d8dde7", wraplength=390).pack(anchor="w", pady=(8, 10))

        engine_buttons = ttk.Frame(right, style="Card.TFrame")
        engine_buttons.pack(fill="x")
        ttk.Button(engine_buttons, text="Zainstaluj / napraw silnik", command=self.install_engine).pack(fill="x", pady=(0, 6))
        ttk.Button(engine_buttons, text="Uruchom silnik", command=self.start_engine).pack(fill="x", pady=6)
        ttk.Button(engine_buttons, text="Sprawdź silnik", command=self.refresh_engine_status).pack(fill="x", pady=6)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=14)

        ttk.Label(right, text="Wyniki", style="Card.TLabel", font=("Segoe UI Semibold", 12)).pack(anchor="w")
        self.outputs = tk.Listbox(
            right,
            bg="#0e1117",
            fg="#f4f4f4",
            selectbackground="#3b82f6",
            selectforeground="#ffffff",
            relief="flat",
            height=10,
            font=("Segoe UI", 9),
        )
        self.outputs.pack(fill="both", expand=True, pady=(8, 8))
        out_buttons = ttk.Frame(right, style="Card.TFrame")
        out_buttons.pack(fill="x")
        ttk.Button(out_buttons, text="Odtwórz wybrany", command=self.play_selected).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(out_buttons, text="Otwórz folder", command=self.open_output_folder).pack(side="left", fill="x", expand=True, padx=(4, 0))

        footer = ttk.Frame(root)
        footer.pack(fill="x", pady=(12, 0))
        self.progress = ttk.Progressbar(footer, mode="indeterminate")
        self.progress.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var, style="Sub.TLabel", wraplength=1050).pack(anchor="w", pady=(6, 0))
        ttk.Label(
            footer,
            text="Używaj nagrań, do których masz odpowiednie prawa lub zgodę na tworzenie opracowań.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(4, 0))

    def on_strength(self, _=None):
        self.strength_text.set(f"{self.strength_var.get():.2f}")

    def apply_preset(self, _=None):
        value = PRESETS.get(self.preset_var.get(), "")
        if value:
            self.prompt.delete("1.0", "end")
            self.prompt.insert("1.0", value)

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Wybierz utwór",
            filetypes=[("Audio", "*.mp3 *.wav *.flac *.m4a *.aac *.ogg"), ("Wszystkie pliki", "*.*")],
        )
        if path:
            self.source_file.set(path)

    def set_busy(self, busy, message=None):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.generate_btn.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
        if message:
            self.status_var.set(message)

    def thread(self, fn):
        t = threading.Thread(target=fn, daemon=True)
        t.start()

    def refresh_engine_status(self):
        def work():
            installed = (ENGINE_DIR / "pyproject.toml").exists() and find_uv() is not None
            running = self.is_engine_running()
            if running:
                text = "Silnik AI: URUCHOMIONY — gotowy do generowania."
            elif installed:
                text = "Silnik AI: zainstalowany, ale obecnie nie jest uruchomiony."
            else:
                text = "Silnik AI: nie jest jeszcze zainstalowany. Pierwsza instalacja pobierze zależności i model AI."
            self.after(0, self.engine_var.set, text)
        self.thread(work)

    def is_engine_running(self):
        try:
            r = requests.get(BASE_URL + "/health", timeout=2)
            return r.ok
        except Exception:
            return False

    def install_engine(self):
        if self.busy:
            return
        if not messagebox.askyesno(
            "Instalacja silnika AI",
            "Program pobierze ACE-Step 1.5, środowisko Python i model AI.\n\n"
            "Potrzebne jest szybkie łącze internetowe oraz kilka-kilkanaście GB wolnego miejsca.\n\nKontynuować?",
        ):
            return
        self.set_busy(True, "Instaluję silnik AI. To może potrwać kilkanaście lub kilkadziesiąt minut przy pierwszym uruchomieniu...")

        def work():
            try:
                safe_mkdirs()
                uv = find_uv()
                if not uv:
                    self.after(0, self.status_var.set, "Instaluję menedżer środowiska uv...")
                    cmd = [
                        "powershell.exe",
                        "-NoProfile",
                        "-ExecutionPolicy", "Bypass",
                        "-Command",
                        "irm https://astral.sh/uv/install.ps1 | iex",
                    ]
                    subprocess.run(cmd, check=True, creationflags=creation_flags())
                    uv = find_uv()
                    if not uv:
                        raise RuntimeError("Nie udało się odnaleźć uv.exe po instalacji.")

                if not (ENGINE_DIR / "pyproject.toml").exists():
                    self.after(0, self.status_var.set, "Pobieram ACE-Step 1.5...")
                    with tempfile.TemporaryDirectory() as td:
                        zip_path = Path(td) / "ace.zip"
                        with requests.get(ACE_ZIP_URL, stream=True, timeout=120) as r:
                            r.raise_for_status()
                            with open(zip_path, "wb") as f:
                                for chunk in r.iter_content(chunk_size=1024 * 1024):
                                    if chunk:
                                        f.write(chunk)
                        extract_dir = Path(td) / "extract"
                        with zipfile.ZipFile(zip_path, "r") as zf:
                            zf.extractall(extract_dir)
                        roots = [p for p in extract_dir.iterdir() if p.is_dir()]
                        if not roots:
                            raise RuntimeError("Nie znaleziono katalogu ACE-Step w pobranym archiwum.")
                        if ENGINE_DIR.exists():
                            shutil.rmtree(ENGINE_DIR, ignore_errors=True)
                        shutil.move(str(roots[0]), str(ENGINE_DIR))

                self.after(0, self.status_var.set, "Instaluję biblioteki AI (uv sync)...")
                subprocess.run([uv, "sync"], cwd=ENGINE_DIR, check=True, creationflags=creation_flags())

                self.after(0, self.status_var.set, "Pobieram główny model ACE-Step. To jest największy etap instalacji...")
                env = os.environ.copy()
                env["ACESTEP_INIT_LLM"] = "false"
                subprocess.run([uv, "run", "acestep-download"], cwd=ENGINE_DIR, env=env, check=True, creationflags=creation_flags())

                self.after(0, self.engine_var.set, "Silnik AI: zainstalowany. Możesz go uruchomić.")
                self.after(0, messagebox.showinfo, "Gotowe", "Silnik ACE-Step został zainstalowany. Teraz kliknij „Uruchom silnik”.")
            except Exception as exc:
                self.after(0, messagebox.showerror, "Błąd instalacji", str(exc))
                self.after(0, self.status_var.set, f"Błąd instalacji: {exc}")
            finally:
                self.after(0, self.set_busy, False)
                self.after(200, self.refresh_engine_status)
        self.thread(work)

    def start_engine(self):
        if self.busy:
            return
        self.set_busy(True, "Uruchamiam silnik AI...")

        def work():
            try:
                if self.is_engine_running():
                    self.after(0, self.engine_var.set, "Silnik AI: URUCHOMIONY — gotowy do generowania.")
                    self.after(0, self.status_var.set, "Silnik jest już uruchomiony.")
                    return
                uv = find_uv()
                if not uv or not (ENGINE_DIR / "pyproject.toml").exists():
                    raise RuntimeError("Silnik nie jest zainstalowany. Najpierw kliknij „Zainstaluj / napraw silnik”.")

                safe_mkdirs()
                env = os.environ.copy()
                env["ACESTEP_API_HOST"] = "127.0.0.1"
                env["ACESTEP_API_PORT"] = "8001"
                env["ACESTEP_INIT_LLM"] = "false"
                env["ACESTEP_CONFIG_PATH"] = "acestep-v15-turbo"
                env["ACESTEP_OFFLOAD_TO_CPU"] = "true" if self.offload_var.get() else "false"

                log_handle = open(SERVER_LOG, "a", encoding="utf-8")
                cmd = [uv, "run", "python", "-m", "acestep.api_server", "--host", "127.0.0.1", "--port", "8001"]
                self.server_process = subprocess.Popen(
                    cmd,
                    cwd=ENGINE_DIR,
                    env=env,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=creation_flags(),
                )

                for _ in range(60):
                    if self.is_engine_running():
                        self.after(0, self.engine_var.set, "Silnik AI: URUCHOMIONY — gotowy do generowania.")
                        self.after(0, self.status_var.set, "Silnik AI działa na tym komputerze.")
                        return
                    if self.server_process.poll() is not None:
                        raise RuntimeError(f"Silnik zakończył działanie. Sprawdź log: {SERVER_LOG}")
                    time.sleep(2)
                raise RuntimeError(f"Silnik nie odpowiedział w wyznaczonym czasie. Sprawdź log: {SERVER_LOG}")
            except Exception as exc:
                self.after(0, messagebox.showerror, "Błąd uruchamiania", str(exc))
                self.after(0, self.status_var.set, f"Błąd uruchamiania: {exc}")
            finally:
                self.after(0, self.set_busy, False)
                self.after(200, self.refresh_engine_status)
        self.thread(work)

    def generate_cover(self):
        if self.busy:
            return
        source = Path(self.source_file.get().strip())
        prompt = self.prompt.get("1.0", "end").strip()
        if not source.exists():
            messagebox.showwarning("Brak pliku", "Wybierz plik MP3/WAV do przerobienia.")
            return
        if not prompt:
            messagebox.showwarning("Brak opisu", "Wpisz opis nowej aranżacji.")
            return
        if not self.is_engine_running():
            messagebox.showwarning("Silnik AI", "Silnik AI nie jest uruchomiony. Kliknij „Uruchom silnik”.")
            return

        try:
            variants = max(1, min(4, int(self.variants_var.get())))
        except Exception:
            variants = 1

        self.set_busy(True, "Wysyłam utwór do lokalnego silnika AI...")

        def work():
            try:
                mime = mimetypes.guess_type(str(source))[0] or "application/octet-stream"
                data = {
                    "prompt": prompt,
                    "task_type": "cover",
                    "audio_cover_strength": f"{self.strength_var.get():.3f}",
                    "audio_format": self.format_var.get(),
                    "batch_size": str(variants),
                    "inference_steps": "8",
                    "thinking": "false",
                    "model": "acestep-v15-turbo",
                }
                with open(source, "rb") as f:
                    files = {"src_audio": (source.name, f, mime)}
                    r = requests.post(BASE_URL + "/release_task", data=data, files=files, timeout=300)
                r.raise_for_status()
                payload = r.json()
                if payload.get("code") != 200:
                    raise RuntimeError(payload.get("error") or "Silnik odrzucił zadanie.")
                task_id = payload["data"]["task_id"]
                self.after(0, self.status_var.set, f"Generowanie trwa... zadanie {task_id[:8]}. Pierwsza generacja może potrwać dłużej, bo model jest ładowany do pamięci.")

                deadline = time.time() + 7200
                result_items = None
                while time.time() < deadline:
                    q = requests.post(BASE_URL + "/query_result", json={"task_id_list": [task_id]}, timeout=60)
                    q.raise_for_status()
                    qp = q.json()
                    if qp.get("code") != 200:
                        raise RuntimeError(qp.get("error") or "Błąd sprawdzania zadania.")
                    jobs = qp.get("data") or []
                    if jobs:
                        job = jobs[0]
                        status = int(job.get("status", 0))
                        if status == 1:
                            raw = job.get("result") or "[]"
                            result_items = json.loads(raw) if isinstance(raw, str) else raw
                            break
                        if status == 2:
                            raise RuntimeError(job.get("error") or "Generowanie zakończyło się błędem.")
                    time.sleep(3)
                if result_items is None:
                    raise RuntimeError("Przekroczono maksymalny czas oczekiwania na generowanie.")

                generated = []
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                for idx, item in enumerate(result_items, start=1):
                    file_ref = item.get("file")
                    if not file_ref:
                        continue
                    download_url = file_ref if file_ref.startswith("http") else urljoin(BASE_URL + "/", file_ref.lstrip("/"))
                    audio = requests.get(download_url, timeout=300)
                    audio.raise_for_status()
                    ext = self.format_var.get().lower()
                    out = OUTPUT_DIR / f"MARBO_AI_Cover_{stamp}_{idx}.{ext}"
                    with open(out, "wb") as f:
                        f.write(audio.content)
                    generated.append(out)

                if not generated:
                    raise RuntimeError("Silnik zgłosił sukces, ale nie zwrócił pliku audio.")

                self.output_files.extend(generated)
                self.after(0, self.refresh_output_list)
                self.after(0, self.status_var.set, f"Gotowe. Wygenerowano {len(generated)} plik(i).")
                self.after(0, messagebox.showinfo, "Gotowe", f"Wygenerowano {len(generated)} wersję/wersje.\n\nPliki zapisano w:\n{OUTPUT_DIR}")
            except Exception as exc:
                self.after(0, messagebox.showerror, "Błąd generowania", str(exc))
                self.after(0, self.status_var.set, f"Błąd generowania: {exc}")
            finally:
                self.after(0, self.set_busy, False)
        self.thread(work)

    def refresh_output_list(self):
        self.outputs.delete(0, "end")
        for p in self.output_files:
            self.outputs.insert("end", str(p))
        if self.output_files:
            self.outputs.selection_set(len(self.output_files) - 1)

    def selected_output(self):
        sel = self.outputs.curselection()
        if not sel:
            return None
        return Path(self.outputs.get(sel[0]))

    def play_selected(self):
        p = self.selected_output()
        if not p or not p.exists():
            messagebox.showinfo("Odtwarzanie", "Najpierw wybierz wygenerowany plik.")
            return
        try:
            if os.name == "nt":
                os.startfile(str(p))
            else:
                subprocess.Popen(["xdg-open", str(p)])
        except Exception as exc:
            messagebox.showerror("Błąd", str(exc))

    def open_output_folder(self):
        safe_mkdirs()
        try:
            if os.name == "nt":
                os.startfile(str(OUTPUT_DIR))
            else:
                subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])
        except Exception as exc:
            messagebox.showerror("Błąd", str(exc))

    def on_close(self):
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
