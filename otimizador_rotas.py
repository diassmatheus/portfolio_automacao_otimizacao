from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from time import sleep
import itertools
import pulp

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

driver.get('https://www.google.com/maps')
driver.maximize_window()
driver.implicitly_wait(2)

dict_enderecos = {"Ponto de partida, marco zero de SP" : "Praça da Sé, s/n - Centro Histórico, São Paulo - SP, 01001-000",
                  "Itaú" : "Praça Alfredo Egydio de Souza Aranha, 100 - Jabaquara, São Paulo - SP, 04344-902",
                  "Bradesco" : "Prédio Prata Cidade de Deus, s/nº, Vila Yara, Osasco - SP, CEP 06029-900",
                  "Santander" : "Avenida Juscelino Kubitschek, 2235, Vila Olímpia, São Paulo - SP, CEP 04543-011",
                  "Nubank" : "Rua Capote Valente, 39. Pinheiros. São Paulo - SP CEP: 05409-000"}
lista_enderecos = list(dict_enderecos.values())
                    

def esta_na_aba_de_rotas():
    botao_fechar_rotas = driver.find_elements(By.XPATH, '//button[@aria-label="Fechar rotas"]')
    return len(botao_fechar_rotas) > 0

def adiciona_destino(endereco, num_caixa_busca=1):
    sleep(0.5)
    if not esta_na_aba_de_rotas():
        caixa_busca = driver.find_element(By.XPATH, value='//input[@id="searchboxinput"]')
        caixa_busca.clear()
        caixa_busca.send_keys(endereco)
        caixa_busca.send_keys(Keys.RETURN)
    else:
        caixas_busca = driver.find_elements(By.XPATH, value='//div[contains(@id, "directions-searchbox")]//input')
        caixas_busca = [caixa for caixa in caixas_busca if caixa.is_displayed()]
        if len(caixas_busca) >= num_caixa_busca:
            caixa_endereco = caixas_busca[num_caixa_busca-1]
            caixa_endereco.send_keys(Keys.CONTROL + 'a')
            caixa_endereco.send_keys(Keys.DELETE)
            caixa_endereco.send_keys(endereco)
            caixa_endereco.send_keys(Keys.RETURN)
        else:
            print('Não foi possível adicionar o endereço')

def abre_rotas():
    wait = WebDriverWait(driver, timeout=7)
    botao_rotas = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Rotas"]')))
    botao_rotas.click()
    wait = WebDriverWait(driver, timeout=5)
    elemento_de_espera_botao_fechar_rotas = wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Fechar rotas"]')))

def adiciona_caixa_destino():
    sleep(1)
    wait = WebDriverWait(driver, timeout=5)
    wait.until(EC.visibility_of_element_located((By.XPATH, '//span[text()="Adicionar destino"]')))
    botao_adicionar_destino = driver.find_element(By.XPATH, value='//span[text()="Adicionar destino"]')
    botao_adicionar_destino.click()

def seleciona_tipo_transporte(tipo_transporte='Carro'):
    wait = WebDriverWait(driver, timeout=5)
    botao_transporte = wait.until(EC.presence_of_element_located((By.XPATH, f'//div[@aria-label="{tipo_transporte}"]')))
    botao_transporte.click()

def retorna_tempo_entre_destinos_em_min():
    wait = WebDriverWait(driver, timeout=5)
    elemento_tempo = wait.until(EC.visibility_of_element_located((By.XPATH, '//div[@id="section-directions-trip-0"]//div[contains(text(), "min")]')))
    return int(elemento_tempo.text.replace(' min', ''))

def retorna_distancia_entre_destinos_em_km():
    wait = WebDriverWait(driver, timeout=5)
    elemento_tempo = wait.until(EC.visibility_of_element_located((By.XPATH, '//div[@id="section-directions-trip-0"]//div[contains(text(), "km")]')))
    return float(elemento_tempo.text.replace(' km', '').replace(',','.'))

