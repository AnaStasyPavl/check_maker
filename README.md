# Invoice PDF Generator

Интерактивный генератор PDF-счётов из CSV и JSON.

```powershell
python main.py
```

После запуска выберите файл данных, HTML-шаблон и `invoice id`. Готовый PDF сохраняется в `output/` и открывается системной программой.

Пакетный запуск остаётся доступным:

```powershell
python main.py validate --input data\data2.json
python main.py generate --input data\data2.json --template templates\invoice.html --output-dir output --format pdf
```

Установите зависимости:

```powershell
python -m pip install -r requirements.txt
```

На Windows для WeasyPrint нужны системные библиотеки Pango/GLib. Проще всего установить официальный пакет GTK for Windows и перезапустить терминал. На macOS установите Pango через Homebrew:

```bash
brew install pango
pip3 install -r requirements.txt
python3 main.py
```
