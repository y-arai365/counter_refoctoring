"""
イレギュラー検知
端材の残りの誤検出や、ピースズレのピースの検出を
製品の色を基準にして行う。
端材の残りは白く、製品と分離可能。
どちらもマッチング結果との比較によって位置を取得する
"""

import cv2
import numpy as np


def color_thresh(img):
    b, g, r = cv2.split(img)   # チャンネル分解
    average_b = np.average(b)
    average_g = np.average(g)
    average_r = np.average(r)
    return average_b, average_g, average_r


def channel_thresh(img, thresh_b, thresh_g, thresh_r):
    """
    それぞれのチャンネルを閾値によって2値化したものを合成する
    :param img: 元画像
    :param thresh_b: 青を2値化するときの閾値
    :param thresh_g: 緑を2値化するときの閾値
    :param thresh_r: 赤を2値化するときの閾値
    :return: 変換後の画像
    """
    b, g, r = cv2.split(img)   # チャンネル分解
    b = np.where(b > thresh_b, 255, 0)
    g = np.where(g > thresh_g, 255, 0)
    r = np.where(r > thresh_r, 255, 0)
    bgr = cv2.merge((b, g, r))  # チャンネル合成
    return bgr


def color_change(img, before_color, after_color, condition=True):
    """
    画像の色を変更する関数
    np.whereで条件に当てはまったピクセルを変更する
    :param img: 変更する画像
    :param before_color: 変更前の色(条件式に入る色)
    :param after_color: 変更後の色
    :param condition: True --> all False --> any
    :return: 変更後の画像
    """
    if condition is True:
        img[np.where(((img == before_color).all(axis=2)))] = after_color
    else:
        img[np.where(((img != before_color).any(axis=2)))] = after_color
    return img


def morphology(img, kernel_size, morpho):
    """
    よく使用するモルフォロジー変換をまとめた関数
    :param img: 2値化画像
    :param kernel_size: 奇数
    :param morpho: 変換の手法
    :return: 変換した結果の画像
    """
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    if morpho == "dilate":  # 膨張
        dst = cv2.dilate(img, kernel, iterations=1)
    elif morpho == "erode":  # 収縮
        dst = cv2.erode(img, kernel, iterations=1)
    elif morpho == "close":  # クロージング(収縮＋膨張)
        dst = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    elif morpho == "open":  # オープニング(膨張＋収縮)
        dst = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
    else:
        dst = img
    return dst


def preprocessing(img_rot, pattern):
    p_h, p_w = pattern.shape[:2]
    pattern = pattern[2:p_h-2, 2:p_w-2]
    thresh_b, thresh_g, thresh_r = color_thresh(pattern)

    # それぞれのチャンネルを閾値によって2値化したものを合成する
    img_bgr = channel_thresh(img_rot, thresh_b+30, thresh_g-15, thresh_r-15)

    # 赤と黄色、緑以外を白に変換し、それ以外の色はすべて黒に変換する
    black_color = [0, 0, 0]
    white = [255, 255, 255]
    img_bgr = color_change(img_bgr, white, black_color)  # 白を先に黒に変換しておく
    red = [0, 0, 255]
    img_bgr = color_change(img_bgr, red, white)  # 赤を白に変換する
    yellow = [0, 255, 255]
    img_bgr = color_change(img_bgr, yellow, white)  # 黄色を白に変換する
    green = [0, 255, 0]
    img_bgr = color_change(img_bgr, green, white)  # 緑を白に変換する
    img_bgr = color_change(img_bgr, white, black_color, condition=False)  # 白以外の色を黒に変換する
    img_bgr = img_bgr.astype(np.uint8)
    img_bgr_thresh = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)  # 2値化して1チャンネルにする

    contours, hierarchy = cv2.findContours(img_bgr_thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(img_bgr_thresh, (x, y), (x+w, y+h), 255, -1)

    return img_bgr_thresh


def mill_ends(img, black,  result):
    img_dst = morphology(img, 5, "open")
    img_dst = morphology(img_dst, 9, "dilate")
    img_nega = cv2.bitwise_not(img_dst)

    img_mask = cv2.bitwise_and(black, black, mask=img_nega)  # マスクがけをする
    ret, img_mask = cv2.threshold(img_mask, 100, 255, cv2.THRESH_BINARY)
    img_mask = morphology(img_mask, 5, "open")

    contours, hierarchy = cv2.findContours(img_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭を抽出する
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(result, (x - 5, y - 5), (x + w + 5, y + h + 5), (255, 255, 0), 2)
    return result


def out_of_position(img, black, result):
    dst = morphology(black, 7, "dilate")  # 製品と製品の間の溝を無くす
    dst = morphology(dst, 3, "erode")  # 面積が広くなりすぎないように元に戻す
    dst_nega = cv2.bitwise_not(dst)

    img_mask = cv2.bitwise_and(img, img, mask=dst_nega)  # マスクがけをする
    ret, img_mask = cv2.threshold(img_mask, 100, 255, cv2.THRESH_BINARY)
    img_mask = morphology(img_mask, 5, "open")

    contours, hierarchy = cv2.findContours(img_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭を抽出する
    cv2.drawContours(result, contours, -1, (0, 0, 255), 2)
    return result


def irregular_detection(img, black, pattern, result, me=True, oop=True):
    """
    イレギュラー検知を行う関数
    me = mill ends 端材の検出
    oop = out of position　位置ズレした製品の検出
    :param img: 検出前画像
    :param black: カウントした結果の白黒画像
    :param pattern: パターン画像
    :param result: カウント結果描画後の画像
    :param me: True or False　検出を行うかどうか
    :param oop: True or False　検出を行うかどうか
    :return:　検出した結果
    """
    img_preprocess = preprocessing(img, pattern)
    # イレギュラー検知を2つとも行う場合
    if me is True and oop is True:
        result = mill_ends(img_preprocess, black, result)
        result = out_of_position(img_preprocess, black, result)
    # 端材の残りの検出のみする場合
    elif me is True:
        result = mill_ends(img_preprocess, black, result)
    #
    elif oop is True:
        result = out_of_position(img_preprocess, black, result)
    else:
        pass
    return result, img_preprocess
