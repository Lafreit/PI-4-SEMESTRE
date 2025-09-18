from django.shortcuts import render,redirect 

# Create your views here.
def cadastrar_veiculo(request):
    """
    View para exibir e processar o formulário de cadastro de veículos.
    """
    if request.method == 'POST':
        marca = request.POST.get('marca')
        modelo = request.POST.get('modelo')
        ano = request.POST.get('ano')
        placa = request.POST.get('placa')
        
    
        

        print(f"Dados recebidos do formulário de veículo:")
        print(f"Marca: {marca}")
        print(f"Modelo: {modelo}")
        print(f"Ano: {ano}")
        print(f"Placa: {placa}")
        
        return redirect('paginainicial')
        
    return render(request, 'cadastraveiculo.html')
