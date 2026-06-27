import json
import os
import uuid
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "mapaequip-dev-key")

MAKE_CREATE_URL = os.getenv("MAKE_CREATE_URL", "").strip()
MAKE_READ_URL = os.getenv("MAKE_READ_URL", "").strip()
MAKE_UPDATE_URL = os.getenv("MAKE_UPDATE_URL", "").strip()
MAKE_DELETE_URL = os.getenv("MAKE_DELETE_URL", "").strip()


def gerar_id():
    return f"EQP-{uuid.uuid4().hex[:6].upper()}"


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def validar_url(nome, url):
    if not url or "SEU_WEBHOOK" in url:
        raise RuntimeError(f"A variável {nome} não está configurada no arquivo .env.")


def chamar_make(url, payload=None, method="POST"):
    try:
        if method.upper() == "GET":
            r = requests.get(url, timeout=20)
        else:
            r = requests.post(url, json=payload or {}, timeout=20)

        r.raise_for_status()
        text = r.text.strip()

        if not text:
            return {"success": True, "message": "Resposta vazia recebida do Make."}

        try:
            data = r.json()
        except ValueError:
            try:
                data = json.loads(text)
            except ValueError:
                return {"success": True, "message": text, "raw": text}

        if isinstance(data, dict) and isinstance(data.get("data"), str):
            try:
                return json.loads(data["data"])
            except ValueError:
                return data

        return data

    except requests.RequestException as exc:
        return {"success": False, "message": f"Erro ao chamar o Make: {exc}"}


def extrair_equipamentos(resposta):
    if not isinstance(resposta, dict):
        return []

    equipamentos = resposta.get("equipamentos")

    if equipamentos is None and isinstance(resposta.get("data"), dict):
        equipamentos = resposta["data"].get("equipamentos")

    if isinstance(equipamentos, str):
        try:
            equipamentos = json.loads(equipamentos)
        except ValueError:
            equipamentos = []

    if isinstance(equipamentos, dict):
        equipamentos = [equipamentos]

    if not isinstance(equipamentos, list):
        return []

    normalizados = []
    for item in equipamentos:
        if not isinstance(item, dict):
            continue

        def pegar(item, *nomes):
            for nome in nomes:
                valor = item.get(nome)
                if valor not in (None, ""):
                    return valor
            return ""

        normalizados.append({
            "id": pegar(item, "id", "id (A)", "0"),
            "nome_equipamento": pegar(item, "nome_equipamento", "nome_equipamento (B)", "1"),
            "tipo_equipamento": pegar(item, "tipo_equipamento", "tipo_equipamento (C)", "2"),
            "patrimonio": pegar(item, "patrimonio", "patrimonio (D)", "3"),
            "numero_serie": pegar(item, "numero_serie", "numero_serie (E)", "4"),
            "hostname": pegar(item, "hostname", "hostname (F)", "5"),
            "ip": pegar(item, "ip", "ip (G)", "6"),
            "setor": pegar(item, "setor", "setor (H)", "7"),
            "localizacao": pegar(item, "localizacao", "localizacao (I)", "8"),
            "responsavel": pegar(item, "responsavel", "responsavel (J)", "9"),
            "status": pegar(item, "status", "status (K)", "10"),
            "observacoes": pegar(item, "observacoes", "observacoes (L)", "11"),
            "data_cadastro": pegar(item, "data_cadastro", "data_cadastro (M)", "12"),
            "data_atualizacao": pegar(item, "data_atualizacao", "data_atualizacao (N)", "13"),
        })

    return normalizados


def buscar_equipamentos():
    validar_url("MAKE_READ_URL", MAKE_READ_URL)
    # Se o cenário READ do Make estiver configurado como POST, troque GET para POST.
    resposta = chamar_make(MAKE_READ_URL, method="GET")
    return extrair_equipamentos(resposta)


def buscar_por_id(equipamento_id):
    for equipamento in buscar_equipamentos():
        if equipamento.get("id") == equipamento_id:
            return equipamento
    return None


