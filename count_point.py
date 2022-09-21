# -*- coding: utf-8 -*-
"""
製品検出後、点検出も行う
"""
import sys

import cv2
import numpy as np


def binarize(img):
    """
    2値化
    """
    ret, img_thresh = cv2.threshold(img, 0, 255, cv2.THRESH_OTSU)
    return img_thresh, ret


def min_rect(contour, img):
    """
    最小外接矩形の頂点を取り出す
    """
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    img = img.copy()
    cv2.drawContours(img, [contour], -1, (0, 255, 0), 10)
    cv2.drawContours(img, [box], 0, (0, 0, 255), 10)

    return box


def thresh(img, ret):
    """
    BGRを分解して、それぞれ閾値で2値化し合成する
    ret: 2値化の閾値
    """
    b, g, r = cv2.split(img)
    b = np.where(b <= ret, 0, 255)
    b = b.astype("uint8")

    g = np.where(g <= ret, 0, 255)
    g = g.astype("uint8")

    r = np.where(r <= ret, 0, 255)
    r = r.astype("uint8")
    new_img = cv2.merge((b, g, r))
    return new_img


def yellow_roi(img):
    """
    製品の領域のみをきれいに切り取るために黄色ピクセルに注目する
    黄色領域のみを白、他の色の領域を黒に変換する
    輪郭を取得して、トリミング枠を決定する
    img: thresh関数を使用して、各チャンネルごとに2値化した画像
    """
    # 黄色を白、黄色以外の色を黒に変換する
    yellow = [0, 255, 255]
    white = [255, 255, 255]
    img[np.where((img == yellow).all(axis=2))] = white
    green = [255, 255, 0]
    black = [0, 0, 0]
    img[np.where((img == green).all(axis=2))] = black
    blue = [255, 0, 0]
    img[np.where((img == blue).all(axis=2))] = black
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, img_th = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    img_th = cv2.morphologyEx(img_th, cv2.MORPH_CLOSE, kernel)
    img_con, contours, hierarchy = cv2.findContours(img_th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    x1 = 5000000
    y1 = 5000000
    x2 = 0
    y2 = 0
    max_area = 0
    max_cnt = None
    if not contours == []:
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # 面積100以上の輪郭が、全て枠内に収まるようにトリミング枠を決定する
            if area > 100:
                x, y, w, h = cv2.boundingRect(cnt)
                if x < x1:
                    x1 = x
                if y < y1:
                    y1 = y
                if x + w > x2:
                    x2 = x + w
                if y + h > y2:
                    y2 = y + h
            # 面積が最大の輪郭を取り出す
            if area > max_area:
                max_cnt = cnt
                max_area = area
    else:
        height, width = img_th.shape[:2]
        max_cnt = np.array([[[0, 0], [0, height], [width, height], [width, 0]]])
        x1 = 0
        x2 = width
        y1 = 0
        y2 = height
    return x1, x2, y1, y2, max_cnt


def convex(img, p_w, p_h):
    """
    輪郭の凸性を利用して、凸製の欠陥のある点の座標を使用して
    縦線、横線を引いて輪郭を小さく区切る
    img: 黒画像に白矩形を描画したもの
    """
    while True:
        # ループするかどうか判定
        roop = 0
        img_con, contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            # 輪郭の外接矩形を取得する
            x, y, w, h = cv2.boundingRect(cnt)

            epsilon = 3
            cnt = cv2.approxPolyDP(cnt, epsilon, True)
            # 輪郭がパターン幅あるいは高さの3倍以上の場合に輪郭の凸性を調べる
            if w > p_w*3 or h > p_h*3:
                hull = cv2.convexHull(cnt, returnPoints=False)
                defects = cv2.convexityDefects(cnt, hull)
                # 凸性の欠陥が存在した場合
                if defects is not None:
                    # 欠陥のある点から、x方向y方向に垂直水平な黒い直線を引く
                    for i in range(defects.shape[0]):
                        s, e, f, d = defects[i, 0]
                        far = tuple(cnt[f][0])
                        farx = far[0]
                        fary = far[1]
                        cv2.line(img, (farx, y), (farx, y + h), 0, 3)
                        cv2.line(img, (x, fary), (x + w, fary), 0, 3)
                    roop += 1
        if roop == 0:
            break
    return img


def x_split(img, p_w):
    """
    輪郭幅が、パターン幅よりも広い場合x方向に切断する
    img: 黒画像に白矩形を描画したもの
    """
    img_con, contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 輪郭の2重検出を防ぐ
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 20:
            cv2.drawContours(img, [cnt], -1, 255, -1)

    # 輪郭とパターンの幅を比べる
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        q = w // p_w
        mod = w % p_w
        threshold = int(p_w / 5)
        # 輪郭の横幅をパターンで割った剰余がパターン幅の1/5を超えた場合、商よりも1つ多く横に並んでいる
        if mod > threshold:
            times = q + 1
        else:
            times = q
        # 輪郭がパターン2つ分以上並んでいる場合 輪郭を等分する
        if times > 1:
            new_width = int(w / times)
            for i in range(q):
                cv2.rectangle(img, (x + new_width - 3, y), (x + new_width + 3, y + h), (0, 0, 0), -1)
                x += new_width

    return img


def y_split(img, p_h):
    """
    輪郭高さが、パターン高さよりも広い場合y方向に切断する
    img: 黒画像に白矩形を描画したもの
    """
    img_con, contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # 輪郭とパターンの高さを比べる
    for cnt in contours:
        area = cv2.contourArea(cnt)
        x, y, w, h = cv2.boundingRect(cnt)
        if area > 20:
            q = h // p_h
            mod = h % p_h
            threshold = int(p_h / 5)
            # 輪郭の高さをパターンで割った剰余がパターン高さの1/5を超えた場合、商よりも1つ多く縦に並んでいる
            if mod > threshold:
                times = q + 1
            else:
                times = q
            # 輪郭がパターン2つ分以上並んでいる場合 輪郭を等分する
            if times > 1:
                new_height = int(h / times)
                for i in range(q):
                    cv2.rectangle(img, (x, y + new_height - 3), (x + w, y + new_height + 3), 0, -1)
                    y += new_height
    return img


def count(img, img_color, p_w, p_h):
    """
    輪郭の数を数える
    img: 黒画像に白矩形を描画したもの
    img_color: 検出画像
    """
    kernel = np.ones((3, 3), np.uint8)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
    img_con, contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    img_h, img_w = img.shape[:2]
    black = np.zeros((img_h, img_w), np.uint8)

    # パターンの縦横比の4倍を閾値に指定
    if p_w > p_h:
        thresh = p_w / p_h * 4
    else:
        thresh = p_h / p_w * 4

    for cnt in contours:
        area = cv2.contourArea(cnt)
        rect = cv2.minAreaRect(cnt)
        w, h = rect[1]
        # 面積が30以上のものを輪郭とする
        if area > 30:
            if w > h:
                magnif = w / h
            else:
                magnif = h / w
            # 閾値を超えるものは影と同様と考えて輪郭からは除外する
            if magnif < thresh:
                cv2.drawContours(black, [cnt], -1, 255, -1)
    # 離れそうな点をくっつける
    kernel = np.ones((3, 3), np.uint8)
    black = cv2.morphologyEx(black, cv2.MORPH_CLOSE, kernel)
    # 膨張したことによって、生まれた穴を塗りつぶす
    img_con, contours, hierarchy = cv2.findContours(black, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    black = cv2.drawContours(black, contours, -1, (255, 255, 255), -1)
    black = cv2.drawContours(black, contours, -1, (255, 255, 255), 1)
    img_con, contours, hierarchy = cv2.findContours(black, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 微細な穴が上手く塗りつぶせない場合があるため、別で処理する
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 10:
            black = cv2.drawContours(black, [cnt], -1, (255, 255, 255), -1)
            black = cv2.drawContours(black, [cnt], -1, (255, 255, 255), 1)
    img_con, contours, hierarchy = cv2.findContours(black, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    point = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 30:
            point += 1
            cv2.drawContours(img_color, [cnt], -1, (0, 0, 255), 1)
    return img_color, point


def make_mask(img_th, y1, y2, x1, x2, pattern, thresh):
    """
    製品領域から、歯抜け、点の部分のみを取得する
    img_th: 2値化された画像
    max_cnt: 黄色領域の最大輪郭
    thresh: パターン画像を2値化するための閾値 2値化された画像と同じ閾値を使用
    """
    ret, pattern_th = cv2.threshold(pattern, thresh, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    pattern_th = cv2.morphologyEx(pattern_th, cv2.MORPH_OPEN, kernel)
    img_con, contours, hierarchy = cv2.findContours(pattern_th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # パターンの面積を調べる パターンに線が入っている場合、その線で区切り、小さいほうの面積を閾値の面積とする
    thresh_area = 5000000
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < thresh_area:
            thresh_area = area

    kernel = np.ones((7, 7), np.uint8)
    img_th = cv2.morphologyEx(img_th, cv2.MORPH_OPEN, kernel)
    img_con, contours, hierarchy = cv2.findContours(img_th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        # 輪郭はパターンの面積の0.9倍以上の場合は、その場に残す
        if area > thresh_area * 0.9:
            cv2.rectangle(img_th, (x, y), (x + w, y + h), 255, 2)
        # それよりも小さい場合は、黒で塗りつぶす
        else:
            cv2.rectangle(img_th, (x, y), (x + w, y + h), 0, -1)

    # 製品以外の余白部分を歯抜けと混同しないようにマスクする
    new_th = img_th[y1:y2, x1:x2]
    new_nega = cv2.bitwise_not(new_th)
    kernel = np.ones((5, 5), np.uint8)
    new_e = cv2.erode(new_nega, kernel, iterations=1)
    return new_e


def black_only(img):
    """
    画像の黒以外の色をすべて白にする
    """
    white = [255, 255, 255]
    black = [0, 0, 0]
    # 黒以外の色をすべて白にする
    img[np.where((img != black).any(axis=2))] = white
    new_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    new_img, _ = binarize(new_img)
    # 白黒反転
    new_img = cv2.bitwise_not(new_img)
    return new_img


def count_point(result, is_count, img_rot, p_w, p_h, pattern):
    """
    画像を射影変換し、回転する
    その後、最適パターン画像を探し、製品検出結果を返す
    path: 画像のパス
    dir_path: パターン4枚が含まれるディレクトリ
    color: カラーによってHSV変換後、Hを使用するかVを使用するかに分かれる
    """
    new_img = thresh(img_rot, 120)
    # 黄色区域の輪郭をとらえる
    x1, x2, y1, y2, max_cnt = yellow_roi(new_img)
    img_rot_gray = cv2.cvtColor(img_rot, cv2.COLOR_BGR2GRAY)
    img_rot_th, ret = binarize(img_rot_gray)
    # マスク画像作成
    new_e = make_mask(img_rot_th, y1, y2, x1, x2, pattern, ret)
    # 凸性によって区切る
    new_e = convex(new_e, p_w, p_h)
    # x方向に区切る
    mask = x_split(new_e, p_w)
    # y方向に区切る
    mask = y_split(mask, p_h)
    mean = np.mean(img_rot_gray)
    # 画像の平均値によって閾値を決定する
    if mean > 160:
        threshold = 85
    elif 150 < mean <= 160:
        threshold = 80
    elif 140 < mean <= 150:
        threshold = 75
    elif 130 < mean <= 140:
        threshold = 70
    else:
        threshold = 65
    new_img_2 = thresh(img_rot, threshold)
    new_img_2 = black_only(new_img_2)
    new_img_2 = new_img_2[y1:y2, x1:x2]
    # マスク画像を使って、点を区切る
    new = cv2.bitwise_and(new_img_2, new_img_2, mask=mask)
    roi = result[y1:y2, x1:x2]
    # 点をカウントする
    result2, point = count(new, roi, p_w, p_h)

    return result2, is_count, point


if __name__ == "__main__":
    import matching_pattern
    path = sys.argv[1]
    dir_path = sys.argv[2]
    n = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(n, cv2.IMREAD_COLOR)
    if len(sys.argv) == 4:
        color = sys.argv[3]
        result, is_count, img_rot, p_w, p_h, pattern = matching_pattern.matching_pattern(img, dir_path)
    else:
        color = "blue"
        result, is_count, img_rot, p_w, p_h, pattern = matching_pattern.matching_pattern(img, dir_path)

    result, is_count, point = count_point(result, is_count, img_rot, p_w, p_h, pattern)

    print("製品個数：{0}個, 点個数：{1}個".format(is_count, point))

