import csv
import os
import shutil
import stat
import time
import requests
from radon.raw import analyze
from pygit2 import clone_repository
import threading

global totalLoc

TIME_LIMIT_TO_FIND_LOC = 900 #seconds
TIMESLEEP = 60 #seconds

headers = {"Authorization": "Bearer YOUR KEY HERER"}

# Run an api graphql request
def run_query(json, headers):  
    request = requests.post('https://api.github.com/graphql', json=json, headers=headers)
    while (request.status_code == 502):
        time.sleep(2)
        request = requests.post('https://api.github.com/graphql', json=json, headers=headers)
    if request.status_code == 200:
        return request.json()  # json returned by request
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

#handle error in function clean_repository(folder) 
def on_rm_error(func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)

#clean local repository folder 
def clean_repository(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if not ".git" in filename: #to avoid error
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path, onerror=on_rm_error)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

#How many rows are already written in final.csv
def where_stop():
    row = 0
    if os.path.exists("final.csv"):
        fileFinal = open("final.csv", 'r')
        row = sum(1 for line in csv.reader(fileFinal))
        fileFinal.close()
    return row

#Insert row in final.csv
def writeInFinalFile(node, totalLoc):
    fileFinal = open("final.csv", 'a', newline='')
    final = csv.writer(fileFinal)
    final.writerow((node[0], node[1],  node[2], node[3], node[4], node[5], node[6], node[7], str(totalLoc)))
    fileFinal.close()

#Clone repository and read files to count LOC
def cloneAndReadFileAndGetLoc(gitURL, repo_path, node):
    clone_repository(gitURL, repo_path)
    print("Git clone finalizado. \nLendo arquivos do Repositório e calculando LOC.....")
    global totalLoc
    totalLoc = 0
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith('.py'):
                fullpath = os.path.join(root, file)
                with open(fullpath, encoding="utf8") as f:
                    content = f.read()
                    b = analyze(content)
                    i = 0
                    for item in b:
                        if i == 0:
                            totalLoc += item
                            i += 1

#Create base.csv
if not os.path.exists("base.csv"):
    print("\n -------------- Iniciando processo pesquisa GraphQl -------------- \n")

    # Query GraphQL to look for first 1000 repositories in Python over 100 stars
    query = """
    query example{
      search (query:"stars:>100 and language:Python", type: REPOSITORY, first:10{AFTER}) {
          pageInfo{
           hasNextPage
            endCursor
          }
          nodes {
            ... on Repository {
              nameWithOwner
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
    result = run_query(json, headers)  # Run Query
    nodes = result["data"]["search"]["nodes"]  # split string to show only the nodes
    next_page = result["data"]["search"]["pageInfo"]["hasNextPage"]

    page = 0
    while next_page and total_pages < 10:
        total_pages += 1
        cursor = result["data"]["search"]["pageInfo"]["endCursor"]
        next_query = query.replace("{AFTER}", ", after: \"%s\"" % cursor)
        json["query"] = next_query
        result = run_query(json, headers)
        nodes += result['data']['search']['nodes']
        next_page = result["data"]["search"]["pageInfo"]["hasNextPage"]
        print(".", end='')
    print("]")

    print("Criando arquivo base CSV")
    file = open("base.csv", 'w', newline='')
    repository = csv.writer(file)

    print("Salvando Repositorios:\n[", end='')
    num = 0
    for node in nodes:
        repository.writerow((node['nameWithOwner'], str(node['url']),
                             str(node['stargazers']['totalCount']), str(node['watchers']['totalCount']),
                             str(node['forks']['totalCount']), str(node['releases']['totalCount']),
                             node['createdAt'], node['primaryLanguage']['name']))
        num = num + 1
        if (num % 10) == 0:
            print(".", end='')
    print("]\nProcesso concluido")
    file.close()


print("\n ------------------- Começo leitura repositorios ------------------- \n")

numRepo = 0
contNode = 0
totalLoc = 0
lastLine = where_stop()

print("lastLine: " + str(lastLine) + "\n")

#Insert table header in final.csv
if not os.path.exists("final.csv"):
    fileFinal = open("final.csv", 'w', newline='')
    final = csv.writer(fileFinal)
    final.writerow(('nameWithOwner', 'url', 'stargazers/totalCount', 'watchers/totalCount',
                    'forks/totalCount', 'releases/totalCount', 'createdAt', 'primaryLanguage/name', "totalLOC"))
    fileFinal.close()


fileBase = open("base.csv", 'r')
base = csv.reader(fileBase)

for node in base:
    if (contNode >= lastLine-1):
        repo_path = 'Repository/' + str(numRepo)
        while os.path.exists(repo_path):
            if totalLoc != -1: #to avoid possible error
                clean_repository(repo_path)
            numRepo += 1
            repo_path = 'Repository/' + str(numRepo)
        print(" ----- Inicio " + repo_path + " ----- \n")
        gitURL = node[1] + ".git"
        print("Começa o git clone")
        print(gitURL)
      #setting timeout
        clrd = threading.Thread(target=cloneAndReadFileAndGetLoc, args=(gitURL, repo_path, node))
        clrd.daemon = True
        clrd.start()
        clrd.join(TIME_LIMIT_TO_FIND_LOC) # Wait for x seconds or until process finishes
        if clrd.is_alive(): # If thread is still active
            print("\n--> Excedeu limite de tempo. Interrompendo análise do repositório.....")
            th = threading.currentThread()
            th._stop
            time.sleep(TIMESLEEP)
            totalLoc = -1 # Define a negative value for LOC
        print("Total loc final é " + str(totalLoc))
        writeInFinalFile(node, totalLoc)
        print("\n ------ Fim " + repo_path + " ------- \n")
        if totalLoc != -1: #to avoid possible error
            if os.path.exists(repo_path):
                clean_repository(repo_path)
    else:
        contNode +=1
        
fileBase.close()

print("\n ---------------------- Fim da execução ---------------------- \n")