def payload_formulario(form):
    return {
        "id": form.get("id") or gerar_id(),
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


@app.route("/")
def home():
    try:
        equipamentos = buscar_equipamentos()
    except RuntimeError:
        equipamentos = []

    total = len(equipamentos)
    em_uso = sum(1 for e in equipamentos if e.get("status") == "Em uso")
    manutencao = sum(1 for e in equipamentos if e.get("status") == "Manutenção")
    disponiveis = sum(1 for e in equipamentos if e.get("status") == "Disponível")

    return render_template(
        "home.html",
        total=total,
        em_uso=em_uso,
        manutencao=manutencao,
        disponiveis=disponiveis,
        active="home",
    )


@app.route("/equipamentos")
def listagem():
    termo = request.args.get("q", "").strip().lower()
    tipo = request.args.get("tipo", "").strip()
    status = request.args.get("status", "").strip()

    try:
        equipamentos = buscar_equipamentos()
    except RuntimeError as exc:
        flash(str(exc), "error")
        equipamentos = []

    if termo:
        equipamentos = [
            e for e in equipamentos
            if termo in " ".join([
                e.get("nome_equipamento", ""),
                e.get("hostname", ""),
                e.get("ip", ""),
                e.get("patrimonio", ""),
                e.get("setor", ""),
            ]).lower()
        ]

    if tipo:
        equipamentos = [e for e in equipamentos if e.get("tipo_equipamento") == tipo]

    if status:
        equipamentos = [e for e in equipamentos if e.get("status") == status]

    return render_template(
        "listagem.html",
        equipamentos=equipamentos,
        termo=termo,
        tipo=tipo,
        status=status,
        active="equipamentos",
    )


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        try:
            validar_url("MAKE_CREATE_URL", MAKE_CREATE_URL)
            payload = payload_formulario(request.form)
            payload["acao"] = "create"
            payload["data_cadastro"] = agora()
            resposta = chamar_make(MAKE_CREATE_URL, payload, method="POST")

            if resposta.get("success", True):
                flash("Equipamento cadastrado com sucesso.", "success")
                return redirect(url_for("listagem"))

            flash(resposta.get("message", "Erro ao cadastrar equipamento."), "error")
        except RuntimeError as exc:
            flash(str(exc), "error")

    return render_template("cadastro.html", active="cadastro")


@app.route("/edicao/<equipamento_id>", methods=["GET", "POST"])
def edicao(equipamento_id):
    try:
        equipamento = buscar_por_id(equipamento_id)
    except RuntimeError as exc:
        flash(str(exc), "error")
        return redirect(url_for("listagem"))

    if not equipamento:
        flash("Equipamento não encontrado.", "error")
        return redirect(url_for("listagem"))

    if request.method == "POST":
        try:
            validar_url("MAKE_UPDATE_URL", MAKE_UPDATE_URL)
            payload = payload_formulario(request.form)
            payload["acao"] = "update"
            resposta = chamar_make(MAKE_UPDATE_URL, payload, method="POST")

            if resposta.get("success", True):
                flash("Equipamento atualizado com sucesso.", "success")
                return redirect(url_for("listagem"))

            flash(resposta.get("message", "Erro ao atualizar equipamento."), "error")
        except RuntimeError as exc:
            flash(str(exc), "error")

    return render_template("edicao.html", equipamento=equipamento, active="equipamentos")


@app.route("/exclusao/<equipamento_id>", methods=["GET", "POST"])
def exclusao(equipamento_id):
    try:
        equipamento = buscar_por_id(equipamento_id)
    except RuntimeError as exc:
        flash(str(exc), "error")
        return redirect(url_for("listagem"))

    if not equipamento:
        flash("Equipamento não encontrado.", "error")
        return redirect(url_for("listagem"))

    if request.method == "POST":
        try:
            validar_url("MAKE_DELETE_URL", MAKE_DELETE_URL)
            resposta = chamar_make(
                MAKE_DELETE_URL,
                {
                    "acao": "delete",
                    "id": equipamento_id
                },
                method="POST"
            )

            if resposta.get("success", True):
                flash("Equipamento excluído com sucesso.", "success")
                return redirect(url_for("listagem"))

            flash(resposta.get("message", "Erro ao excluir equipamento."), "error")
        except RuntimeError as exc:
            flash(str(exc), "error")

    return render_template("exclusao.html", equipamento=equipamento, active="equipamentos")


@app.errorhandler(404)
def page_not_found(_):
    return render_template("404.html", active="home"), 404


if __name__ == "__main__":
    app.run(debug=True)
