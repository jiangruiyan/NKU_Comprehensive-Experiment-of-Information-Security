import random
import math
import csv
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

# 使用说明：该文件提供了一个基本的MWEM-2D算法框架，关键部分需要同学们通过自学python语言和算法相关内容进行补全。
# 需要补全的位置已经标出。

# 该值是用于确定算法启动模式，为True时会读取/Dataset文件夹下的数据集，为False时使用随机数据
# 真实数据的好处是来自现实世界，是实际有效的数据，更有意义
# 随机数据的好处是分布更加均匀
USING_INPUT_DATA = True

# B:输入数据
# rows：拆分出的行信息
# colums: 拆分出的列信息
# minRow:行最小值
# minCol:列最小值
# 从原始的MWEM文件我们可知，1D数据可以看做是一维的数据，所以只需要一个列表
# 而2D数据是二维的，所以我们需要创造一个矩阵。
# 实际上，这个函数就是将行、列的分桶情况组合并创造出一个二维的列表（其他语言称之为数组）
# 其格式类似于:histogram[row][column]，而histogram[x][y]相当于是对B执行了一次row=x，column=y的count查询的解
# 对于我们给定的两列数据，这个矩阵规模会是14行4列，因为第一列14种取值，第二列4种
def matrixCreation(B, rows, columns, minRow, minCol):
    # 先初始化一个全0的、规模为row*column的矩阵
    histogram = [[0]*(columns) for i in range(rows)]
    # 启动遍历，将B中数据填进矩阵中 
    for val in range(len(B[0])):
        histogram[B[0][val] - minRow][B[1][val] - minCol] += 1 
    return histogram


# B:原始数据
# Q:查询集
# T:迭代次数
# eps:隐私预算
# repetitions:乘法权重算法的重复次数
def MWEM(B, Q, T, eps, repetitions):
    # 初始化真实数据集对应的直方图
    # 基本逻辑与1D相同，而与1D不同的是，这里要同时考虑行列的最大最小值以确定桶
    minRow = min(B[0])
    minCol = min(B[1])
    rows = max(B[0]) - min(B[0]) + 1 #age
    columns = max(B[1]) - min(B[1]) + 1 #satisfaction
    # 这里的直方图发生了变化，从一个列表变成了矩阵，具体可以参考matrixCreation函数
    histogram = matrixCreation(B,rows,columns,minRow,minCol)

    # 初始化数据合成流程
    nAtt = 2 # 合成算法作用的属性数量
    A = []
    n = 0
    # 初始化一个分布平均的查询作为初始的分布
    # 先算所有行的每行加和，再将这些sum值再次sum，得到总矩阵的和
    # 然后平均分配给矩阵各个单元格
    m = [sum(histogram[i]) for i in range(len(histogram))]
    n = sum(m)
    value = n/(rows*columns)
    A = [[0]*(columns) for i in range(rows)]
    for i in range(len(histogram)):
        for j in range(len(histogram[i])):
            A[i][j] += value

    measurements = {} # esurements是一个dict类型，其初始化时应该以{ }初始化
    # 迭代优化循环体
    for i in range(T):
        print("ITERATION #" + str(i))
        # ****需要补全**** #
        # 本部分的执行逻辑：首先，选定本轮要优化的查询在查询集Q中的位置qi，同时，如果出现与此前一致的查询则再运行一次算法，直到选中从未优化过的查询
        # 具体流程：先调用指数机制来在查询集Q中选择一个查询，并反馈其在查询集Q中的位置qi。
        # 然后，查看该查询是否已经在mesurements内存储，若已有则重启选择，直到选中未优化过的查询
        # 其中，问号"?"代表该处需要补全，下同。此外，已经给出的代码也有可能不是完全完整的，请酌情进行添加。

        # 选定本轮要优化的查询，同时，如果出现与此前一致的查询则再运行一次算法，直到选中从未优化过的查询
        # mesurements:已观测的查询，将查询收入此以避免重复优化
        qi = "?"

        while("?"):
            qi = ExpM(histogram, A, Q, eps / (2*T))

        # 对查询值进行观测并加入已观测的列表中
        evaluate = Evaluate(Q[qi],histogram)
        lap = Laplace((2*T)/(eps*nAtt))
        measurements[qi] = evaluate + lap
         # ****补全结束**** #

        # 乘法权重更新开始
        MultiplicativeWeights(A, Q, measurements, repetitions)

    return A, histogram


