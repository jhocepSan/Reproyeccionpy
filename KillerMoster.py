from collections import deque

def main():
    k = int(input())
    for _ in range(k):
        listaLeng =list()
        campo = deque()
        aux = deque()
        n = int(input())
        montros = list(map(int,input().split()))
        for i in montros:
            if len(campo)==0:
                campo.append(i)
            else:
                while len(campo)!=0:
                    m = campo.pop()
                    if m>i:
                        aux.append(m)
                aux.append(i)
                campo=aux.copy()
                aux=deque()
            listaLeng.append(len(campo))
        print(" ".join(map(str, listaLeng)))
if __name__=='__main__':
    main()