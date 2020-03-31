import csv
import os
import shutil
import stat
import time
import requests
from radon.raw import analyze
from pygit2 import clone_repository

headers = {"Authorization": "Bearer 9a1175f6b32c38aa63ce9ff65d07b8c9d026e775 "}


def run_query(json, headers):  # Função que executa uma request pela api graphql
    request = requests.post('https://api.github.com/graphql', json=json, headers=headers)
    while (request.status_code == 502):
        time.sleep(2)
        request = requests.post('https://api.github.com/graphql', json=json, headers=headers)
    if request.status_code == 200:
        return request.json()  # json que retorna da requisição
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))


def on_rm_error(func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)


def clean_repository(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if not ".git" in filename:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path, onerror=on_rm_error)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def where_stop():
    row = 0
    if os.path.exists("final.csv"):
        fileFinal = open("final.csv", 'r')
        row = sum(1 for line in csv.reader(fileFinal))
        fileFinal.close()
    return row


if not os.path.exists("base.csv"):
    print("Iniciando processo")

    # Query do GraphQL que procura os primeiros 1000 repositorios com mais de 100 estrelas.
    query = """
    query example{
      search (query:"stars:>100 and language:Python", type: REPOSITORY, first:20{AFTER}) {
          pageInfo{
           hasNextPage
            endCursor
          }
          nodes {
            ... on Repository {
              nameWithOwner
                  owner {
                    login
                    }
                  url
                  stargazers {
                    totalCount
                    }
                  watchers {
                    totalCount
                    }
                  forks {
                    totalCount
                    }
                  releases {
                    totalCount
                    }
                  createdAt
                  primaryLanguage {
                    name
                  }
                }
            }
        }
    }
    """

    finalQuery = query.replace("{AFTER}", "")

    json = {
        "query": finalQuery, "variables": {}
    }

    total_pages = 1
    print("Executando Query\n[", end='')
    result = run_query(json, headers)  # Executar a Query
    nodes = result["data"]["search"]["nodes"]  # separar a string para exibir apenas os nodes
    next_page = result["data"]["search"]["pageInfo"]["hasNextPage"]

    page = 0
    while next_page and total_pages < 50:
        total_pages += 1
        cursor = result["data"]["search"]["pageInfo"]["endCursor"]
        next_query = query.replace("{AFTER}", ", after: \"%s\"" % cursor)
        json["query"] = next_query
        result = run_query(json, headers)
        nodes += result['data']['search']['nodes']
        next_page = result["data"]["search"]["pageInfo"]["hasNextPage"]
        print(".", end='')
    print("]")

    print("Criando arquivo CSV")
    file = open("base.csv", 'w', newline='')
    repository = csv.writer(file)

    print("Salvando Repositorios:\n[", end='')
    num = 0
    for node in nodes:
        # Adicionando dados de cada repositorio
        repository.writerow((node['nameWithOwner'], node['owner']['login'], str(node['url']),
                             str(node['stargazers']['totalCount']), str(node['watchers']['totalCount']),
                             str(node['forks']['totalCount']), str(node['releases']['totalCount']),
                             node['createdAt'], node['primaryLanguage']['name']))
        num = num + 1
        if (num % 10) == 0:
            print(".", end='')
    print("]\nProcesso concluido")
    file.close()

print("\n ------ Começo leitura repositorios ------ \n")

numRepo = 0

fileBase = open("base.csv", 'r')
base = csv.reader(fileBase)

lastLine = where_stop()

fileFinal = open("final.csv", 'w', newline='')
final = csv.writer(fileFinal)

if lastLine == 0:
    final.writerow(('nameWithOwner', 'owner/login', 'url', 'stargazers/totalCount', 'watchers/totalCount',
                    'forks/totalCount', 'releases/totalCount', 'createdAt', 'primaryLanguage/name', "totalLOC"))

for node in base:
    if numRepo - 1 >= lastLine:
        repo_path = 'Repository/' + str(numRepo)
        if os.path.exists(repo_path):
            clean_repository(repo_path)
            print("\n" + "Limpeza da pasta do Repositório: ")
        print("repo_path = " + repo_path)
        numRepo = numRepo + 1
        time.sleep(1)
        totalLoc = 0
        gitURL = node[2] + ".git"
        print("\n" + "Começa o git clone")
        print(gitURL)
        repo = clone_repository(gitURL, repo_path)
        print("Termina o git clone \n")
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.py'):
                    fullpath = os.path.join(root, file)
                    with open(fullpath, encoding="utf8") as f:
                        content = f.read()
                        print("\nLendo arquivo " + fullpath)
                        b = analyze(content)
                        print(b)
                        i = 0
                        for item in b:
                            if i == 0:
                                totalLoc += item
                                print("loc = " + str(item))
                                print("Total loc até agora: " + str(totalLoc))
                                i += 1
        print("\nTotal loc final para o repo " + node['nameWithOwner'] + " é " + str(totalLoc))
        print("\n ------ Fim de um repositorio ------ \n")
        clean_repository(repo_path)
        final.writerow(node, totalLoc)
    else:
        numRepo = numRepo + 1

print("Total repositórios " + str(numRepo))
fileBase.close()
fileFinal.close()
print("\n ------------- Fim da execução ------------- \n")