# B:原始数据
# A:合成数据
# Q:查询集
# T:迭代次数
# eps:隐私预算
# ExpM-使用指数机制来选定一个查询
# 本部分算法原理：首先测量对原始数据集和合成数据运行同一个查询时其之间的误差作为打分函数，
# 根据各查询得分的多少计算出每个查询被选中的概率，之后基于这些概率随机抽取一个查询。
# 【本机制与一维时无变化！】
def ExpM(B, A, Q, eps):
    # 初始化一个Q长度的打分列表。其他类似初始化方式不再赘述。
    scores = [0] * len(Q)
    for i in range(len(scores)):
        # ****需要补全**** #
        # 该循环体即为打分函数。此处我们使用的打分原始来源是原数据和估计数据在响应同一个查询时差异的绝对值。
        # 但是由于绝对误差太大，会造成指数计算越界，所以此处需要除以100000来缩小错误的规模
        # 使用该方法对得分的相对差距是不会有影响的。
        scores[i] ="?"/100000
    # 基于分数计算每个查询被选中的概率
    Pr = ["?" for score in scores]
    # 规范化概率，使其和为1
    Pr = Pr / np.linalg.norm(Pr, ord=1)
    # 基于生成的概率表抽取查询
    return "?"
    # ****补全结束**** #

# 请设计函数，利用给定的sigma来生成拉普拉斯随机数noise作为噪音。
# 提示:可以看看numpy的随机数模块。
def Laplace(sigma):
    noise = '?'
    return noise

# 请根据文献、Julia代码和此处的辅助描述，来完成该函数。
# A:合成数据
# Q:查询集
# measurements:已观测过的查询
# repetitions:重复次数
def MultiplicativeWeights(A, Q, measurements, repetitions):
    # 应使用一个内联的循环体实现，用于重复地更新多次乘法权重
    # 对所有观测值进行更新时，根据原始算法实现的Julia，需要先对measurements生成一个随机的更新顺序，再利用洗牌算法打乱更新顺序
    # 根据新生成的访问顺序来对乘法权重执行更新
    # 具体更新方法是先计算观测值和合成数据之间的误差，此后将所有查询转换为二进制形式。
    # 之后，使用MW机制核心算法来对A内的每个数值都执行一次乘法权重更新。注意，在我们的实现中，因为需要一个值来降低实际error以防越界，所以需要额外除一个total，total的定义已经给出。
    # 即，如果MW在数学实现上除的2.0，那么你在写的时候应该改写为/(2.0 * total)  
    # 最后，对A上的所有值执行重新归一化，保证更新后的权重全部处于有效区间内。
    # 提示：根据2D数据特点，遍历和误差计算方式应进行相应改变，其他基本算法逻辑是一致的。

    m = [sum(A[i]) for i in range(len(A))]
    total = sum(m)

# 由于2D的算法是提高用内容，我们不再将以下函数独立成一个python文件
# 但是其实下面这几个函数就是errortools.py内函数的二维版

# query:指定的查询
# data:运行查询的数据
# Evaluate函数用于执行查询。其基本逻辑为：
# 对于传入的查询{(x,y):(x,y)}，其累加传入的数据中，值在x和y区间(含x和y)的查询。
def Evaluate(query, data):
    # 查询集Q本身是一个以dict为项目的list，也就是说，每个查询都是一个dict类型数据
    # 这里，我们先将dict类型做list化来正确获取dict的左值(即在行上的查询)，绕开dict无序的限制
    # 然后我们就可以再用获取到的左值来获得dict的右值了，即可将dict还原回两个list的组合
    q_x = list(query)[0]
    q_y = query[q_x]
    counts = 0
    for i in range(q_x[0],q_x[1]+1):
        for j in range(q_y[0],q_y[1]+1):
            counts += data[i][j]
    return counts

