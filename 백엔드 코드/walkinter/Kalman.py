import numpy as np
import pandas as pd

def apply_kalman_filter(measurements, Q, R):
    n_iter = len(measurements)
    sz = (n_iter,)  # 배열의 크기 설정

    xhat = np.zeros(sz)      # 추정값
    P = np.zeros(sz)         # 오차 공분산
    xhatminus = np.zeros(sz) # 사전 추정값
    Pminus = np.zeros(sz)    # 사전 오차 공분산
    K = np.zeros(sz)         # 칼만 이득

    xhat[0] = 0.0
    P[0] = 2.0

    for k in range(1, n_iter):
        xhatminus[k] = xhat[k-1]
        Pminus[k] = P[k-1] + Q

        K[k] = Pminus[k] / (Pminus[k] + R)
        xhat[k] = xhatminus[k] + K[k] * (measurements[k] - xhatminus[k])
        P[k] = (1 - K[k]) * Pminus[k]

    return xhat

