def main():
    n = int(input())
    lista = list(map(int,input().split()))
    ini = 0 
    fin = len(lista)-1
    salida = list()
    ejecutar = True
    while ejecutar:
        if lista[ini]>lista[fin]:
            salida.append(1)
            fin-=1
        elif lista[ini]<lista[fin]:
            salida.append(2)
            ini+=1
        else:
            salida.append(0)
            fin-=1
            ini+=1
        if ini==len(lista) or fin<0:
            ejecutar=False
    print(' '.join(map(str,salida)))

if __name__=='__main__':
    main()