def gera_pares_distancia(enderecos):
    distancia_pares = {}
    driver.get('https://www.google.com/maps')
    adiciona_destino(endereco=enderecos[0], num_caixa_busca=1)
    sleep(2)
    abre_rotas()
    seleciona_tipo_transporte(tipo_transporte='Carro')
    for i, endereco1 in enumerate(enderecos):
        adiciona_destino(endereco=endereco1, num_caixa_busca=1)
        for j, endereco2 in enumerate(enderecos):
            if i != j:
                adiciona_destino(endereco=endereco2, num_caixa_busca=2)
                distancia_par = retorna_distancia_entre_destinos_em_km()
                distancia_pares[f'{i}-{j}'] = distancia_par
    return distancia_pares

def gera_pares_tempo(enderecos):
    tempo_pares = {}
    driver.get('https://www.google.com/maps')
    adiciona_destino(endereco=enderecos[0], num_caixa_busca=1)
    abre_rotas()
    seleciona_tipo_transporte(tipo_transporte='Motocicleta')
    for i, endereco1 in enumerate(enderecos):
        adiciona_destino(endereco=endereco1, num_caixa_busca=1)
        for j, endereco2 in enumerate(enderecos):
            if i != j:
                adiciona_destino(endereco=endereco2, num_caixa_busca=2)
                tempo_par = retorna_tempo_entre_destinos_em_min()
                tempo_pares[f'{i}-{j}'] = tempo_par
    return tempo_pares

def gera_otimizacao(enderecos, tempo_pares):
    def tempo(endereco1, endereco2):
        return tempo_pares[f'{endereco1}-{endereco2}']
    problema = pulp.LpProblem("TSP", pulp.LpMinimize)
    x = pulp.LpVariable.dicts('x', [(i, j) for i in range(len(enderecos)) for j in range(len(enderecos)) if i != j], cat='Binary')
    problema += pulp.lpSum([tempo(i, j) * x[(i, j)] for i in range(len(enderecos)) for j in range(len(enderecos)) if i != j])
    for i in range(len(enderecos)):
        problema += pulp.lpSum([x[(i, j)] for j in range(len(enderecos)) if i != j]) == 1
        problema += pulp.lpSum([x[(j, i)] for j in range(len(enderecos)) if i != j]) == 1
    for k in range(len(enderecos)):
        for s in range(2, len(enderecos)):
            for subset in itertools.combinations([i for i in range(len(enderecos)) if i != k], s):
                problema += pulp.lpSum([x[(i, j)] for i in subset for j in subset if i != j]) <= len(subset) - 1
    problema.solve(pulp.PULP_CBC_CMD())
    solucao = []
    cidade_inicial = 0
    proxima_cidade = cidade_inicial
    while True:
        for j in range(len(enderecos)):
            if j != proxima_cidade and x[(proxima_cidade, j)].value() == 1:
                solucao.append((proxima_cidade, j))
                proxima_cidade = j
                break
        if proxima_cidade == cidade_inicial:
            break
    print('Rotas:')
    for i in range(len(solucao)):
        print(solucao[i][0], '->>', solucao[i][1])
    return solucao

def mostra_rota_otimizada(enderecos, solucao):
    driver.get('https://www.google.com/maps')
    adiciona_destino(enderecos[0], 1)
    abre_rotas()
    caixa_busca_2 = driver.find_element(By.XPATH, value='//div[@id="directions-searchbox-1"]//input')
    caixa_busca_2.clear()
    for i in range(len(solucao)):
        adiciona_destino(enderecos[solucao[i][0]], i+1)
        if i > 0:
            adiciona_caixa_destino()
    adiciona_destino(enderecos[0], len(enderecos)+1)


if __name__ == '__main__':
    tempo_pares = gera_pares_tempo(lista_enderecos)
    solucao = gera_otimizacao(lista_enderecos, tempo_pares)
    mostra_rota_otimizada(lista_enderecos, solucao)

