# notificacao/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from .models import Notificacao
from django.views.decorators.http import require_POST, require_GET
from corrida.models import Corrida
import json

@login_required
def lista_notificacoes(request):
    # mostra todas notificações do usuário (paginável se desejar)
    notificacoes = list(Notificacao.objects.filter(usuario=request.user).order_by('-criada_em')[:100])

    # Normalizar/Enriquecer cada notificação com informações sobre a corrida (quando aplicável)
    for n in notificacoes:
        # garantir que n.dados seja dict (pode ser string JSON dependendo de como foi salvo)
        dados = n.dados
        if isinstance(dados, str):
            try:
                dados = json.loads(dados)
            except Exception:
                dados = {}
        elif dados is None:
            dados = {}

        # expõe uma versão normalizada para o template (sem underscore)
        n.dados_normalizados = dados

        # detectar corrida_id em keys comuns
        corrida_id = None
        if isinstance(dados, dict) and 'corrida_id' in dados:
            corrida_id = dados.get('corrida_id')
        elif isinstance(dados, dict) and 'corrida' in dados:
            corrida_id = dados.get('corrida')

        n.corrida_id = corrida_id
        n.corrida_exists = False
        n.corrida_status = None

        if corrida_id:
            try:
                corrida = Corrida.objects.get(id=int(corrida_id))
                n.corrida_exists = True
                n.corrida_status = getattr(corrida, 'status', None)
            except (Corrida.DoesNotExist, ValueError, TypeError):
                n.corrida_exists = False
                n.corrida_status = None

    return render(request, "notificacao/lista_notificacoes.html", {"notificacoes": notificacoes})

@login_required
@require_POST
def api_marcar_lida(request):
    # espera JSON: { "id": <notificacao_id> }
    try:
        nid = int(request.POST.get("id") or request.body and __import__('json').loads(request.body).get("id"))
    except Exception:
        return HttpResponseBadRequest("id inválido")

    notific = get_object_or_404(Notificacao, id=nid, usuario=request.user)
    notific.lida = True
    notific.save(update_fields=['lida'])
    return JsonResponse({"ok": True})

@login_required
@require_GET
def api_contagem_nao_lidas(request):
    count = Notificacao.objects.filter(usuario=request.user, lida=False).count()
    return JsonResponse({"unread": count})
