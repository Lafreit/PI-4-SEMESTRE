# notificacao/views.py
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from .models import Notificacao
from django.views.decorators.http import require_POST, require_GET



@login_required
def lista_notificacoes(request):
    # mostra todas notificações do usuário (paginável se desejar)
    notificacoes = Notificacao.objects.filter(usuario=request.user).order_by('-criada_em')[:100]
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