# qi:输入的查询
# cols:行长度
# rows：列长度
# 转换查询为二进制形式，用于MW机制使用
# 运行逻辑：MW机制是对符合区间的桶进行乘法权重更新，这里使用一个binary序列来代表数据集的桶是否属于区间。
# 首先，将binary全部置0，然后将输入的查询区间内的桶对应的binary值变为1。这样的话，根据这个binary值，
# MW机制就能只更新所选查询影响到的桶了。
def queryToBinary(qi, cols, rows):
    binary = [[0]*cols for i in range(rows)] 
    # 这个地方操作原理和Evaluate以及1D情况下的ToBinary类似，不再赘述
    q_x = list(qi)[0]
    q_y = qi[q_x]
    for i in range(rows):
        if (i >= q_x[0]) and (i <= q_x[1]):
            for j in range(cols):
                if (j >= q_y[0]) and (j <= q_y[1]):
                    binary[i][j] = 1
    return binary

# real:真实数据
# synthetic:合成数据
# Q:查询集合
# maxError函数用于检测传入的两数据集间的最大差异。
# 该函数会计算传入的两数据集对于查询集Q的响应，并找出最大的差异值（以绝对值计算）
def maxError(real, synthetic, Q):
    maxVal = 0
    diff = 0
    for i in range(len(Q)):
        diff = abs(Evaluate(Q[i], real) - Evaluate(Q[i], synthetic))
        if diff > maxVal:
            maxVal = diff
    return maxVal

# real:真实数据
# synthetic:合成数据
# Q:查询集合
# meansSqError函数用于检测传入的两数据集间的均方差。
# 该函数会计算传入的两数据集对于查询集Q的响应，计算其均方差。（以绝对值计算）
def meanSqErr(real, synthetic, Q):
    errors = [(Evaluate(Q[i], synthetic) - Evaluate(Q[i], real)) for i in range(len(Q))]
    return (np.linalg.norm((errors))**2)/len(errors)

# real:真实数据
# synthetic:合成数据
# Q:查询集合
# minError函数用于检测传入的两数据集间的最小差异。
# 该函数会计算传入的两数据集对于查询集Q的响应，并找出最小的差异值（以绝对值计算）
def minError(real, synthetic, Q):
    minVal = 100000000000
    diff = 0
    for i in range(len(Q)):
        diff = abs(Evaluate(Q[i], real) - Evaluate(Q[i], synthetic))
        if diff < minVal:
            minVal = diff
    return minVal

# real:真实数据
# synthetic:合成数据
# Q:查询集合
# meanError函数用于检测传入的两数据集间的平均差异。
# 该函数会计算传入的两数据集对于查询集Q的响应，并计算差异平均值（以绝对值计算）
def meanError(real, synthetic, Q):
    errors = [abs(Evaluate(Q[i], synthetic) - Evaluate(Q[i], real)) for i in range(len(Q))]
    return sum(errors)/len(errors)


# 随机生成Q_size个查询，并对查询集中的已有查询规避
# 运行逻辑和1D时基本类似，也是先生成两个维度上的查询上下界，然后判断这个查询是否已经出现在已有查询之中了
# 如果在的话则重新生成一个
# 当两个维度值域较小的时候，重新生成的次数可能会非常多
# 该函数请根据一维时的情况，由参数表、输出结构自行补全。提示：
# 1. Q应该是一个列表嵌套字典的格式，即其中一项可能是：[{(2,3):(3,3)}]，结合Evaluate和一维时的生成方式，考虑下怎么生成？
# 2. 要和一维时一样，能规避已有查询并重新生成，还能统计生成的数量
def randomQueries(Q_size, maxVal1, minVal1,maxVal2,minVal2):
    # 此时生成的是一个列表嵌套字典的格式
    Q=[]
    count_regen = 0
    "?"
    print("查询集随机生成完毕，生成了"+str(Q_size)+"个查询，共进行规避生成"+str(count_regen)+"次")
    return Q

