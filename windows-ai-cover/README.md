# MARBO AI Cover — Windows + Google Colab

Wersja 2.0 przenosi generowanie AI z lokalnego komputera do Google Colab.

## Jak działa

1. Program Windows zapisuje MP3/WAV i plik zadania do `Mój dysk/MARBO AI Cover/Queue`.
2. Google Drive synchronizuje pliki z chmurą.
3. Notebook `MARBO_AI_Cover_Colab.ipynb` działa w Google Colab na GPU i uruchamia ACE-Step 1.5.
4. Notebook pobiera zadania z kolejki, generuje cover i zapisuje wynik do `Mój dysk/MARBO AI Cover/Output`.
5. Program Windows pokazuje status oraz gotowe pliki po synchronizacji.

## Wymagania

- Windows 10/11,
- Google Drive na komputer — lokalny folder `Mój dysk`,
- konto Google,
- Google Colab z aktywnym GPU, gdy jest dostępne,
- utwory, do których użytkownik ma odpowiednie prawa lub zgodę na opracowanie.

## ACE-Step

Notebook korzysta z oficjalnego repozytorium `ACE-Step/ACE-Step-1.5` oraz trybu `task_type=cover`, źródłowego pliku `src_audio`, parametru `audio_cover_strength`, `batch_size` i modelu `acestep-v15-turbo`.

Darmowy Google Colab nie gwarantuje dostępności GPU ani ciągłego działania sesji.
