# MapaEquip - versão sem Make

Aplicativo web responsivo em Python/Flask com CRUD direto no Python usando SQLite.

## Funções
- CREATE: cadastrar equipamento
- READ: listar equipamentos
- UPDATE: editar equipamento
- DELETE: excluir equipamento

## Rodar localmente

```powershell
cd mapaequip-python-sem-make
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Acesse:

```text
http://127.0.0.1:5000
```

## Render

Build Command:

```text
pip install -r requirements.txt
```

Start Command:

```text
gunicorn app:app
```

Variável de ambiente recomendada:

```text
FLASK_SECRET_KEY=MapaEquip_2026_Projeto_CRUD
```