def main():

    B = []  # 二维数据也可以是个多维的list
    Q_size = 400 # 查询集查询个数
    T = 200 # T是迭代运行次数。要注意的是，该处迭代次数不应大于上一步所生成的查询总数。
    eps = 0.1 # eps即epsilon，隐私预算。
    repetitions = 20 # MW机制的重复次数，一般不需更改

    B.append([])
    B.append([])
    # 使用外部数据时，该部分即为读取指定路径的测试数据。
    if USING_INPUT_DATA == True: 
        with open('Datasets/childMentalHealth_1M.csv', 'rt') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                    try:
                        B[0].append(int(row[0]))
                        B[1].append(int(row[1]))
                    except ValueError as e:
                        continue
                    except IndexError as e:
                        continue
    # 保留了一个测试模式：当不指定输入数据集时，允许随机生成一个6行2000列的记录来进行测试
    else:
        B = [[random.randint(0,100) for i in range(6)], [random.randint(0,100) for i in range(2000)]] #Dataset


   # 限制上下界
    maxVal1 = max(B[0])
    maxVal2 = max(B[1])
    minVal1 = min(B[0])
    minVal2 = min(B[1])

    # 随机生成Q_size个查询，并对查询集中的已有查询规避
    Q = {}
    Q = randomQueries(Q_size, maxVal1, minVal1,maxVal2,minVal2)

    print()
        
    #启动MWEM
    SyntheticData, RealHisto = MWEM(B, Q, T, eps, repetitions)
        
    #获得分析数据
    maxErr = maxError(RealHisto, SyntheticData, Q)
    minErr = minError(RealHisto, SyntheticData, Q)
    mse = meanSqErr(RealHisto, SyntheticData, Q)
        
    print()
    print("Real data histogram: " + str(RealHisto))
    print()
    # 格式化地输出合成数据到屏幕
    print("Synthetic Data: " + str(SyntheticData))
    print()
    print("Metrics:")
    print("  - Max Error: " + str(maxErr))
    print("  - Min Error: " + str(minErr))
    print("  - Mean Squared Error: " + str(mse))
    print("  - Mean Error: " + str(meanError(RealHisto, SyntheticData, Q)))
    print()
    
    
    #Plot化数据和生成直方图
    print("************ REAL DATA *******************")    
    
    H = np.array(RealHisto)

    fig = plt.figure(figsize=(4, 4.2))

    ax = fig.add_subplot(111)
    ax.set_title('colorMap')
    plt.imshow(H)
    ax.set_aspect('equal')

    cax = fig.add_axes([0.12, 0.1, 0.78, 0.8])
    cax.get_xaxis().set_visible(False)
    cax.get_yaxis().set_visible(False)
    cax.patch.set_alpha(0)
    cax.set_frame_on(False)
    plt.colorbar(orientation='vertical',ax=cax)
    plt.savefig("./Results/result_2D_TRUE.png")
    plt.show()
    
    print()
    print("************ Synthetic DATA **************")
    
    H2 = np.array(SyntheticData)

    fig = plt.figure(figsize=(4, 4.2))

    ax = fig.add_subplot(111)
    ax.set_title('colorMap')
    plt.imshow(H2)
    ax.set_aspect('equal')

    cax = fig.add_axes([0.12, 0.1, 0.78, 0.8])
    cax.get_xaxis().set_visible(False)
    cax.get_yaxis().set_visible(False)
    cax.patch.set_alpha(0)
    cax.set_frame_on(False)
    plt.colorbar(orientation='vertical',ax=cax)
    plt.savefig("./Results/result_2D_SYN.png")
    plt.show()
    
main()
