#!/usr/bin/env python
# coding: utf-8

# # Part E: 梯度提升树（下）
# 
# ## 1. XGBoost基础
# 
# 由于树模型较强的拟合能力，我们需要对模型进行正则约束来控制每轮模型学习的进度，除了学习率参数之外，XGBoost还引入了两项作用于损失函数的正则项：首先我们希望树的生长受到抑制而引入$\gamma T$，其中的$T$为树的叶子节点个数，$\gamma$越大，树就越不容易生长；接着我们希望模型每次的拟合值较小而引入$\frac{1}{2}\lambda \sum_{i=1}^T w_i^2$，其中的$w_i$是回归树上第$i$个叶子结点的预测目标值。记第$m$轮中第$i$个样本在上一轮的预测值为$F^{(m-1)}_i$，本轮需要学习的树模型为$h^{(m)}$，此时的损失函数即为
# 
# $$
# L^{(m)}(h^{(m)}) = \gamma T+\frac{1}{2}\lambda \sum_{j=1}^Tw_j+\sum_{i=1}^NL(y_i, F^{(m-1)}_i+h^{(m)}(X_i)) 
# $$
# 
# 从参数空间的角度而言，损失即为
# 
# $$
# L^{(m)}(F^{(m)}_i)  = \gamma T+\frac{1}{2}\lambda \sum_{j=1}^Tw_j+\sum_{i=1}^NL(y_i, F^{(m)}_i)
# $$
# 
# 不同于上一节中GBDT的梯度下降方法，XGBoost直接在$h^{(m)}=0$处（或$F^{(m)}_i=F^{(m-1)}_i$处）将损失函数近似为一个二次函数，从而直接将该二次函数的顶点坐标作为$h^{*(m)}(X_i)$的值，即具有更小的损失。梯度下降法只依赖损失的一阶导数，当损失的一阶导数变化较大时，使用一步梯度获得的$h^{*(m)}$估计很容易越过最优点，甚至使得损失变大（如子图2所示）；二次函数近似的方法需要同时利用一阶导数和二阶导数的信息，因此对于$h^{*(m)}$的估计在某些情况下会比梯度下降法的估计值更加准确，或说对各类损失函数更有自适应性（如子图3和子图4所示）。
# 
# ```{figure} ../_static/gbdt_pic2.png
# ---
# width: 700px
# align: center
# ---
# ```
# 
# 为了得到$h^{*(m)}(X_i)$，记$h_i=h^{(m)}(X_i)$，$\textbf{h}=[h_1,...,h_N]$，我们需要先将损失函数显式地展开为一个关于$h^{(m)}(X_i)$的二次函数，：
# 
# $$
# \begin{aligned}
# L^{(m)}(\textbf{h}) &= \gamma T+\frac{1}{2}\lambda \sum_{j=1}^Tw_j+\sum_{i=1}^N L(y_i, F^{(m-1)}_i+h_i) \\
# &\approx \gamma T+\frac{1}{2}\lambda \sum_{j=1}^Tw_j+\sum_{i=1}^N [L(y_i, F^{(m-1)}_i)+\left . \frac{\partial L}{\partial h_i}\right |_{h_i=0} h_i+\frac{1}{2}\left . \frac{\partial^2 L}{\partial h^2_i}\right |_{h_i=0} h^2_i]\\
# &= \gamma T+\frac{1}{2}\lambda \sum_{j=1}^Tw_j+\sum_{i=1}^N [\left . \frac{\partial L}{\partial h_i}\right |_{h_i=0} h_i+\frac{1}{2}\left . \frac{\partial^2 L}{\partial h^2_i}\right |_{h_i=0} h^2_i] + constant
# \end{aligned}
# $$
# 
# ````{margin}
# 【练习】请写出$L^{(m)}(F^{(m)}_i)$在$F^{(m)}_i=F^{(m-1)}_i$处的二阶展开。
# ````
# ````{margin}
# 【练习】试说明不将损失函数展开至更高阶的原因。
# ````
# ````{margin}
# 【练习】请写出平方损失下的近似损失。
# ````
# 
# 由于近似后损失的第二项是按照叶子结点的编号来加和的，而第三项是按照样本编号来加和的，我们为了方便处理，不妨统一将第三项按照叶子结点的编号重排以统一形式。设叶子节点$j$上的样本编号集合为$I_j$，记$p_i=\left . \frac{\partial L}{\partial h_i}\right |_{h_i=0}$且$q_i=\left . \frac{\partial^2 L}{\partial h^2_i}\right |_{h_i=0}$，忽略常数项后有
# 
# $$
# \begin{aligned}
# \tilde{L}^{(m)}(\textbf{h}) &= \gamma T+\frac{1}{2}\lambda \sum_{j=1}^Tw_j+\sum_{i=1}^N [p_i h_i+\frac{1}{2}q_i h^2_i]\\
# &= \gamma T+\frac{1}{2}\lambda \sum_{j=1}^Tw_j+\sum_{j=1}^T[(\sum_{i\in I_j} p_i )w_j+\frac{1}{2}(\sum_{i\in I_j}q_i )w^2_i]\\
# &= \gamma T+\sum_{j=1}^T[(\sum_{i\in I_j} p_i )w_j+\frac{1}{2}(\sum_{i\in I_j}q_i +\lambda)w^2_i]\\
# &=\tilde{L}^{(m)}(\textbf{w})
# \end{aligned}
# $$
# 
# 上式的第二个等号是由于同一个叶子节点上的模型输出一定相同，即$I_j$中样本对应的$h_i$一定都是$w_j$。此时，我们将损失统一为了关于叶子节点值$\textbf{w}=[w_1,...,w_T]$的二次函数，从而可以求得最优的输出值为
# 
# $$
# w^*_j=-\frac{\sum_{i\in I_j}p_i}{\sum_{i\in I_j}q_i+\lambda}
# $$
# 
# 当前模型的近似损失（忽略常数项）即为
# 
# $$
# \begin{aligned}
# \tilde{L}^{(m)}(\textbf{w}^*)&=\gamma T+\sum_{j=1}^T[-\frac{(\sum_{i\in I_j}p_i)^2}{\sum_{i\in I_j}q_i+\lambda}+\frac{1}{2}\frac{(\sum_{i\in I_j}p_i)^2}{\sum_{i\in I_j}q_i+\lambda}]\\
# &= \gamma T-\frac{1}{2}\sum_{j=1}^T\frac{(\sum_{i\in I_j}p_i)^2}{\sum_{i\in I_j}q_i+\lambda}
# \end{aligned}
# $$
# 
# 在决策树的一节中，我们曾以信息增益作为节点分裂行为操作的依据，信息增益本质上就是一种损失，增益越大即子节点的平均纯度越高，从而损失就越小。因此我们可以直接将上述的近似损失来作为分裂的依据，即选择使得损失减少得最多的特征及其分割点来进行节点分裂。由于对于某一个节点而言，分裂前后整棵树的损失变化只和该节点$I$及其左右子节点$I_L$与$L_R$的$w^*$值有关，此时分裂带来的近似损失减少量为
# 
# $$
# \begin{aligned}
# G&= [\gamma T-\frac{1}{2}\frac{(\sum_{i\in I}p_i)^2}{\sum_{i\in I}q_i+\lambda}] - [\gamma (T+1)-\frac{1}{2}\frac{(\sum_{i\in I_L}p_i)^2}{\sum_{i\in I_L}q_i+\lambda}- \frac{1}{2}\frac{(\sum_{i\in I_R}p_i)^2}{\sum_{i\in I_R}q_i+\lambda}]\\
# &= \frac{1}{2}[\frac{(\sum_{i\in I_L}p_i)^2}{\sum_{i\in I_L}q_i+\lambda}+\frac{(\sum_{i\in I_R}p_i)^2}{\sum_{i\in I_R}q_i+\lambda}-\frac{(\sum_{i\in I}p_i)^2}{\sum_{i\in I}q_i+\lambda}] -\gamma
# \end{aligned}
# $$
# 
# 模型应当选择使得$G$达到最大的特征和分割点进行分裂。
# 
# ````{margin}
# 【练习】在下列的三个损失函数$L(y,\hat{y})$中，请选出一个不应作为XGBoost损失的函数并说明理由。
# - Root Absolute Error: $\sqrt{\vert y-\hat{y}\vert}$
# - Squared Log Error: $\frac{1}{2}[\log(\frac{y+1}{\hat{y}+1})]^2$
# - Pseudo Huber Error: $\delta^2(\sqrt{1+(\frac{y-\hat{y}}{\delta})^2}-1)$
# ````
# 
# 最后我们来重新回到单个样本的损失函数上：由于XGBoost使用的是二阶展开，为了保证函数在拐点处取到的是近似损失的最小值，需要满足二阶导数$q_i>0$。当损失函数不满足此条件时，$h^*_i$反而会使得损失上升，即如下图中右侧的情况所示，而使用梯度下降法时并不会产生此问题。因此，我们应当选择在整个定义域上或在$y_i$临域上二阶导数恒正的损失函数，例如平方损失。
# 
# ```{figure} ../_static/gbdt_pic3.png
# ---
# width: 500px
# align: center
# ---
# ```
# 
# ## 2. XGBoost的分割点查询
# 
# 
# 
# ## 3. XGBoost的系统设计
# 
# ## 4. LightGBM算法
# 
# LightGBM的GBDT原理与XGBoost的二阶近似方法完全一致，并且在此基础上提出了三个改进，它们分别是优化直方图算法、单边梯度采样以及互斥特征绑定。
# 
# ## 代码实践
# 
# ## 算法实现
# 
# ## 知识回顾
