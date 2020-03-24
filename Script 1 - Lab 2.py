import requests
import json
import time
import os
import shutil
import errno
import stat
import subprocess
from radon.raw import analyze
from pygit2 import clone_repository


headers = {"Authorization": "Bearer Your key here"}


def run_query(json, headers): #Função que executa uma request pela api graphql 
    request = requests.post('https://api.github.com/graphql', json=json, headers=headers) #efetua uma requisição post determinando o json com a query recebida
    while (request.status_code == 502):
      time.sleep(2)
      request = requests.post('https://api.github.com/graphql', json=json, headers=headers)
    if request.status_code == 200:
        return request.json() #json que retorna da requisição
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))


#Respostas das perguntas na Query:
#Questão 1 - 
#Questão 2 - 
#Questão 3 - 
#Questão 4 - 
#Questão 5 - 
#Questão 5 - 


query = """
query example{  
          user(login: "gvanrossum") {
              repositories(first: 100, isFork: false) {
      			totalCount
                nodes {
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


print("\n\n ------------- Começo da consulta com graphQL ------------- \n" )

#finalQuery = query.replace("{AFTER}", "")


json={"query": query}


#total_pages = 1

result = run_query(json, headers)

#print(result)
nodes = result['data']['user']['repositories']['nodes']
totalRepos = str(result['data']['user']['repositories']['totalCount'])
print("total repositorios encontrados = " + totalRepos + "\n")
#next_page  = result["data"]["search"]["pageInfo"]["hasNextPage"]

#paginating
#while (next_page and total_pages < 50):
#    total_pages += 1
#    cursor = result["data"]["search"]["pageInfo"]["endCursor"]
#    next_query = query.replace("{AFTER}", ", after: \"%s\"" % cursor)
#    json["query"] = next_query
#    result = run_query(json, headers)
#    nodes += result['data']['search']['nodes']
#    next_page  = result["data"]["search"]["pageInfo"]["hasNextPage"]


#print("\n\n ------------- Retorno da consulta com graphQL para responder as Questões de 1 a 6 ------------- \n" )
#print(nodes)

#saving data

if os.path.exists("repos.csv"):
  os.remove("repos.csv")


def on_rm_error(func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod(path, stat.S_IWRITE )
    os.unlink(path)

def cleanRepository(folder):
  for filename in os.listdir(folder):
      file_path = os.path.join(folder, filename)
      try:
          if os.path.isfile(file_path) or os.path.islink(file_path):
              os.unlink(file_path)
          elif os.path.isdir(file_path):
              shutil.rmtree(file_path, onerror = on_rm_error)
      except Exception as e:
          print('Failed to delete %s. Reason: %s' % (file_path, e))

numRepo = 0

print("\n ------ Começo leitura repositorios ------ \n" )

with open("repos.csv", 'w') as the_file:
        the_file.write("nameWithOwner" + ";" + "url" + ";" + "stars" + ";" 
        + "watchers" + ";" + "forks" + ";" + "releases" + ";" 
        + "createdAt" + ";" + "primaryLanguage" + ";" + "totalLOC" +"\n")
for node in nodes:
    if node['primaryLanguage'] is not None:
        if node['primaryLanguage']['name'] == "Python" and node['nameWithOwner'] != "fake-python/cpython":
          repo_path = 'Repository/' + str(numRepo)
          if(os.path.exists(repo_path)):
            cleanRepository(repo_path)
            print("\n" + "Limpeza da pasta do Repositório: ")
          print("repo_path = " + repo_path)
          numRepo += 1
          #print("\n" + "Comeca limpeza")
          #cleanRepository(repo_path)
          time.sleep(1)
          #if os.path.exists("Repository/.git"):
           # print("\n entrou no if do apagar")
            #for root, dirs, files in os.walk('Repository/.git'):
             # for fname in files:
              #  full_path = os.path.join(root, fname)
               # print("\n Tentando apagar o " + full_path)
                #os.chmod(full_path, stat.S_IWRITE)
                #os.remove(full_path)      
              #for dir in dirs:
               # full_path = os.path.join(root, dir)
                #subprocess.check_call(('attrib -R ' + full_path + '\\* /S').split())
                #cleanRepository(full_path)
            #cleanRepository("Repository/.git")
            #cleanRepository("Repository/.git/objects/pack")
          #cleanRepository(repo_path)
          totalLoc = 0
          gitURL = node['url'] + ".git"
          print("\n" + "Começa o git clone")
          print(node['url'])
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
                    if i==0:
                      totalLoc += item
                      print("loc = " + str(item))
                      print("Total loc até agora: " + str(totalLoc))
                      i+=1
          print("\nTotal loc final para o repo " + node['nameWithOwner'] + " é " + str(totalLoc))
          print("\n ------ Fim de um repositorio ------ \n" )
          cleanRepository(repo_path)
          with open("repos.csv", 'a') as the_file:
                the_file.write(node['nameWithOwner'] + ";" + node['url'] + ";" + str(node['stargazers']['totalCount'])
                + ";" + str(node['watchers']['totalCount']) + ";" + str(node['forks']['totalCount']) + ";"
                + str(node['releases']['totalCount']) + ";" + node['createdAt'] + ";" + node['primaryLanguage']['name'] + ";" + str(totalLoc) +  "\n") 
          
print("Total repositórios " + str(numRepo))
print("\n ------------- Fim da execução ------------- \n" )