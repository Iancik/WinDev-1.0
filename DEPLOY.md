# WinDev — publicare online

WinDev convertește proiecte **Winsmeta** (folder `.KOS`) în Excel **Deviz360**.

## Variante de rulare

### 1. PHP (recomandat pe serverul dvs.)

1. Copiați **întregul proiect** WinDev pe server (nu doar `public/`).
2. Setați document root-ul site-ului către folderul `public/`.
3. Editați `public/config.php`:
   - `$PYTHON` — calea către Python 3 (ex: `/usr/bin/python3`)
   - `$WINDEV_ROOT` — rădăcina proiectului (implicit corect)
4. Instalați dependențele Python pe server:
   ```bash
   pip install -r requirements.txt
   ```
5. Verificați că PHP poate executa Python (`exec` activ, permisiuni OK).

**URL:** `https://domeniul-dvs.ro/` → interfață modernă WinDev.

### 2. Flask (Python direct)

```bash
pip install -r requirements.txt
python web/app.py
```

Deschideți `http://localhost:8080` sau folosiți **gunicorn** + nginx în producție:

```bash
gunicorn -w 2 -b 127.0.0.1:8080 "web.app:create_app()"
```

## Utilizare

1. Comprimați folderul `WINSMETA.KOS` într-un fișier `.zip`.
2. Încărcați ZIP-ul în interfața WinDev.
3. Descărcați fișierul `.xlsx` și importați în Deviz360.

## Cerințe server

- PHP 7.4+ (cu `ZipArchive`, `exec`)
- Python 3.9+
- Pachete: `pypxlib`, `openpyxl`, `flask` (doar pentru varianta Flask)

## Desktop (local)

- `Porneste_Convertor.bat` — aplicație desktop
- `Porneste_WinDev_Web.bat` — server web local Flask
