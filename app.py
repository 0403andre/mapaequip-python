import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "MapaEquip_2026_Projeto_CRUD")

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "mapaequip.db"))


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def gerar_id():
    return f"EQP-{uuid.uuid4().hex[:6].upper()}"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS equipamentos (
            id TEXT PRIMARY KEY,
            nome_equipamento TEXT NOT NULL,
            tipo_equipamento TEXT NOT NULL,
            patrimonio TEXT NOT NULL,
            numero_serie TEXT,
            hostname TEXT,
            ip TEXT,
            setor TEXT,
            localizacao TEXT,
            responsavel TEXT,
            status TEXT NOT NULL,
            observacoes TEXT,
            data_cadastro TEXT,
            data_atualizacao TEXT
        )
    """)
    db.commit()

    total = db.execute("SELECT COUNT(*) FROM equipamentos").fetchone()[0]

    if total == 0:
        dados_iniciais = [
            (
                "EQP-0001",
                "Notebook Dell Latitude",
                "Notebook",
                "123456",
                "ABC123XYZ",
                "NTB-FIN-001",
                "10.10.1.88",
                "Financeiro",
                "3º Andar - Sala 301",
                "Mavila Silva Lima",
                "Em uso",
                "Equipamento utilizado pela equipe financeira.",
                agora(),
                agora(),
            ),
            (
                "EQP-0002",
                "LENOVO",
                "Notebook",
                "789456",
                "CEI557",
                "LAPTOP-EF80IMQ5",
                "192.168.1.4",
                "T.I",
                "1º ANDAR",
                "Milena Silva",
                "Manutenção",
                "",
                agora(),
                agora(),
            ),
        ]

        db.executemany("""
            INSERT INTO equipamentos (
                id, nome_equipamento, tipo_equipamento, patrimonio,
                numero_serie, hostname, ip, setor, localizacao, responsavel,
                status, observacoes, data_cadastro, data_atualizacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dados_iniciais)
        db.commit()

    db.close()


def equipamento_from_form(form, equipamento_id=None):
    return {
        "id": equipamento_id or form.get("id") or gerar_id(),
        "nome_equipamento": form.get("nome_equipamento", "").strip(),
        "tipo_equipamento": form.get("tipo_equipamento", "").strip(),
        "patrimonio": form.get("patrimonio", "").strip(),
        "numero_serie": form.get("numero_serie", "").strip(),
        "hostname": form.get("hostname", "").strip(),
        "ip": form.get("ip", "").strip(),
        "setor": form.get("setor", "").strip(),
        "localizacao": form.get("localizacao", "").strip(),
        "responsavel": form.get("responsavel", "").strip(),
        "status": form.get("status", "").strip(),
        "observacoes": form.get("observacoes", "").strip(),
        "data_atualizacao": agora(),
    }


def listar_equipamentos(termo="", tipo="", status=""):
    db = get_db()
    sql = "SELECT * FROM equipamentos WHERE 1=1"
    params = []

    if termo:
        sql += """
            AND (
                lower(nome_equipamento) LIKE ?
                OR lower(hostname) LIKE ?
                OR lower(ip) LIKE ?
                OR lower(patrimonio) LIKE ?
                OR lower(setor) LIKE ?
            )
        """
        busca = f"%{termo.lower()}%"
        params.extend([busca, busca, busca, busca, busca])

    if tipo:
        sql += " AND tipo_equipamento = ?"
        params.append(tipo)

    if status:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY data_atualizacao DESC, nome_equipamento ASC"
    rows = db.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def obter_equipamento(equipamento_id):
    db = get_db()
    row = db.execute("SELECT * FROM equipamentos WHERE id = ?", (equipamento_id,)).fetchone()
    return dict(row) if row else None


@app.route("/")
def home():
    equipamentos = listar_equipamentos()
    total = len(equipamentos)
    em_uso = sum(1 for e in equipamentos if e.get("status") == "Em uso")
    manutencao = sum(1 for e in equipamentos if e.get("status") == "Manutenção")
    disponiveis = sum(1 for e in equipamentos if e.get("status") == "Disponível")
    return render_template("home.html", total=total, em_uso=em_uso, manutencao=manutencao, disponiveis=disponiveis, active="home")


@app.route("/equipamentos")
def listagem():
    termo = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "").strip()
    status = request.args.get("status", "").strip()
    equipamentos = listar_equipamentos(termo=termo, tipo=tipo, status=status)
    return render_template("listagem.html", equipamentos=equipamentos, termo=termo, tipo=tipo, status=status, active="equipamentos")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        payload = equipamento_from_form(request.form)
        payload["data_cadastro"] = agora()
        db = get_db()
        db.execute("""
            INSERT INTO equipamentos (
                id, nome_equipamento, tipo_equipamento, patrimonio,
                numero_serie, hostname, ip, setor, localizacao, responsavel,
                status, observacoes, data_cadastro, data_atualizacao
            )
            VALUES (
                :id, :nome_equipamento, :tipo_equipamento, :patrimonio,
                :numero_serie, :hostname, :ip, :setor, :localizacao, :responsavel,
                :status, :observacoes, :data_cadastro, :data_atualizacao
            )
        """, payload)
        db.commit()
        flash("Equipamento cadastrado com sucesso.", "success")
        return redirect(url_for("listagem"))
    return render_template("cadastro.html", active="cadastro")


@app.route("/edicao/<equipamento_id>", methods=["GET", "POST"])
def edicao(equipamento_id):
    equipamento = obter_equipamento(equipamento_id)
    if not equipamento:
        flash("Equipamento não encontrado.", "error")
        return redirect(url_for("listagem"))

    if request.method == "POST":
        payload = equipamento_from_form(request.form, equipamento_id=equipamento_id)
        db = get_db()
        db.execute("""
            UPDATE equipamentos
            SET nome_equipamento = :nome_equipamento,
                tipo_equipamento = :tipo_equipamento,
                patrimonio = :patrimonio,
                numero_serie = :numero_serie,
                hostname = :hostname,
                ip = :ip,
                setor = :setor,
                localizacao = :localizacao,
                responsavel = :responsavel,
                status = :status,
                observacoes = :observacoes,
                data_atualizacao = :data_atualizacao
            WHERE id = :id
        """, payload)
        db.commit()
        flash("Equipamento atualizado com sucesso.", "success")
        return redirect(url_for("listagem"))

    return render_template("edicao.html", equipamento=equipamento, active="equipamentos")


@app.route("/exclusao/<equipamento_id>", methods=["GET", "POST"])
def exclusao(equipamento_id):
    equipamento = obter_equipamento(equipamento_id)
    if not equipamento:
        flash("Equipamento não encontrado.", "error")
        return redirect(url_for("listagem"))

    if request.method == "POST":
        db = get_db()
        db.execute("DELETE FROM equipamentos WHERE id = ?", (equipamento_id,))
        db.commit()
        flash("Equipamento excluído com sucesso.", "success")
        return redirect(url_for("listagem"))

    return render_template("exclusao.html", equipamento=equipamento, active="equipamentos")


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html", active="home"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
