from decimal import Decimal, ROUND_DOWN, ROUND_UP
import math

import cv2
import numpy as np
from PIL import Image


def perspective(img, pts):
    """
    射影変換を行う
    pts：1続きの4点のarray型
    """
    corner = np.float32([[320, 240], [320, 2640], [3520, 2640], [3520, 240]])
    p = cv2.getPerspectiveTransform(np.float32(pts), corner)
    img_pers = cv2.warpPerspective(img, p, (4000, 3000))
    return img_pers


def invert(img):
    """
    ネガポジ変換
    """
    img_inv = cv2.bitwise_not(img)
    return img_inv


def degree(x1, y1, x2, y2):
    """
    長辺が水平になるように、回転角を決める
    """
    rad = math.atan2(y1 - y2, x1 - x2)
    deg = math.degrees(rad)
    if 90 < deg:
        deg -= 180
    if deg < -90:
        deg += 180

    if deg < -45:
        deg += 90
    if deg > 45:
        deg -= 90
    return deg


def rotation(img, deg):
    """
    回転角に従って画像を回転する
    """
    img_pil = Image.fromarray(img)
    img_rot = img_pil.rotate(deg, resample=Image.BILINEAR, expand=True)
    img_rot = np.asarray(img_rot)
    return img_rot


def preprocessing(image, max_gap=30):
    """
    エッジ検出からハフ変換によって直線を検出。
    ハフ変換で検出した直線の角度の最頻値を利用して回転。
    :param image: 画像
    :param max_gap: 直線と認識する点の最大距離
    :return: 回転後画像
    """
    # 画像を2値化してエッジ検出する
    pts = np.load("pers_num.npy")[0]
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    img_canny = cv2.Canny(img_gray, 100, 200)  # エッジ検出
    img_canny = perspective(img_canny, pts)  # 射影変換
    kernel = np.ones((3, 3), np.uint8)
    img_canny = cv2.morphologyEx(img_canny, cv2.MORPH_CLOSE, kernel)
    # エッジの穴の部分を埋めるための輪郭検出
    contours, hierarchy = cv2.findContours(img_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭検出
    for cnt in contours:
        cv2.drawContours(img_canny, [cnt], -1, 255, -1)
    # 製品部分ではなく余白部分を抽出
    img_canny_inv = invert(img_canny)
    kernel = np.ones((3, 3), np.uint8)
    img_canny_inv = cv2.erode(img_canny_inv, kernel, iterations=1)
    # 余白のエッジを抽出
    img_canny_2 = cv2.Canny(img_canny_inv, 100, 200)

    image = perspective(image, pts)
    degs = []
    degs_times = []
    try:
        finish = False
        get_result_deg = True
        check = 0
        result_deg = 0
        # ハフ変換で直線を検出
        min_length = 500  # 直線の最小の長さ
        while min_length > 0:
            threshold = 500  # 直線状の点の数(?)
            while threshold > 0:
                # 確率的ハフ変換で検出
                lines = cv2.HoughLinesP(img_canny_2, 1, np.pi/720,  # 角度は0.5°ずつ検出
                                        threshold=threshold, minLineLength=min_length, maxLineGap=max_gap)
                if lines is not None:  # 直線が検出できた場合
                    for line in lines:
                        x1, y1, x2, y2 = line[0]
                        deg = degree(x1, y1, x2, y2)  # 角度を求める
                        if deg not in degs:  # 角度がかぶっている場合はスルー
                            degs.append(deg)
                            degs_times.append(deg)
                        else:
                            degs_times.append(deg)
                    if len(degs) >= check:  # 新しい角度が見つかった場合
                        while check < len(degs):
                            deg = degs[check]
                            # 回転してから直線を探してみる
                            img_canny_rot = rotation(img_canny_2, deg)
                            lines = cv2.HoughLinesP(img_canny_rot, 1, np.pi / 360,  # 角度は0.5°ずつ検出
                                                    threshold=threshold, minLineLength=min_length, maxLineGap=max_gap)
                            if lines is not None:  # 直線が検出できた場合
                                _degs = []
                                for line in lines:
                                    x1, y1, x2, y2 = line[0]
                                    _deg = degree(x1, y1, x2, y2)
                                    if _deg < 0:
                                        _deg_decimal = Decimal(str(_deg)).quantize(Decimal("0.1"), rounding=ROUND_DOWN)
                                        _deg = float(_deg_decimal)
                                    else:
                                        _deg_decimal = Decimal(str(_deg)).quantize(Decimal("0.1"), rounding=ROUND_UP)
                                        _deg = float(_deg_decimal)
                                    if _deg != -45.0 and _deg != 45.0:
                                        if _deg not in _degs:
                                            _degs.append(_deg)
                                # 正しく回転している場合は-0.5~0.5の角度以外は検出されない(?)
                                if len(_degs) > 0 and np.all(np.array(_degs) <= 0.5) and np.all(np.array(_degs) >= -0.5):
                                    result_deg = deg
                                    finish = True  # 角度検出を終了する
                                    break
                                else:
                                    check += 1
                                if check > 10:  # 正しい角度が見つからない場合終了する
                                    finish = True
                                    get_result_deg = False
                                    break
                            else:
                                check += 1
                        if finish is True:
                            break
                        threshold -= 50
                    else:
                        threshold -= 50  # 閾値を下げてもう一度検出する
                else:
                    threshold -= 50  # 閾値を下げてもう一度検出する
            if finish is True:
                break
            min_length -= 50

        # 検出した角度の中央値をとる
        if get_result_deg is False:
            degs_abs = []
            for _deg in degs_times:
                degs_abs.append(abs(_deg))
            # 45°付近の直線が検出されたが他の角度の直線が検出されている場合、誤りであることが多いので削除
            while True:
                # 角度の絶対値の最小と最大の差が10以上ある場合は最大を削除
                deg_min = np.min(degs_abs)
                deg_max = np.max(degs_abs)
                if deg_max - deg_min > 30:
                    _degs = []
                    _degs_abs = []
                    for deg in degs_times:  # 最大の角度がいくつか存在する可能性があるので新しいリストを作成
                        if abs(deg) != deg_max:
                            _degs.append(deg)
                    for deg in degs_abs:
                        if deg != deg_max:
                            _degs_abs.append(deg)
                    degs_times = _degs
                    degs_abs = _degs_abs
                else:
                    break
            result_deg = np.median(degs_times)

        img_rot = rotation(image, result_deg)

    except Exception as err:
        import traceback
        import datetime
        import os
        error_dir = "./preprocessing_error/"
        os.makedirs(error_dir, exist_ok=True)
        now = datetime.datetime.now()
        str_now = "{0:%m%d_%H%M}".format(now)
        file_name = error_dir + str_now + ".txt"
        with open(file_name, "w") as f:
            pass
        traceback.print_exc(file=open(file_name, "a"))
        img_rot = image
    finally:
        result = img_rot
    return result


if __name__ == '__main__':
    import sys
    path = sys.argv[1]
    n = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(n, cv2.IMREAD_COLOR)
    img_rot = preprocessing(img)
    cv2.imwrite("pre.jpg", img_rot)
