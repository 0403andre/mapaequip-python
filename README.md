# MapaEquip - Python Flask

Aplicativo web responsivo para cadastrar, listar, editar e excluir equipamentos usando Python/Flask + Make + Google Sheets.

## Como executar no Windows PowerShell

```powershell
cd mapaequip-python
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
python app.py
```

Acesse:

```text
http://127.0.0.1:5000
```

Preencha o `.env` com as URLs reais dos Webhooks do Make.
