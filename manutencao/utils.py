# manutencao/utils.py
import requests

def enviar_notificacao_ntfy(chamado, host):
    try:
        topico = "manutencao_lynd_notificacao"
        
        # 1. Garantimos que maquina seja sempre string, mesmo se der erro no banco
        maquina = str(chamado.equipamento.nome) if chamado.equipamento else "Avulso/Setor"
        
        # 2. Simplificamos os headers ao máximo (evitando acentos aqui)
        headers = {
            "Title": "NOVO CHAMADO", # Sem acento para evitar erro de header
            "Priority": "4",
            "Tags": "wrench,warning"
        }

        # 3. Adicionamos o link APENAS se o host existir
        if host:
            headers["Click"] = f"http://{host}/admin-manutencao"  # Link para o detalhe do chamado

        # 4. Montamos o corpo de forma segura (usando f-string limpa)
        corpo = f"Maquina: {maquina}\nSolicitante: {chamado.solicitante}"

        # 5. O Post
        response = requests.post(
            f"https://ntfy.sh/{topico}",
            data=corpo.encode('utf-8'),
            headers=headers,
            timeout=10
        )
        
        return response.status_code == 200

    except Exception as e:
        print(f"Erro na notificacao: {e}")
        return False
    


# Nova função para notificar o mecânico designado
def notificar_mecanico_designado(chamado, mecanico, host):
    try:
        # 1. Limpa o username para garantir que a URL seja válida (remove espaços e acentos)
        # Ou melhor ainda: use o ID do usuário para ser impossível errar
        topico_limpo = f"manutencao_lynd_mecanico_{mecanico.id}"
        
        maquina = str(chamado.equipamento.nome) if chamado.equipamento else "Avulso/Setor"
        
        headers = {
            "Title": "TRABALHO DESIGNADO",
            "Priority": "5", # Urgente
            "Tags": "hammer_and_wrench",
            "Click": f"http://{host}/chamado/{chamado.id}/status"
        }

        # 2. Faz o POST
        response = requests.post(
            f"https://ntfy.sh/{topico_limpo}",
            data=f"Voce foi escalado para a maquina: {maquina}".encode('utf-8'),
            headers=headers,
            timeout=10
        )
        
        print(f"DEBUG: Enviado para {topico_limpo} | Status: {response.status_code}")
        return True

    except Exception as e:
        print(f"DEBUG: Erro ao notificar: {e}")
        return False