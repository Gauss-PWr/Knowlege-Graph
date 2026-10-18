# Setup Markera dla `pdf_preprocessing.py`

Skrypt `local_LLMs/pdf_preprocessing.py` konwertuje PDF-y z folderu `papers/` do Markdowna (z wzorami jako LaTeX) w folderze `papers_md/`, używając [Markera](https://github.com/datalab-to/marker) 2.x.

Marker działa w dwóch procesach: Twój skrypt w Pythonie oraz **serwer z modelem VLM** (OCR, wzory, układ strony), który Marker uruchamia sam. Serwer ma dwa backendy i od Twojej karty zależy, który wybierzesz:

| Karta | Backend (`backend=`) | Wymagania |
|---|---|---|
| NVIDIA | `"vllm"` | Docker + sterownik NVIDIA |
| AMD, Intel, Apple Silicon, brak GPU | `"llamacpp"` | binarka `llama-server` z llama.cpp |

---

## 1. Instalacja wspólna

**1.1. Zainstaluj** Pythona 3.10+ (na Windowsie zaznacz *„Add python.exe to PATH”*), Git i VS Code z rozszerzeniem Python.

**1.2. Sklonuj repo i utwórz venv** w katalogu głównym repo. Venv tworzy się osobno na każdym komputerze, nie kopiuje się go.

Windows (PowerShell):
```powershell
git clone <URL_REPO> Cool-ML-stuff
cd Cool-ML-stuff
python -m venv .venv
.venv\Scripts\activate
```
> Błąd uruchamiania skryptów? Raz: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Linux / macOS:
```bash
git clone <URL_REPO> Cool-ML-stuff
cd Cool-ML-stuff
python3 -m venv .venv
source .venv/bin/activate
```

**1.3. Zainstaluj Markera** (w aktywnym venvie, przed promptem widać `(.venv)`):
```bash
python -m pip install --upgrade pip
python -m pip install marker-pdf
```

**1.4. Ustaw interpreter w VS Code.** Otwórz **cały folder repo** → `Ctrl+Shift+P` → **Python: Select Interpreter** → wybierz `.venv` (albo *Enter interpreter path* → `.venv\Scripts\python.exe` / `.venv/bin/python`) → otwórz nowy terminal.

---

## 2. Backend: setup per platforma

### NVIDIA, Windows

1. Sterownik z [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx). Test: `nvidia-smi`.
2. PowerShell jako administrator: `wsl --install`, potem restart komputera.
3. Zainstaluj [Docker Desktop](https://www.docker.com/products/docker-desktop/). W *Settings → General* zaznacz **Use the WSL 2 based engine**.
4. Test (Docker Desktop uruchomiony):
   ```powershell
   docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
   ```

W kodzie: `backend="vllm"`. **Docker Desktop musi być włączony przy każdej konwersji.**

### NVIDIA, Linux

1. Sterownik NVIDIA (`nvidia-smi` działa).
2. [Docker Engine](https://docs.docker.com/engine/install/) + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
3. Dostęp bez `sudo`: `sudo usermod -aG docker $USER`, potem wyloguj się i zaloguj.
4. Test: `docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi`

W kodzie: `backend="vllm"`.

### AMD / Intel, Windows

1. Aktualne sterowniki (AMD Adrenalin / Intel Graphics). Dostarczają obsługę Vulkana.
2. Z [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) pobierz `llama-bXXXX-bin-win-vulkan-x64.zip` (w nazwie **`win`** i **`vulkan`**).
3. Rozpakuj do stałego miejsca. `llama-server.exe` musi leżeć **razem z plikami `.dll`** (zip czasem tworzy dodatkowy podfolder).
4. Test: `<ścieżka>\llama-server.exe --version`. Powinna się pojawić nazwa Twojej karty jako urządzenie Vulkan.
5. Skopiuj ścieżkę do pliku (prawy przycisk → *Kopiuj jako ścieżkę*).

W kodzie: `backend="llamacpp"`, `llama_cpp_binary=r"<ścieżka>\llama-server.exe"`.

### AMD / Intel, Linux

1. Sterowniki Mesa z Vulkanem (test: `vulkaninfo --summary` z pakietu `vulkan-tools`).
2. Pobierz linuksowy build llama.cpp z Vulkanem z [releases](https://github.com/ggml-org/llama.cpp/releases) albo zbuduj ze źródeł z `-DGGML_VULKAN=ON`.
3. Test: `<ścieżka>/llama-server --version`.

W kodzie: `backend="llamacpp"`, `llama_cpp_binary="<ścieżka>/llama-server"`.

### macOS (Apple Silicon)

```bash
brew install llama.cpp
llama-server --version
```

W kodzie: `backend="llamacpp"`. `llama_cpp_binary` niepotrzebne, binarka jest w PATH.

### Bez GPU

Jak w wariancie AMD/Intel, ale pobierz build **`cpu`** llama.cpp. Działa, ale cała książka w trybie `balanced` będzie się liczyć bardzo długo.

---

## 3. Konfiguracja w kodzie

### 3.1. Jak działa `PdfToMarkdownConverter`

Przy tworzeniu obiektu klasa kolejno:

1. zapisuje ścieżki i opcje plików,
2. **ustawia zmienne środowiskowe** (`_set_env`),
3. **dopiero wtedy importuje Markera**, bo Marker czyta zmienne w momencie importu, więc ustawione później nie zadziałałyby,
4. buduje słownik `config`,
5. ładuje modele (`create_model_dict`) i tworzy `PdfConverter` **raz** dla wszystkich plików.

Kroki 3 i 5 trwają, więc start skryptu jest wolny. Serwer VLM startuje dopiero przy pierwszej konwertowanej stronie.

### 3.2. Argumenty

**Pliki**

| Argument | Domyślnie | Opis |
|---|---|---|
| `input_dir` | `<repo>/papers` | Folder z PDF-ami |
| `output_dir` | `<repo>/papers_md` | Folder na wyniki (tworzony automatycznie) |
| `pattern` | `"*.pdf"` | Które pliki brać |
| `search_subfolders` | `False` | `True` = szukaj też w podfolderach; struktura jest odtwarzana w `output_dir` |
| `overwrite_mds` | `False` | `True` = konwertuj ponownie pliki, które mają już `.md` |

`<repo>` to `Path(__file__).resolve().parents[1]`, czyli folder liczony od położenia skryptu. Domyślne ścieżki działają więc na każdym komputerze, niezależnie od katalogu, z którego uruchomisz skrypt.

**Konwersja** (trafia do słownika `config` Markera)

| Argument | Domyślnie | Opis |
|---|---|---|
| `mode` | `"balanced"` | `"balanced"` = najlepsze wzory (LaTeX), wolniej. `"fast"` = szybciej, słabsze wzory. Ustawiony jawnie, bo bez niego Marker poza NVIDIA sam wybrałby `fast` |
| `disable_image_extraction` | `True` | `False` = obrazki zapisywane obok pliku `.md` |
| `page_range` | `None` | Lista stron **liczonych od 0**, stosowana do każdego pliku, np. `list(range(100, 120))`. Do testów |
| `add_config` | `None` | Dodatkowe opcje Markera, np. `{"paginate_output": True}`. Pełna lista: `marker_single --help` |

**Serwer i zasoby** (trafiają do zmiennych środowiskowych)

| Argument | Domyślnie | Zmienna | Opis |
|---|---|---|---|
| `backend` | `"llamacpp"` | `SURYA_INFERENCE_BACKEND` | `"vllm"` dla NVIDIA, `"llamacpp"` dla reszty |
| `llama_cpp_binary` | `None` | `LLAMA_CPP_BINARY` | Pełna ścieżka do `llama-server`, gdy nie ma go w PATH |
| `parallel` | `4` | `SURYA_INFERENCE_PARALLEL` | Liczba równoległych zapytań do serwera. Więcej = szybciej, ale więcej pamięci. `None` = automatycznie |
| `keep_alive` | `True` | `SURYA_INFERENCE_KEEP_ALIVE` | Serwer działa dalej po zakończeniu skryptu (szybszy kolejny start, ale **trzyma RAM/VRAM**, patrz [sekcja 4](#4-uruchamianie)) |
| `hf_home` | `None` | `HF_HOME` | Gdzie trzymać pobrane modele (np. inny dysk) |
| (zawsze) | | `HF_HUB_DISABLE_SYMLINKS_WARNING=1` | Wycisza niegroźne ostrzeżenie na Windowsie |

Na Windowsie podawaj ścieżki jako `r"..."`. Bez `r` np. `\t` w ścieżce zamieni się w tabulator.

### 3.3. Metody

| Metoda | Opis |
|---|---|
| `find_pdfs()` | Lista PDF-ów z `input_dir` pasujących do `pattern` |
| `output_path(pdf)` | Ścieżka wyniku: `papers/sub/book.pdf` → `papers_md/sub/book.md` |
| `convert_file(pdf)` | Konwertuje jeden plik, zapisuje `.md` i zwraca statystyki: `file`, `pages`, `seconds`, `sec_per_page` |
| `convert_all()` | Konwertuje wszystkie pliki, pomija gotowe, nie przerywa całości przy błędzie jednego pliku, wypisuje podsumowanie |

### 3.4. Przykłady

```python
# Windows + AMD/Intel
PdfToMarkdownConverter(
    llama_cpp_binary=r"C:\Users\<TY>\Desktop\llama.cpp\llama-server.exe",
).convert_all()

# NVIDIA (Windows/Linux)
PdfToMarkdownConverter(backend="vllm", parallel=None).convert_all()

# macOS
PdfToMarkdownConverter().convert_all()

# test kilku stron przed całą książką
conv = PdfToMarkdownConverter(page_range=list(range(100, 106)), overwrite_mds=True)
print(conv.convert_file(conv.input_dir / "convex_opt_book.pdf"))
```

---

## 4. Uruchamianie

```bash
python local_LLMs/pdf_preprocessing.py
```

**Pierwsze uruchomienie** pobiera wagi modelu Surya (ok. 1,5 GB) do cache Hugging Face, a na NVIDIA także obraz Dockera z vLLM. Dzieje się to tylko raz. Ostrzeżenia o `HF_TOKEN` są niegroźne.

**Zalecana kolejność:** najpierw `page_range` na kilku stronach z gęstą matematyką. Sprawdź jakość wzorów i `sec_per_page`, a dopiero potem puść całą bibliotekę.

**Zwalnianie pamięci po pracy.** Przy `keep_alive=True` serwer zostaje w tle i trzyma model w pamięci. Kiedy skończysz pracę, zatrzymaj go:

| Backend | Komenda |
|---|---|
| `llamacpp`, Windows | `taskkill /IM llama-server.exe /F` |
| `llamacpp`, Linux/macOS | `pkill llama-server` |
| `vllm` | `docker ps`, potem `docker stop <ID>` |

Zmiana `parallel` lub `backend` zadziała dopiero po takim zatrzymaniu, bo inaczej skrypt połączy się ze starym serwerem.

---

## 5. Najczęstsze problemy

| Błąd / objaw | Rozwiązanie |
|---|---|
| `No module named 'marker'` | Skrypt uruchomiony innym Pythonem. Sprawdź `python -c "import sys; print(sys.executable)"` i wybierz `.venv` (krok 1.4) |
| `failed to connect to the docker API` | NVIDIA: włącz Docker Desktop. Inna karta: `backend="llamacpp"` |
| `llama-server binary not found` | Podaj `llama_cpp_binary` z pełną ścieżką do pliku |
| Dodałem `llama-server` do PATH, a nie działa | Zamknij całe VS Code i otwórz ponownie (PATH jest wczytywany przy starcie) |
| Wzory wyglądają jak `6=`, `Xm i=1` | Użyj `mode="balanced"` z działającym backendem |
| Bardzo wolno | Sprawdź w Menedżerze zadań / `nvidia-smi`, czy pracuje karta. AMD/Intel: build `vulkan` i aktualne sterowniki |
| RAM / VRAM zajęte po pracy | Serwer działa w tle (`keep_alive`). Zatrzymaj go (sekcja 4) |
| Brak pamięci w trakcie | Zmniejsz `parallel` (np. do `2`) |
